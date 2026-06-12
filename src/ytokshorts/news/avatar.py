"""AI presenter generation/selection.

Two engines:

- ``clips``  — pick a per-country presenter video you supplied (free).
- ``heygen`` — generate a lip-synced talking head per story via the HeyGen API
  (paid; needs an API key). The presenter is rendered on a green background so we
  can chroma-key it onto the pitch ourselves.

The request/response shaping is pure (and unit-tested); the HTTP calls are
isolated and lazy. The HeyGen calls follow the documented v2 generate / v1
status endpoints; they are not exercised against a live key in CI, so treat
field names as the documented best-effort and adjust if the API shifts.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request
from pathlib import Path

from ..config import AvatarConfig
from ..errors import YtokshortsError

log = logging.getLogger("ytokshorts")

_VIDEO_EXTS = (".mp4", ".mov", ".webm", ".mkv", ".m4v")
_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")
HEYGEN_GENERATE = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS = "https://api.heygen.com/v1/video_status.get"
HEYGEN_UPLOAD = "https://upload.heygen.com/v1/asset"
HEYGEN_UPLOAD_PHOTO = "https://upload.heygen.com/v1/talking_photo"


# --------------------------------------------------------------------------- #
# clips mode (pure)
# --------------------------------------------------------------------------- #

def resolve_presenter_clip(country: str | None, config: AvatarConfig) -> Path | None:
    """Find the presenter clip for ``country`` (or the neutral clip) on disk.

    Looks for ``<clips_dir>/<country>.<ext>``; falls back to
    ``<clips_dir>/neutral.<ext>`` for neutral stories or a missing kit.
    """
    base = Path(config.clips_dir)
    for key in ([country] if country else []) + ["neutral"]:
        if not key:
            continue
        for ext in _VIDEO_EXTS:
            cand = base / f"{key}{ext}"
            if cand.exists():
                return cand
    return None


def avatar_id_for_country(country: str | None, config: AvatarConfig) -> str:
    """Pick the HeyGen avatar_id for a country, or the neutral/your-logo avatar."""
    if country and country in config.avatar_map:
        return config.avatar_map[country]
    if config.neutral_avatar:
        return config.neutral_avatar
    raise YtokshortsError(
        "No HeyGen avatar configured for this story. Set avatar.neutral_avatar "
        "(and avatar.avatar_map per country)."
    )


# --------------------------------------------------------------------------- #
# heygen mode (pure request/response shaping)
# --------------------------------------------------------------------------- #

def build_generate_payload(
    avatar_id: str, audio_url: str, *, width: int, height: int, chroma_color: str
) -> dict:
    """Build the HeyGen v2 /video/generate body: avatar lip-synced to our audio."""
    background = (
        {"type": "color", "value": chroma_color}
        if chroma_color
        else {"type": "transparent"}
    )
    return {
        "video_inputs": [
            {
                "character": {"type": "avatar", "avatar_id": avatar_id, "avatar_style": "normal"},
                "voice": {"type": "audio", "audio_url": audio_url},
                "background": background,
            }
        ],
        "dimension": {"width": width, "height": height},
    }


def build_talking_photo_payload(
    talking_photo_id: str, audio_url: str, *, width: int, height: int,
    chroma_color: str, use_avatar_iv: bool = True,
) -> dict:
    """Build the /video/generate body for a *talking photo* (your uploaded image)."""
    background = (
        {"type": "color", "value": chroma_color} if chroma_color else {"type": "transparent"}
    )
    character: dict = {"type": "talking_photo", "talking_photo_id": talking_photo_id}
    if use_avatar_iv:
        character["use_avatar_iv_model"] = True
    return {
        "video_inputs": [
            {
                "character": character,
                "voice": {"type": "audio", "audio_url": audio_url},
                "background": background,
            }
        ],
        "dimension": {"width": width, "height": height},
    }


def parse_status(data: dict) -> tuple[str, str | None]:
    """Extract ``(status, video_url)`` from a HeyGen status.get response (pure)."""
    payload = data.get("data", data)
    return payload.get("status", "unknown"), payload.get("video_url")


def resolve_photo(country: str | None, config: AvatarConfig) -> Path | None:
    """Find the per-country avatar still (or the neutral still) in ``photo_dir``."""
    base = Path(config.photo_dir)
    for key in ([country] if country else []) + ["neutral"]:
        for ext in _IMAGE_EXTS:
            cand = base / f"{key}{ext}"
            if cand.exists():
                return cand
    return None


# --------------------------------------------------------------------------- #
# heygen mode (HTTP — lazy, isolated)
# --------------------------------------------------------------------------- #

def build_local_command(template: str, image: str | Path, audio: str | Path,
                        result_dir: str | Path) -> str:
    """Substitute {image}/{audio}/{result_dir} into a local lip-sync command (pure)."""
    return template.format(
        image=str(Path(image).resolve()),
        audio=str(Path(audio).resolve()),
        result_dir=str(Path(result_dir).resolve()),
    )


def newest_video(directory: str | Path) -> Path:
    """Return the most recently modified video file under ``directory``."""
    base = Path(directory)
    vids = [p for p in base.rglob("*") if p.suffix.lower() in _VIDEO_EXTS]
    if not vids:
        raise YtokshortsError(f"Local lip-sync produced no video in {base}")
    return max(vids, key=lambda p: p.stat().st_mtime)


def run_local_lipsync(
    image_path: str | Path,
    audio_path: str | Path,
    out_path: str | Path,
    config: AvatarConfig,
    *,
    result_dir: str | Path,
) -> Path:
    """Run the configured local tool (e.g. SadTalker) and return the output clip."""
    import shutil
    import subprocess

    result = Path(result_dir)
    result.mkdir(parents=True, exist_ok=True)
    command = build_local_command(config.local_command, image_path, audio_path, result)
    cwd = config.local_cwd or None
    log.info("  Local lip-sync: %s", command)
    proc = subprocess.run(command, shell=True, cwd=cwd)  # noqa: S602 - user-configured command
    if proc.returncode != 0:
        raise YtokshortsError(
            f"Local lip-sync command failed (exit {proc.returncode}). "
            f"Check avatar.local_command / avatar.local_cwd ({config.local_cwd!r})."
        )
    produced = newest_video(result)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(produced, out)
    return out


def _api_key(config: AvatarConfig) -> str:
    import os

    key = os.environ.get(config.api_key_env)
    if not key:
        raise YtokshortsError(
            f"HeyGen API key not found. Set the {config.api_key_env} environment variable."
        )
    return key


def _request(url: str, *, api_key: str, method: str, data: bytes | None = None,
             content_type: str | None = None) -> dict:
    headers = {"x-api-key": api_key, "accept": "application/json"}
    if content_type:
        headers["content-type"] = content_type
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            return json.loads(resp.read().decode("utf-8", "replace"))
    except Exception as exc:  # urllib raises many error types
        raise YtokshortsError(f"HeyGen API request to {url} failed: {exc}") from exc


def upload_audio(path: str | Path, api_key: str) -> str:
    """Upload an mp3 to HeyGen and return a hosted audio URL for the voice input."""
    raw = Path(path).read_bytes()
    data = _request(HEYGEN_UPLOAD, api_key=api_key, method="POST", data=raw,
                    content_type="audio/mpeg")
    payload = data.get("data", data)
    url = payload.get("url") or payload.get("asset_url")
    if not url:
        raise YtokshortsError(f"HeyGen upload returned no audio URL: {data}")
    return url


def upload_talking_photo(image_path: str | Path, api_key: str) -> str:
    """Upload a still image to HeyGen and return its ``talking_photo_id``."""
    raw = Path(image_path).read_bytes()
    ctype = "image/png" if str(image_path).lower().endswith(".png") else "image/jpeg"
    data = _request(HEYGEN_UPLOAD_PHOTO, api_key=api_key, method="POST", data=raw,
                    content_type=ctype)
    payload = data.get("data", data)
    tp_id = payload.get("talking_photo_id") or payload.get("id")
    if not tp_id:
        raise YtokshortsError(f"HeyGen talking-photo upload returned no id: {data}")
    return tp_id


def submit_video(payload: dict, api_key: str) -> str:
    data = _request(HEYGEN_GENERATE, api_key=api_key, method="POST",
                    data=json.dumps(payload).encode(), content_type="application/json")
    body = data.get("data", data)
    video_id = body.get("video_id") or body.get("id")
    if not video_id:
        raise YtokshortsError(f"HeyGen generate returned no video_id: {data}")
    return video_id


def poll_status(video_id: str, api_key: str, *, timeout: float = 600.0, interval: float = 10.0) -> str:
    """Poll until the video is ``completed`` and return its download URL."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        data = _request(f"{HEYGEN_STATUS}?video_id={video_id}", api_key=api_key, method="GET")
        status, url = parse_status(data)
        if status == "completed" and url:
            return url
        if status == "failed":
            raise YtokshortsError(f"HeyGen video {video_id} failed: {data}")
        time.sleep(interval)
    raise YtokshortsError(f"HeyGen video {video_id} did not complete within {timeout:.0f}s")


