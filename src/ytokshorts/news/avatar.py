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
HEYGEN_GENERATE = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS = "https://api.heygen.com/v1/video_status.get"
HEYGEN_UPLOAD = "https://upload.heygen.com/v1/asset"


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


def parse_status(data: dict) -> tuple[str, str | None]:
    """Extract ``(status, video_url)`` from a HeyGen status.get response (pure)."""
    payload = data.get("data", data)
    return payload.get("status", "unknown"), payload.get("video_url")


# --------------------------------------------------------------------------- #
# heygen mode (HTTP — lazy, isolated)
# --------------------------------------------------------------------------- #

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
