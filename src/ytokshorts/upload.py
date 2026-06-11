"""Schedule and upload finished Shorts to YouTube via the Data API v3.

The request-building and schedule-math helpers are pure and tested. The actual
OAuth + HTTP upload is isolated in :func:`get_authenticated_service` /
:func:`upload_video`, behind the optional ``upload`` extra.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .config import UploadConfig
from .errors import MissingDependencyError, YtokshortsError

log = logging.getLogger("ytokshorts")

# OAuth scope for uploading on the user's behalf.
YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]


def compute_schedule_times(
    start: str | None,
    interval_hours: float,
    count: int,
) -> list[str | None]:
    """Return ``count`` publish timestamps, spaced ``interval_hours`` apart.

    ``start`` is an ISO-8601 instant (a trailing ``Z`` is accepted; naive values
    are treated as UTC). When ``start`` is falsy, every entry is ``None`` meaning
    "publish immediately". Output is RFC-3339 UTC (``...Z``), the form the
    YouTube API expects for ``status.publishAt``.
    """
    if count < 0:
        raise ValueError("count must be >= 0")
    if not start:
        return [None] * count

    base = _parse_instant(start)
    out: list[str | None] = []
    for i in range(count):
        t = base + timedelta(hours=interval_hours * i)
        out.append(t.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    return out


def _parse_instant(value: str) -> datetime:
    """Parse an ISO-8601 instant, tolerating a trailing ``Z`` and naive values."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError as exc:
        raise YtokshortsError(
            f"Invalid schedule time {value!r}; expected ISO-8601 like "
            "'2026-06-12T09:00:00Z'"
        ) from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def build_video_resource(
    title: str,
    description: str,
    config: UploadConfig,
    *,
    publish_at: str | None = None,
) -> dict:
    """Build the YouTube ``videos.insert`` request body for one clip."""
    final_title = _apply_title_suffix(title, config.title_suffix)
    status: dict[str, object] = {
        "privacyStatus": config.privacy,
        "selfDeclaredMadeForKids": config.made_for_kids,
    }
    if publish_at:
        if config.privacy != "private":
            raise YtokshortsError(
                "Scheduled publishAt requires privacy 'private' until the time arrives"
            )
        status["publishAt"] = publish_at
    return {
        "snippet": {
            "title": final_title[:100],  # YouTube hard-caps titles at 100 chars
            "description": description,
            "tags": list(config.tags),
            "categoryId": config.category_id,
        },
        "status": status,
    }


def _apply_title_suffix(title: str, suffix: str) -> str:
    """Append ``suffix`` (e.g. ``#shorts``) unless it's already present."""
    suffix = suffix.strip()
    if not suffix or suffix.lower() in title.lower():
        return title
    return f"{title} {suffix}"


def get_authenticated_service(config: UploadConfig):
    """Build an authenticated YouTube API client, running OAuth if needed.

    On first use this opens a browser consent flow and caches the resulting
    token to ``config.token`` so later runs are non-interactive.
    """
    try:
        from google.auth.transport.requests import Request  # type: ignore
        from google.oauth2.credentials import Credentials  # type: ignore
        from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore
        from googleapiclient.discovery import build  # type: ignore
    except ImportError as exc:
        raise MissingDependencyError(
            "google-api-python-client", extra="upload", purpose="upload to YouTube"
        ) from exc

    token_path = Path(config.token)
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), YOUTUBE_UPLOAD_SCOPE)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(config.client_secrets).exists():
                raise YtokshortsError(
                    f"OAuth client secrets not found at {config.client_secrets}. "
                    "Create an OAuth client in Google Cloud Console (YouTube Data "
                    "API v3) and download the JSON."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                config.client_secrets, YOUTUBE_UPLOAD_SCOPE
            )
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json())

    return build("youtube", "v3", credentials=creds)


def upload_video(service, file_path: str | Path, resource: dict) -> dict:
    """Upload ``file_path`` with the given request ``resource`` (resumable)."""
    try:
        from googleapiclient.http import MediaFileUpload  # type: ignore
    except ImportError as exc:  # pragma: no cover - paired with get_authenticated_service
        raise MissingDependencyError(
            "google-api-python-client", extra="upload", purpose="upload to YouTube"
        ) from exc

    media = MediaFileUpload(str(file_path), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = service.videos().insert(
        part=",".join(resource.keys()),
        body=resource,
        media_body=media,
    )
    log.info("Uploading %s", file_path)
    response = None
    while response is None:
        _status, response = request.next_chunk()
    log.info("Uploaded video id=%s", response.get("id"))
    return response
