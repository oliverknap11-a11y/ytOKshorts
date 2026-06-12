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


def subject_bbox(image):
    """Bounding box (left, top, right, bottom) of the non-transparent subject.

    Returns None if the image has no alpha or is fully transparent.
    """
    if image.mode != "RGBA":
        return None
    return image.getchannel("A").getbbox()


def crop_upper_body(image, keep: float = 0.55):
    """Crop an RGBA cutout to the subject's head + upper body (pure-ish).

    ``keep`` is the fraction of the subject's height (from the top of the head
    down) to retain, so a tall full-body shot becomes a head-and-shoulders frame
    with a large, lip-syncable face. No-op if there's no subject alpha.
    """
    box = subject_bbox(image)
    if box is None:
        return image
    left, top, right, bottom = box
    new_bottom = top + max(1, round((bottom - top) * keep))
    # Widen slightly so shoulders aren't clipped, clamped to the image.
    pad = round((right - left) * 0.12)
    left = max(0, left - pad)
    right = min(image.width, right + pad)
    return image.crop((left, top, right, min(new_bottom, image.height)))


def _should_crop(image, framing: str) -> bool:
    """Decide whether to crop to upper body for the given framing policy."""
    if framing == "full":
        return False
    if framing == "upper":
        return True
    # auto: crop only clearly full-body shots (tall subject bounding box).
    box = subject_bbox(image)
    if box is None:
        return False
    left, top, right, bottom = box
    height, width = bottom - top, max(1, right - left)
    return height / width > 2.0


def to_green_screen(
    image_path: str | Path,
    out_path: str | Path,
    *,
    color: str = "#00FF00",
    remove_background: bool = True,
    framing: str = "auto",
) -> Path:
    """Write a green-screen (optionally upper-body-cropped) version of an image.

    When ``remove_background`` is True the subject is cut out with ``rembg``;
    ``framing`` then optionally crops a full-body shot to head-and-shoulders so
    the talking face is large. The result is composited over ``color``.
    """
    from PIL import Image  # part of the news/avatar extras

    src = Image.open(image_path)
    if remove_background and (src.mode != "RGBA" or _is_opaque(src)):
        src = _remove_background(src)

    if src.mode == "RGBA" and _should_crop(src, framing):
        src = crop_upper_body(src)

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
