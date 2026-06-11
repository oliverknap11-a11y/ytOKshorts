"""Fetch source videos with yt-dlp."""

from __future__ import annotations

import logging
from pathlib import Path

from .config import DownloadConfig
from .errors import MissingDependencyError, YtokshortsError

log = logging.getLogger("ytokshorts")


def download(url: str, dest_dir: str | Path, config: DownloadConfig | None = None) -> Path:
    """Download ``url`` into ``dest_dir`` and return the resulting file path.

    Uses the yt-dlp Python API directly (rather than shelling out) so we can read
    back the exact output filename from the info dict.
    """
    config = config or DownloadConfig()
    try:
        import yt_dlp  # type: ignore
    except ImportError as exc:
        raise MissingDependencyError(
            "yt-dlp", purpose="download source videos"
        ) from exc

    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    ydl_opts = {
        "format": config.format,
        "outtmpl": str(dest / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        # Remux to mp4 when the chosen streams allow it, for a predictable input.
        "merge_output_format": "mp4",
    }
    if config.cookies:
        ydl_opts["cookiefile"] = config.cookies

    log.info("Downloading %s", url)
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        path = Path(ydl.prepare_filename(info))

    # prepare_filename reflects the pre-merge extension; reconcile with what
    # actually landed on disk (e.g. .mp4 after a merge/remux).
    if not path.exists():
        candidate = path.with_suffix(".mp4")
        if candidate.exists():
            path = candidate
    if not path.exists():
        matches = sorted(dest.glob(f"{info.get('id', '*')}.*"))
        if matches:
            path = matches[0]
    if not path.exists():
        raise YtokshortsError(f"Download finished but output file was not found for {url}")

    log.info("Downloaded to %s", path)
    return path
