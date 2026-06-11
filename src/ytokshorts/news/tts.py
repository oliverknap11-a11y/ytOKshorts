"""Text-to-speech voiceover via edge-tts (free, no API key), with word timings.

edge-tts streams audio chunks plus ``WordBoundary`` metadata; we capture both so
the captions can be timed to the spoken words. The offset→seconds conversion is
pure and unit-tested; the network/audio part is isolated in :func:`synthesize`.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from ..errors import MissingDependencyError

# edge-tts reports time in 100-nanosecond "ticks" (the .NET TimeSpan unit).
_TICKS_PER_SECOND = 10_000_000


@dataclass(frozen=True)
class WordCue:
    """A spoken word and when it occurs, in seconds from the start."""

    word: str
    start: float
    end: float


def boundaries_to_cues(boundaries: list[dict]) -> list[WordCue]:
    """Convert raw edge-tts WordBoundary dicts (ticks) to :class:`WordCue` (seconds).

    Each boundary has ``offset``/``duration`` in 100ns ticks and ``text``.
    """
    cues: list[WordCue] = []
    for b in boundaries:
        offset = b.get("offset", 0) / _TICKS_PER_SECOND
        duration = b.get("duration", 0) / _TICKS_PER_SECOND
        text = (b.get("text") or "").strip()
        if text:
            cues.append(WordCue(word=text, start=round(offset, 3), end=round(offset + duration, 3)))
    return cues


def synthesize(text: str, out_path: str | Path, *, voice: str) -> list[WordCue]:
    """Synthesize ``text`` to an mp3 at ``out_path``; return word-timed cues."""
    try:
        import edge_tts  # type: ignore
    except ImportError as exc:
        raise MissingDependencyError(
            "edge-tts", extra="news", purpose="generate the voiceover"
        ) from exc

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    async def _run() -> list[dict]:
        communicate = edge_tts.Communicate(text, voice)
        boundaries: list[dict] = []
        with open(out, "wb") as f:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    f.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    boundaries.append(chunk)
        return boundaries

    boundaries = asyncio.run(_run())
    return boundaries_to_cues(boundaries)
