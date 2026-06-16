"""Compose a vertical Short from a voiceover: background + title + word captions.

There is no source video to clip here — we synthesize the visual from a
background (a drawn football pitch, user media, or a gradient) and burned-in,
word-timed captions that pop in and highlight numbers. The ASS document and the
ffmpeg command are built by pure functions so they can be asserted in tests.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..captions import Caption, _ass_escape, format_ass_timestamp
from ..clip import escape_filter_path
from .tts import WordCue

# Tokens worth emphasizing on screen: scores (2-1), money (£50m), %, ages, dates.
_EMPH_RE = re.compile(r"(?:£|\$|€)?\d[\d.,:]*(?:[-–]\d[\d.,]*)?(?:[a-zA-Z%]+)?")
_GOLD = r"{\c&H28C8FF&}"   # ASS \c is &HBBGGRR& — this is gold (#FFC828)
_WHITE = r"{\c&HFFFFFF&}"


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


def title_override(animate: bool) -> str:
    """Leading ASS override for the title: a gentle fade-in (pure)."""
    return r"{\fad(300,120)}" if animate else ""


def emphasize_numbers(escaped_text: str) -> str:
    """Wrap number-like tokens (scores, money, %) in a gold colour run (pure)."""
    return _EMPH_RE.sub(lambda m: f"{_GOLD}{m.group(0)}{_WHITE}", escaped_text)


def caption_override(animate: bool) -> str:
    """Leading ASS override for a 'pop' caption chunk: fade + scale (pure)."""
    if not animate:
        return ""
    return r"{\fad(90,70)\fscx72\fscy72\t(0,140,\fscx100\fscy100)}"


def stack_caption_override(x: int, y: int, active_seconds: float, animate: bool) -> str:
    """Override for a stacked subtitle line: position, fade-in, then dim after spoken.

    The line fades in at ``(x, y)`` (top-anchored), stays bright while it's being
    spoken, then dims to ~57% so the next line below it becomes the focus.
    """
    base = rf"\an8\pos({x},{y})"
    if not animate:
        return "{" + base + "}"
    a = max(150, round(active_seconds * 1000))
    return (
        "{" + base
        + r"\alpha&HFF&\t(0,120,\alpha&H00&)"   # fade in
        + rf"\t({a},{a + 260},\alpha&H6E&)" + "}"  # dim once spoken
    )


def stack_dialogues(
    captions: list[Caption],
    *,
    width: int,
    height: int,
    caption_fs: int,
    duration: float,
    animate: bool,
    emphasize: bool,
    y_top_frac: float = 0.20,
    y_bottom_frac: float = 0.90,
) -> list[str]:
    """Lay subtitles out as an accumulating, downward-building, paged stack (pure).

    Lines appear under one another as they're spoken within the vertical band
    ``[y_top_frac, y_bottom_frac]``; when the column reaches the bottom of the
    band it clears and the next page starts again from the top.
    """
    if not captions:
        return []
    y_top = round(height * y_top_frac)
    y_bottom = round(height * y_bottom_frac)
    line_h = max(1, round(caption_fs * 1.30))
    max_lines = max(1, (y_bottom - y_top) // line_h)

    out: list[str] = []
    n = len(captions)
    for p in range(0, n, max_lines):
        page = captions[p : p + max_lines]
        page_end = captions[p + max_lines].start if p + max_lines < n else duration
        for j, c in enumerate(page):
            y = y_top + j * line_h
            body = emphasize_numbers(_ass_escape(c.text)) if emphasize else _ass_escape(c.text)
            ov = stack_caption_override(width // 2, y, c.end - c.start, animate)
            out.append(
                f"Dialogue: 0,{format_ass_timestamp(c.start)},{format_ass_timestamp(page_end)},"
                f"Caption,,0,0,0,,{ov}{body}"
            )
    return out


def pop_dialogues(
    captions: list[Caption], *, animate: bool, emphasize: bool
) -> list[str]:
    """One centered caption chunk at a time (the original 'pop' style) — pure."""
    out: list[str] = []
    for c in captions:
        body = emphasize_numbers(_ass_escape(c.text)) if emphasize else _ass_escape(c.text)
        out.append(
            f"Dialogue: 0,{format_ass_timestamp(c.start)},{format_ass_timestamp(c.end)},"
            f"Caption,,0,0,0,,{caption_override(animate)}{body}"
        )
    return out


def build_news_ass(
    title: str,
    captions: list[Caption],
    *,
    width: int,
    height: int,
    duration: float,
    font: str = "Arial",
    animate: bool = True,
    emphasize: bool = True,
    style: str = "stack",
    band: str = "full",
) -> str:
    """Render the ASS: a persistent top title + captions.

    ``style="stack"`` builds subtitles down the screen (each line stays as the
    next appears under it); ``style="pop"`` shows one centered chunk at a time.
    ``band`` constrains the stack vertically: ``"full"`` uses most of the frame,
    ``"top"`` keeps subtitles in the upper third (above a presenter's head),
    ``"center"`` keeps them mid-frame.
    """
    title_fs = max(24, round(height * 0.032))
    if style == "stack":
        caption_fs = max(36, round(height * 0.040))
    else:
        caption_fs = max(40, round(height * 0.062))
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
        # Caption: bold white with a heavy outline + drop shadow.
        f"Style: Caption,{font},{caption_fs},&H00FFFFFF,&H000000FF,&H00000000,&HA0000000,"
        f"1,0,0,0,100,100,0,0,1,3,2,5,{side},{side},0,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, "
        "MarginV, Effect, Text\n"
    )

    lines = []
    if title.strip():
        lines.append(
            f"Dialogue: 0,{format_ass_timestamp(0)},{format_ass_timestamp(duration)},"
            f"Title,,0,0,0,,{title_override(animate)}{_ass_escape(title.strip())}"
        )
    if style == "stack":
        has_title = bool(title.strip())
        if band == "top":
            y_top_frac, y_bottom_frac = 0.13, 0.46
        elif band == "center":
            y_top_frac, y_bottom_frac = 0.30, 0.66
        else:  # full
            y_top_frac, y_bottom_frac = (0.20 if has_title else 0.12), 0.90
        lines += stack_dialogues(
            captions, width=width, height=height, caption_fs=caption_fs,
            duration=duration, animate=animate, emphasize=emphasize,
            y_top_frac=y_top_frac, y_bottom_frac=y_bottom_frac,
        )
    else:
        lines += pop_dialogues(captions, animate=animate, emphasize=emphasize)
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
    background: tuple[str, str] | None = None,
    scrim: float = 0.4,
    fps: int = 30,
    ffmpeg: str = "ffmpeg",
    crf: int = 20,
    preset: str = "veryfast",
) -> list[str]:
    """Assemble the ffmpeg argv that renders the captioned Short.

    ``background`` is ``None`` (gradient), or ``("image", path)`` / ``("video",
    path)`` for user media; image/video backgrounds get a ``scrim`` darkening so
    captions stay legible.
    """
    if duration <= 0:
        raise ValueError("duration must be > 0")

    input_args, prep = _background_input_and_filter(
        background, width, height, duration, bg_top, bg_bottom, scrim, fps
    )
    filtergraph = f"{prep};[bg]ass={escape_filter_path(ass_path)},format=yuv420p[v]"

    return [
        ffmpeg,
        "-v", "error",
        "-y",
        *input_args,
        "-i", str(audio_path),
        "-filter_complex", filtergraph,
        "-map", "[v]",
        "-map", "1:a",
        "-t", f"{duration:.3f}",
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]


def build_presenter_compose_command(
    ass_path: str | Path,
    presenter_path: str | Path,
    output_path: str | Path,
    *,
    width: int,
    height: int,
    duration: float,
    bg_top: str,
    bg_bottom: str,
    background: tuple[str, str] | None = None,
    scrim: float = 0.4,
    presenter_has_audio: bool = True,
    audio_path: str | Path | None = None,
    chroma_color: str = "#00FF00",
    chroma_similarity: float = 0.18,
    chroma_blend: float = 0.10,
    scale: float = 0.62,
    position: str = "bottom",
    fps: int = 30,
    ffmpeg: str = "ffmpeg",
    crf: int = 20,
    preset: str = "veryfast",
) -> list[str]:
    """Composite a presenter video over the background, with captions on top.

    The presenter is chroma-keyed (green screen) and overlaid; audio comes from
    the presenter clip itself (``presenter_has_audio``, e.g. HeyGen output) or
    from a separate ``audio_path`` (looped presenter clips).
    """
    if duration <= 0:
        raise ValueError("duration must be > 0")

    bg_args, bg_prep = _background_input_and_filter(
        background, width, height, duration, bg_top, bg_bottom, scrim, fps
    )
    # Input order: [0]=background, [1]=presenter, [2]=audio (only when separate).
    if presenter_has_audio:
        presenter_args = ["-i", str(presenter_path)]
        audio_map = "1:a"
    else:
        presenter_args = ["-stream_loop", "-1", "-i", str(presenter_path)]
        if audio_path is None:
            raise ValueError("audio_path is required when presenter_has_audio is False")
        presenter_args += ["-i", str(audio_path)]
        audio_map = "2:a"

    ph = round(height * scale)
    y = (height - ph) if position == "bottom" else (height - ph) // 2
    key = ""
    if chroma_color:
        key = (
            f"chromakey={hex_to_ff_color(chroma_color)}:{chroma_similarity:.3f}:"
            f"{chroma_blend:.3f},"
        )
    presenter_chain = f"[1:v]{key}scale=-1:{ph}[pres]"
    overlay = f"[bgf][pres]overlay=(W-w)/2:{y}[comp]"
    filtergraph = (
        f"{bg_prep.removesuffix('[bg]')}[bgf];"   # reuse bg cover/scrim, relabel
        f"{presenter_chain};"
        f"{overlay};"
        f"[comp]ass={escape_filter_path(ass_path)},format=yuv420p[v]"
    )

    return [
        ffmpeg,
        "-v", "error",
        "-y",
        *bg_args,
        *presenter_args,
        "-filter_complex", filtergraph,
        "-map", "[v]",
        "-map", audio_map,
        "-t", f"{duration:.3f}",
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]


def _background_input_and_filter(
    background: tuple[str, str] | None,
    width: int,
    height: int,
    duration: float,
    bg_top: str,
    bg_bottom: str,
    scrim: float,
    fps: int,
) -> tuple[list[str], str]:
    """Return ``(input_args, prep_filter)`` producing a ``[bg]`` label."""
    cover = (
        f"[0:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    if background is None:
        gradient = build_gradient_input(width, height, duration, bg_top, bg_bottom)
        return ["-f", "lavfi", "-i", gradient], f"{cover}[bg]"

    kind, path = background
    if kind == "image":
        input_args = ["-loop", "1", "-framerate", str(fps), "-i", str(path)]
    elif kind == "video":
        input_args = ["-stream_loop", "-1", "-i", str(path)]
    else:
        raise ValueError(f"Unknown background kind: {kind!r}")
    if scrim > 0:
        cover += f",drawbox=x=0:y=0:w={width}:h={height}:color=black@{scrim:.2f}:t=fill"
    return input_args, f"{cover}[bg]"
