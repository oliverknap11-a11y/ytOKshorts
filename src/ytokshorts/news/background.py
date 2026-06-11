"""Backgrounds for news Shorts: a drawn football pitch, or user-supplied media.

The pitch is rendered procedurally with Pillow (no assets, no rights issues).
Users can instead point at their own image / video / folder via config or
``--background``; this module just classifies and resolves those.
"""

from __future__ import annotations

from pathlib import Path

from ..errors import MissingDependencyError, YtokshortsError

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v", ".gif"}


def classify(path: str | Path) -> str | None:
    """Return ``"image"`` or ``"video"`` for a media path, or None if unknown."""
    ext = Path(path).suffix.lower()
    if ext in _IMAGE_EXTS:
        return "image"
    if ext in _VIDEO_EXTS:
        return "video"
    return None


def resolve_background(spec: str, index: int) -> tuple[str, str]:
    """Resolve a user background ``spec`` (file or directory) to ``(kind, path)``.

    For a directory, files are cycled by ``index`` so successive clips get
    different backgrounds.
    """
    p = Path(spec)
    if p.is_dir():
        files = sorted(f for f in p.iterdir() if classify(f))
        if not files:
            raise YtokshortsError(f"No image/video files found in background folder: {p}")
        chosen = files[index % len(files)]
    else:
        if not p.exists():
            raise YtokshortsError(f"Background file not found: {p}")
        chosen = p
    kind = classify(chosen)
    if kind is None:
        raise YtokshortsError(f"Unsupported background file type: {chosen}")
    return kind, str(chosen)


def _hex_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def render_pitch(width: int, height: int, out_path: str | Path, *, top: str, bottom: str) -> Path:
    """Draw a stylized vertical football pitch to ``out_path`` (PNG) with Pillow."""
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except ImportError as exc:
        raise MissingDependencyError(
            "pillow", extra="news", purpose="draw the football-pitch background"
        ) from exc

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Vertical green gradient, built as a 1px column then stretched (fast).
    tr, tg, tb = _hex_rgb(top)
    br, bg, bb = _hex_rgb(bottom)
    column = Image.new("RGB", (1, height))
    cpx = column.load()
    for y in range(height):
        t = y / max(1, height - 1)
        cpx[0, y] = (
            round(tr + (br - tr) * t),
            round(tg + (bg - tg) * t),
            round(tb + (bb - tb) * t),
        )
    base = column.resize((width, height)).convert("RGBA")

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Faint horizontal mow stripes.
    bands = 14
    band_h = height / bands
    for i in range(bands):
        if i % 2 == 0:
            y0 = round(i * band_h)
            y1 = round((i + 1) * band_h)
            draw.rectangle([0, y0, width, y1], fill=(255, 255, 255, 10))

    # White pitch markings.
    line = (255, 255, 255, 150)
    w = max(3, width // 180)
    m = round(width * 0.07)
    cx, cy = width / 2, height / 2

    draw.rectangle([m, m, width - m, height - m], outline=line, width=w)          # boundary
    draw.line([m, cy, width - m, cy], fill=line, width=w)                          # halfway line
    cr = round(width * 0.13)
    draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], outline=line, width=w)      # centre circle
    sp = max(4, w)
    draw.ellipse([cx - sp, cy - sp, cx + sp, cy + sp], fill=line)                  # centre spot

    # Penalty + goal boxes, top and bottom.
    pen_w, pen_h = round(width * 0.5), round(height * 0.12)
    goal_w, goal_h = round(width * 0.26), round(height * 0.055)
    for top_box in (True, False):
        if top_box:
            y_pen = [cx - pen_w / 2, m, cx + pen_w / 2, m + pen_h]
            y_goal = [cx - goal_w / 2, m, cx + goal_w / 2, m + goal_h]
        else:
            y_pen = [cx - pen_w / 2, height - m - pen_h, cx + pen_w / 2, height - m]
            y_goal = [cx - goal_w / 2, height - m - goal_h, cx + goal_w / 2, height - m]
        draw.rectangle(y_pen, outline=line, width=w)
        draw.rectangle(y_goal, outline=line, width=w)

    base.alpha_composite(overlay)
    base.convert("RGB").save(out)
    return out
