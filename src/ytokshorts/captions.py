"""Transcribe audio and render burn-in subtitles.

The transcription step uses faster-whisper (an optional dependency). Everything
that turns timed text into SRT/ASS — the part most likely to have off-by-one
bugs — is pure and unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import CaptionConfig
from .errors import MissingDependencyError

# ASS \an alignment values (numpad layout): bottom / middle / top, all centered.
_ASS_ALIGNMENT = {"bottom": 2, "center": 5, "top": 8}


@dataclass(frozen=True)
class Caption:
    """A single timed subtitle cue, in seconds relative to its clip."""

    start: float
    end: float
    text: str


def transcribe(
    audio_path: str | Path,
    *,
    model: str = "base",
    language: str | None = None,
) -> list[Caption]:
    """Transcribe ``audio_path`` into timed :class:`Caption` cues with Whisper.

    Imported lazily so the package works without the (large) ASR dependency
    installed; raises :class:`MissingDependencyError` with an install hint if
    it's needed but absent.
    """
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as exc:
        raise MissingDependencyError(
            "faster-whisper", extra="captions", purpose="generate captions"
        ) from exc

    whisper = WhisperModel(model, device="cpu", compute_type="int8")
    segments, _info = whisper.transcribe(str(audio_path), language=language)
    cues: list[Caption] = []
    for seg in segments:
        text = seg.text.strip()
        if text:
            cues.append(Caption(start=float(seg.start), end=float(seg.end), text=text))
    return cues


def clip_captions(captions: list[Caption], start: float, end: float) -> list[Caption]:
    """Return captions overlapping [start, end), retimed to the clip's origin.

    Lets you transcribe a whole video once and then slice cues per clip, with
    cue times shifted so 0 is the start of the clip.
    """
    out: list[Caption] = []
    for c in captions:
        if c.end <= start or c.start >= end:
            continue
        new_start = max(0.0, c.start - start)
        new_end = min(end, c.end) - start
        if new_end > new_start:
            out.append(Caption(start=new_start, end=new_end, text=c.text))
    return out


def format_srt_timestamp(seconds: float) -> str:
    """Seconds → ``HH:MM:SS,mmm`` (SRT format)."""
    if seconds < 0:
        seconds = 0.0
    ms_total = round(seconds * 1000)
    hours, ms_total = divmod(ms_total, 3_600_000)
    minutes, ms_total = divmod(ms_total, 60_000)
    secs, millis = divmod(ms_total, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def format_ass_timestamp(seconds: float) -> str:
    """Seconds → ``H:MM:SS.cc`` (ASS format, centiseconds)."""
    if seconds < 0:
        seconds = 0.0
    cs_total = round(seconds * 100)
    hours, cs_total = divmod(cs_total, 360_000)
    minutes, cs_total = divmod(cs_total, 6_000)
    secs, centis = divmod(cs_total, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{centis:02d}"


def to_srt(captions: list[Caption]) -> str:
    """Render cues as an SRT document."""
    blocks = []
    for i, c in enumerate(captions, start=1):
        blocks.append(
            f"{i}\n"
            f"{format_srt_timestamp(c.start)} --> {format_srt_timestamp(c.end)}\n"
            f"{c.text}\n"
        )
    return "\n".join(blocks)


def to_ass(
    captions: list[Caption],
    config: CaptionConfig,
    *,
    width: int,
    height: int,
) -> str:
    """Render cues as a styled ASS document sized for ``width`` x ``height``.

    ASS gives us control over font, outline and vertical placement, which is
    what makes burned-in Shorts captions look intentional rather than default.
    """
    alignment = _ASS_ALIGNMENT[config.position]
    margin_v = max(10, round(height * 0.08))
    style = (
        "Style: Default,"
        f"{config.font},{config.font_size},"
        f"{config.primary_color},&H000000FF,"
        f"{config.outline_color},&H64000000,"
        "0,0,0,0,"          # bold, italic, underline, strikeout
        "100,100,0,0,"       # scale x/y, spacing, angle
        f"1,{config.outline},0,"  # border style, outline, shadow
        f"{alignment},40,40,{margin_v},1"  # alignment, margins L/R/V, encoding
    )
    header = (
        "[Script Info]\n"
        "ScriptType: v4.00+\n"
        "WrapStyle: 0\n"
        "ScaledBorderAndShadow: yes\n"
        f"PlayResX: {width}\n"
        f"PlayResY: {height}\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"{style}\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )
    lines = []
    for c in captions:
        text = _ass_escape(c.text)
        lines.append(
            f"Dialogue: 0,{format_ass_timestamp(c.start)},"
            f"{format_ass_timestamp(c.end)},Default,,0,0,0,,{text}"
        )
    return header + "\n".join(lines) + ("\n" if lines else "")


def _ass_escape(text: str) -> str:
    """Escape characters that have meaning in an ASS dialogue line."""
    # Collapse newlines into ASS hard-breaks and neutralize brace overrides.
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\r\n", "\\N")
        .replace("\n", "\\N")
    )
