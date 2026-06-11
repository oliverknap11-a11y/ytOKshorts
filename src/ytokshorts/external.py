"""Thin, well-behaved wrappers around external command-line tools.

Everything that shells out to ffmpeg / ffprobe / yt-dlp goes through here so we
get one consistent place for "is this installed?" checks and for turning a
non-zero exit into a readable :class:`ExternalToolError`.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Sequence

from .errors import ExternalToolError

log = logging.getLogger("ytokshorts")


def tool_path(name: str) -> str | None:
    """Return the resolved path to ``name`` on PATH, or None if absent."""
    return shutil.which(name)


def require_tool(name: str, *, install_hint: str | None = None) -> str:
    """Return the path to ``name`` or raise a helpful :class:`ExternalToolError`."""
    found = tool_path(name)
    if found is None:
        hint = install_hint or _DEFAULT_HINTS.get(name, f"Install '{name}' and ensure it is on PATH.")
        raise ExternalToolError(
            f"Required tool '{name}' was not found on PATH. {hint}",
            tool=name,
        )
    return found


def run(
    cmd: Sequence[str],
    *,
    capture: bool = True,
    check: bool = True,
    cwd: str | Path | None = None,
) -> subprocess.CompletedProcess:
    """Run ``cmd``, logging it, and raise :class:`ExternalToolError` on failure.

    Returns the :class:`subprocess.CompletedProcess`. ``stdout``/``stderr`` are
    captured as text by default.
    """
    tool = cmd[0]
    log.debug("running: %s", " ".join(map(str, cmd)))
    try:
        proc = subprocess.run(
            list(map(str, cmd)),
            capture_output=capture,
            text=True,
            cwd=str(cwd) if cwd else None,
        )
    except FileNotFoundError as exc:
        raise ExternalToolError(
            f"Could not execute '{tool}': {exc}", tool=tool
        ) from exc
    if check and proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        tail = "\n".join(stderr.splitlines()[-15:]) if stderr else "(no stderr)"
        raise ExternalToolError(
            f"'{tool}' exited with code {proc.returncode}:\n{tail}",
            tool=tool,
            returncode=proc.returncode,
            stderr=stderr,
        )
    return proc


_DEFAULT_HINTS = {
    "ffmpeg": "Install ffmpeg, e.g. `apt install ffmpeg` or `brew install ffmpeg`.",
    "ffprobe": "ffprobe ships with ffmpeg, e.g. `apt install ffmpeg` or `brew install ffmpeg`.",
    "yt-dlp": "Install yt-dlp, e.g. `pip install yt-dlp` or `pipx install yt-dlp`.",
}
