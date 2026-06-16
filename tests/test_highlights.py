"""Tests for the (pure) highlight-selection logic."""

import math
import struct

import pytest

from ytokshorts.highlights import (
    Segment,
    compute_window_energies,
    find_highlights,
    smooth,
)


def _pcm(samples):
    """Pack int16 samples into little-endian s16 PCM bytes."""
    return struct.pack(f"<{len(samples)}h", *samples)


def test_compute_window_energies_counts_and_values():
    # 1000 Hz, window 0.5s => 500 samples/window. Two windows.
    sr = 1000
    quiet = [0] * 500
    loud = [10000, -10000] * 250  # constant-magnitude => RMS == 10000
    energies = compute_window_energies(_pcm(quiet + loud), sr, 0.5)
    assert len(energies) == 2
    assert energies[0] == pytest.approx(0.0)
    assert energies[1] == pytest.approx(10000.0, rel=1e-6)


def test_compute_window_energies_empty():
    assert compute_window_energies(b"", 16000, 0.5) == []


def test_compute_window_energies_rejects_bad_window():
    with pytest.raises(ValueError):
        compute_window_energies(_pcm([1, 2, 3, 4]), 1000, 0)


def test_smooth_constant_is_unchanged():
    vals = [5.0] * 10
    assert smooth(vals, radius=2) == pytest.approx(vals)


def test_smooth_reduces_single_spike():
    vals = [0, 0, 10, 0, 0]
    out = smooth([float(v) for v in vals], radius=1)
    # The spike is averaged with neighbours -> lower peak, raised shoulders.
    assert out[2] == pytest.approx(10 / 3)
    assert out[1] > 0
    assert max(out) < 10


def test_find_highlights_locates_loud_region():
    # 60s of audio at window=1s; a loud plateau from 30-40s.
    window = 1.0
    energies = [1.0] * 60
    for i in range(30, 40):
        energies[i] = 100.0
    segs = find_highlights(
        energies, window,
        min_duration=5, max_duration=10, target_count=1, spacing=5,
    )
    assert len(segs) == 1
    seg = segs[0]
    # The 10s clip should cover the loud plateau.
    assert seg.start <= 30 and seg.end >= 40
    assert seg.score == pytest.approx(1.0)


def test_find_highlights_respects_target_count_and_spacing():
    window = 1.0
    energies = [1.0] * 120
    for center in (20, 60, 100):
        for i in range(center, center + 5):
            energies[i] = 50.0
    segs = find_highlights(
        energies, window,
        min_duration=5, max_duration=10, target_count=3, spacing=5,
    )
    assert len(segs) == 3
    # Returned in start order and non-overlapping with >= spacing between them.
    assert segs == sorted(segs, key=lambda s: s.start)
    for a, b in zip(segs, segs[1:]):
        assert b.start - a.end >= 5


def test_find_highlights_too_short_returns_empty():
    # Only 5s of audio but min clip is 15s.
    energies = [1.0] * 5
    segs = find_highlights(
        energies, 1.0,
        min_duration=15, max_duration=58, target_count=5, spacing=5,
    )
    assert segs == []


def test_find_highlights_empty_input():
    assert find_highlights([], 0.5, min_duration=15, max_duration=58, target_count=5, spacing=5) == []


def test_segment_duration():
    assert Segment(10.0, 25.0, 0.5).duration == 15.0
