"""Pick the most "interesting" segments of a video from its audio energy.

The heuristic is deliberately simple and dependency-free: loud, sustained
passages (laughter, music drops, emphatic speech, applause) tend to be the
moments worth clipping. We build a loudness envelope, then greedily select
non-overlapping windows with the highest energy.

Everything here is pure (operates on plain numbers), so the selection logic is
fully unit-testable without ffmpeg or any media file.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass


@dataclass(frozen=True)
class Segment:
    """A chosen clip: ``start``/``end`` in seconds, plus a relative ``score``."""

    start: float
    end: float
    score: float

    @property
    def duration(self) -> float:
        return self.end - self.start

    def __str__(self) -> str:  # pragma: no cover - cosmetic
        return f"[{self.start:7.2f}s → {self.end:7.2f}s] ({self.duration:5.1f}s, score={self.score:.3f})"


def compute_window_energies(
    pcm: bytes,
    sample_rate: int,
    window_seconds: float,
) -> list[float]:
    """Reduce raw mono s16le PCM to one RMS-loudness value per time window.

    Uses numpy when available (fast), otherwise a pure-Python fallback so the
    base install needs no compiled dependencies.
    """
    if window_seconds <= 0:
        raise ValueError("window_seconds must be > 0")
    samples_per_window = max(1, round(window_seconds * sample_rate))
    sample_count = len(pcm) // 2
    if sample_count == 0:
        return []

    try:
        import numpy as np  # type: ignore
    except ImportError:
        return _window_energies_py(pcm, sample_count, samples_per_window)

    data = np.frombuffer(pcm, dtype="<i2", count=sample_count).astype(np.float64)
    n_windows = math.ceil(sample_count / samples_per_window)
    energies: list[float] = []
    for w in range(n_windows):
        chunk = data[w * samples_per_window : (w + 1) * samples_per_window]
        if chunk.size:
            energies.append(float(np.sqrt(np.mean(chunk * chunk))))
    return energies


def _window_energies_py(pcm: bytes, sample_count: int, samples_per_window: int) -> list[float]:
    """Pure-Python RMS-per-window fallback (no numpy)."""
    # struct-unpack the whole buffer once; '<h' enforces little-endian s16.
    samples = struct.unpack(f"<{sample_count}h", pcm[: sample_count * 2])
    energies: list[float] = []
    for start in range(0, sample_count, samples_per_window):
        chunk = samples[start : start + samples_per_window]
        if not chunk:
            continue
        acc = 0
        for s in chunk:
            acc += s * s
        energies.append(math.sqrt(acc / len(chunk)))
    return energies


def smooth(values: list[float], radius: int) -> list[float]:
    """Centered moving-average smoothing with a +/- ``radius`` window.

    Tames single-window spikes so selection latches onto sustained energy rather
    than one loud transient.
    """
    if radius <= 0 or len(values) <= 1:
        return list(values)
    n = len(values)
    # Prefix sums make this O(n) regardless of radius.
    prefix = [0.0]
    for v in values:
        prefix.append(prefix[-1] + v)
    out: list[float] = []
    for i in range(n):
        lo = max(0, i - radius)
        hi = min(n, i + radius + 1)
        out.append((prefix[hi] - prefix[lo]) / (hi - lo))
    return out


def find_highlights(
    energies: list[float],
    window_seconds: float,
    *,
    min_duration: float,
    max_duration: float,
    target_count: int,
    spacing: float,
) -> list[Segment]:
    """Greedily select up to ``target_count`` high-energy, non-overlapping clips.

    ``energies`` is one loudness value per ``window_seconds`` of audio (as
    produced by :func:`compute_window_energies`). Clips are a fixed length —
    ``max_duration`` clamped to what the source can supply — and kept at least
    ``spacing`` seconds apart. Returns segments ordered by start time; the
    ``score`` is each clip's mean energy normalized to the loudest clip (0–1).
    """
    n = len(energies)
    if n == 0 or target_count < 1:
        return []

    total_duration = n * window_seconds
    clip_len = min(max_duration, total_duration)
    if clip_len < min_duration:
        # Source is shorter than a viable Short — nothing to cut.
        return []

    smoothed = smooth(energies, radius=max(1, round(1.0 / window_seconds)))

    clip_windows = max(1, round(clip_len / window_seconds))
    clip_windows = min(clip_windows, n)
    spacing_windows = max(0, round(spacing / window_seconds))

    # Prefix sums of the smoothed envelope → O(1) window energy lookups.
    prefix = [0.0]
    for v in smoothed:
        prefix.append(prefix[-1] + v)

    last_start = n - clip_windows
    candidates = [
        (prefix[s + clip_windows] - prefix[s], s)
        for s in range(0, last_start + 1)
    ]
    # Highest energy first; ties broken by earlier start for determinism.
    candidates.sort(key=lambda t: (-t[0], t[1]))

    chosen: list[tuple[int, int]] = []  # (start_window, end_window) exclusive
    chosen_energy: list[float] = []
    for energy_sum, start in candidates:
        if len(chosen) >= target_count:
            break
        end = start + clip_windows
        if _overlaps(start, end, chosen, spacing_windows):
            continue
        chosen.append((start, end))
        chosen_energy.append(energy_sum / clip_windows)

    if not chosen:
        return []

    peak = max(chosen_energy) or 1.0
    segments = [
        Segment(
            start=round(s * window_seconds, 3),
            end=round(min(e * window_seconds, total_duration), 3),
            score=round(energy / peak, 4),
        )
        for (s, e), energy in zip(chosen, chosen_energy)
    ]
    segments.sort(key=lambda seg: seg.start)
    return segments


def _overlaps(
    start: int,
    end: int,
    chosen: list[tuple[int, int]],
    spacing_windows: int,
) -> bool:
    """True if [start, end) comes within ``spacing_windows`` of any chosen span."""
    for cs, ce in chosen:
        if not (end + spacing_windows <= cs or start >= ce + spacing_windows):
            return True
    return False