def _download(url: str, out_path: str | Path) -> Path:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=120) as resp, open(out, "wb") as f:  # noqa: S310
        f.write(resp.read())
    return out


def generate_presenter(
    audio_path: str | Path,
    avatar_id: str,
    config: AvatarConfig,
    *,
    width: int,
    height: int,
    out_path: str | Path,
) -> Path:
    """Generate a lip-synced presenter clip (green background) via HeyGen."""
    key = _api_key(config)
    log.info("  HeyGen: uploading audio + generating presenter (avatar %s)...", avatar_id)
    audio_url = upload_audio(audio_path, key)
    payload = build_generate_payload(
        avatar_id, audio_url, width=width, height=height, chroma_color=config.chroma_color
    )
    video_id = submit_video(payload, key)
    url = poll_status(video_id, key)
    return _download(url, out_path)


def generate_from_photo(
    image_path: str | Path,
    audio_path: str | Path,
    config: AvatarConfig,
    *,
    width: int,
    height: int,
    out_path: str | Path,
) -> Path:
    """Lip-sync a still image to our audio via HeyGen Talking Photo (green bg)."""
    key = _api_key(config)
    log.info("  HeyGen: uploading photo + audio, lip-syncing your avatar...")
    talking_photo_id = upload_talking_photo(image_path, key)
    audio_url = upload_audio(audio_path, key)
    payload = build_talking_photo_payload(
        talking_photo_id, audio_url, width=width, height=height,
        chroma_color=config.chroma_color, use_avatar_iv=config.use_avatar_iv,
    )
    video_id = submit_video(payload, key)
    url = poll_status(video_id, key)
    return _download(url, out_path)
