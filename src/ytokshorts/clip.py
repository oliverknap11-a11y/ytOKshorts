"""Cut a segment, reframe it to vertical 9:16, and burn in captions.

The ffmpeg invocation is assembled by small pure functions (``build_*``) so the
exact filtergraph and argument list can be asserted in tests; :func:`render_clip`
is the only part that actually touches the binary.
"""

from __future__ import annotations

from pathlib import Path

from .config import ReframeConfig
from .external import require_tool, run


def build_filtergraph(reframe: ReframeConfig, ass_path: str | None) -> tuple[str, str]:
    """Return ``(filtergraph, output_label)`` for the reframe (+ optional captions).

    ``crop`` zooms and center-crops to fill the vertical frame. ``blur`` fits the
    whole source and fills the bars with a blurred, zoomed copy of itself — the
    look most Shorts use to avoid cropping faces out of frame.
    """
    tw, th = reframe.width, reframe.height
    if reframe.mode == "crop":
        graph = (
            f"[0:v]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},setsar=1[v]"
        )
    else:  # blur
        graph = (
            f"[0:v]split=2[bg][fg];"
            f"[bg]scale={tw}:{th}:force_original_aspect_ratio=increase,"
            f"crop={tw}:{th},boxblur=20:1[bgb];"
            f"[fg]scale={tw}:{th}:force_original_aspect_ratio=decrease[fgs];"
            f"[bgb][fgs]overlay=(W-w)/2:(H-h)/2,setsar=1[v]"
        )

    if ass_path:
        graph += f";[v]ass={escape_filter_path(ass_path)}[vout]"
        return graph, "vout"
    return graph, "v"


def escape_filter_path(path: str | Path) -> str:
    """Escape a filesystem path for use inside an ffmpeg filter argument.

    Inside a filtergraph, ``:`` separates options and ``'`` quotes values, so
    both must be escaped or a path with a colon/space breaks the graph.

    Windows paths use backslashes, which the filtergraph parser treats as escape
    characters and silently eats (``work\\news\\x.ass`` → ``worknewsx.ass``).
    ffmpeg accepts forward slashes on Windows too, so we normalize to ``/`` and
    only have to escape the drive-letter colon.
    """
    s = str(path).replace("\\", "/")
    s = s.replace(":", "\\:")
    s = s.replace("'", "\\'")
    return s


def build_clip_command(
    input_path: str | Path,
    output_path: str | Path,
    *,
    start: float,
    duration: float,
    reframe: ReframeConfig,
    ass_path: str | None = None,
    ffmpeg: str = "ffmpeg",
    crf: int = 20,
    preset: str = "veryfast",
) -> list[str]:
    """Assemble the full ffmpeg argv to render one reframed, captioned clip."""
    if duration <= 0:
        raise ValueError("duration must be > 0")
    filtergraph, out_label = build_filtergraph(reframe, ass_path)
    return [
        ffmpeg,
        "-v", "error",
        "-y",
        "-ss", f"{start:.3f}",
        "-i", str(input_path),
        "-t", f"{duration:.3f}",
        "-filter_complex", filtergraph,
        "-map", f"[{out_label}]",
        "-map", "0:a?",            # include audio if the source has it
        "-c:v", "libx264",
        "-profile:v", "high",
        "-preset", preset,
        "-crf", str(crf),
        "-pix_fmt", "yuv420p",     # broad player/device compatibility
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        str(output_path),
    ]


def render_clip(
    input_path: str | Path,
    output_path: str | Path,
    *,
    start: float,
    duration: float,
    reframe: ReframeConfig,
    ass_path: str | None = None,
    crf: int = 20,
    preset: str = "veryfast",
) -> Path:
    """Render a single clip to ``output_path`` and return it."""
    ffmpeg = require_tool("ffmpeg")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = build_clip_command(
        input_path,
        output_path,
        start=start,
        duration=duration,
        reframe=reframe,
        ass_path=ass_path,
        ffmpeg=ffmpeg,
        crf=crf,
        preset=preset,
    )
    run(cmd)
    return Path(output_path)
