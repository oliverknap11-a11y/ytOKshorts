"""Prepare an avatar still for chroma-keying: subject onto a green screen.

The lip-sync provider animates whatever image we send, so if we bake a solid
green background behind the subject, the resulting talking video keys cleanly
onto the pitch. Background removal uses ``rembg`` (lazy); the pixel compositing
is pure Pillow and unit-tested.
"""

from __future__ import annotations

from pathlib import Path

from ..errors import MissingDependencyError


def _hex_rgb(value: str) -> tuple[int, int, int]:
    v = value.strip().lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16)


def composite_on_color(image, color: str):
    """Composite an RGBA Pillow image over a solid ``color`` background (pure).

    Returns an RGB image. If the input has no usable alpha it's returned on the
    colour unchanged (fully opaque), which is a no-op for already-keyed images.
    """
    from PIL import Image  # local: only needed when a presenter is used

    rgba = image.convert("RGBA")
    bg = Image.new("RGBA", rgba.size, (*_hex_rgb(color), 255))
    bg.alpha_composite(rgba)
    return bg.convert("RGB")


def to_green_screen(
    image_path: str | Path,
    out_path: str | Path,
    *,
    color: str = "#00FF00",
    remove_background: bool = True,
) -> Path:
    """Write a green-screen version of ``image_path`` to ``out_path``.

    When ``remove_background`` is True the subject is cut out with ``rembg``
    first; otherwise the image's own alpha (if any) is composited over green.
    """
    from PIL import Image  # part of the news/avatar extras

    src = Image.open(image_path)
    if remove_background and src.mode != "RGBA":
        src = _remove_background(src)
    elif remove_background and _is_opaque(src):
        src = _remove_background(src)

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    composite_on_color(src, color).save(out)
    return out


def _is_opaque(image) -> bool:
    """True if the image has no transparency to composite (so we must matte)."""
    if image.mode != "RGBA":
        return True
    alpha = image.getchannel("A")
    return alpha.getextrema() == (255, 255)


def _remove_background(image):
    """Cut the subject out of ``image`` with rembg, returning an RGBA image."""
    try:
        from rembg import remove  # type: ignore
    except ImportError as exc:
        raise MissingDependencyError(
            "rembg", extra="avatar",
            purpose="remove the avatar's background for green-screen keying",
        ) from exc
    return remove(image.convert("RGBA"))
