"""Media inspection and audio extraction via ffprobe / ffmpeg."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import ExternalToolError
from .external import require_tool, run

# Sample rate used for the loudness analysis. We don't need fidelity here, just
# a consistent envelope, so 16 kHz mono keeps the PCM small and fast to scan.
ANALYSIS_SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class MediaInfo:
    """The handful of source properties the pipeline actually cares about."""

    duration: float
    width: int
    height: int
    has_audio: bool

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 0.0


def probe(path: str | Path) -> MediaInfo:
    """Return duration / dimensions / audio presence for ``path`` via ffprobe."""
    ffprobe = require_tool("ffprobe")
    proc = run(
        [
            ffprobe,
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            str(path),
        ]
    )
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive
        raise ExternalToolError(
            f"Could not parse ffprobe output for {path}", tool="ffprobe"
        ) from exc
    return _media_info_from_probe(data)


def _media_info_from_probe(data: dict) -> MediaInfo:
    """Pure transform from ffprobe JSON to :class:`MediaInfo` (unit-testable)."""
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    duration = 0.0
    fmt_dur = data.get("format", {}).get("duration")
    if fmt_dur is not None:
        duration = float(fmt_dur)
    elif video and video.get("duration") is not None:
        duration = float(video["duration"])

    width = int(video["width"]) if video and video.get("width") else 0
    height = int(video["height"]) if video and video.get("height") else 0
    return MediaInfo(duration=duration, width=width, height=height, has_audio=has_audio)


def extract_pcm(path: str | Path, *, sample_rate: int = ANALYSIS_SAMPLE_RATE) -> bytes:
    """Decode ``path`` to mono signed-16-bit little-endian PCM and return bytes.

    Streamed to stdout (captured as binary — PCM is not text) so we never write
    a giant WAV to disk just to scan it.
    """
    import subprocess

    ffmpeg = require_tool("ffmpeg")
    cmd = [
        ffmpeg,
        "-v", "error",
        "-i", str(path),
        "-ac", "1",
        "-ar", str(sample_rate),
        "-f", "s16le",
        "-acodec", "pcm_s16le",
        "pipe:1",
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise ExternalToolError(
            f"ffmpeg failed to extract audio from {path}",
            tool="ffmpeg",
            returncode=proc.returncode,
            stderr=proc.stderr.decode("utf-8", "replace"),
        )
    return proc.stdout
