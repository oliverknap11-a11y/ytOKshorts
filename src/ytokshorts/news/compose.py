"""Compose a vertical Short from a voiceover: gradient bg + title + word captions.

There is no source video to clip here — we synthesize the visual from a gradient
background and burned-in, word-timed captions. The ASS document and the ffmpeg
command are built by pure functions so they can be asserted in tests.
"""

from __future__ import annotations

from pathlib import Path

from ..captions import Caption, _ass_escape, format_ass_timestamp
from ..clip import escape_filter_path
from .tts import WordCue


def group_words_into_captions(cues: list[WordCue], max_words: int) -> list[Caption]:
    """Chunk word cues into short caption lines timed to the speech (pure)."""
    captions: list[Caption] = []
    for i in range(0, len(cues), max_words):
        group = cues[i : i + max_words]
        if not group:
            continue
        text = " ".join(c.word for c in group)
        start, end = group[0].start, group[-1].end
        if end <= start:
            end = start + 0.4
        captions.append(Caption(start=start, end=end, text=text))
    return captions


def build_news_ass(
    title: str,
    captions: list[Caption],
    *,
    width: int,
    height: int,
    duration: float,
    font: str = "Arial",
) -> str:
    """Render a two-style ASS: a persistent top title + center word captions."""
    title_fs = max(24, round(height * 0.032))
    caption_fs = max(40, round(height * 0.060))
    title_mv = round(height * 0.07)
    side = round(width * 0.07)

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
        # Title: top-centered, gold, medium.
        f"Style: Title,{font},{title_fs},&H0028C8FF,&H000000FF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,3,0,8,{side},{side},{title_mv},1\n"
        # Caption: center, big, bold, white with a heavy outline.
        f"Style: Caption,{font},{caption_fs},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,"
        f"1,0,0,0,100,100,0,0,1,4,1,5,{side},{side},0,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )

    lines = []
    if title.strip():
        lines.append(
            f"Dialogue: 0,{format_ass_timestamp(0)},{format_ass_timestamp(duration)},"
            f"Title,,0,0,0,,{_ass_escape(title.strip())}"
        )
    for c in captions:
        lines.append(
            f"Dialogue: 0,{format_ass_timestamp(c.start)},{format_ass_timestamp(c.end)},"
            f"Caption,,0,0,0,,{_ass_escape(c.text)}"
        )
    return header + "\n".join(lines) + ("\n" if lines else "")


def hex_to_ff_color(value: str) -> str:
    """Convert a ``#RRGGBB`` string to ffmpeg's ``0xRRGGBB`` color form."""
    v = value.strip().lstrip("#")
    if len(v) != 6 or not all(c in "0123456789abcdefABCDEF" for c in v):
        raise ValueError(f"Invalid hex color: {value!r}")
    return f"0x{v.upper()}"


def build_gradient_input(width: int, height: int, duration: float, top: str, bottom: str) -> str:
    """Build the lavfi ``gradients`` source spec for a near-static vertical fade."""
    c0, c1 = hex_to_ff_color(top), hex_to_ff_color(bottom)
    # Vertical (top→bottom) gradient; a tiny speed keeps it alive without distracting.
    return (
        f"gradients=s={width}x{height}:c0={c0}:c1={c1}:"
        f"x0=0:y0=0:x1=0:y1={height}:nb_colors=2:speed=0.004:duration={duration:.3f}"
    )


def build_compose_command(
    audio_path: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    *,
    width: int,
    height: int,
    duration: float,
    bg_top: str,
    bg_bottom: str,
    ffmpeg: str = "ffmpeg",
    crf: int = 20,
    preset: str = "veryfast",
) -> list[str]:
    """Assemble the ffmpeg argv that renders the captioned Short."""
    if duration <= 0:
        raise ValueError("duration must be > 0")
    gradient = build_gradient_input(width, height, duration, bg_top, bg_bottom)
    filtergraph = f"[0:v]ass={escape_filter_path(ass_path)},format=yuv420p[v]"
    return [
        ffmpeg,
        "-v", "error",
        "-y",
        "-f", "lavfi",
        "-i", gradient,
        "-i", str(audio_path),
        "-filter_complex", filtergraph,
        "-map", "[v]",
        "-map", "1:a",
        "-t", f"{duration:.3f}",
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]
