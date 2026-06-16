"""Exception hierarchy for ytOKshorts.

Everything the package raises on purpose descends from :class:`YtokshortsError`
so the CLI can present a clean message (and a non-zero exit code) instead of a
traceback for expected failures.
"""

from __future__ import annotations


class YtokshortsError(Exception):
    """Base class for all errors raised intentionally by ytOKshorts."""


class ConfigError(YtokshortsError):
    """Raised when configuration is missing or invalid."""


class MissingDependencyError(YtokshortsError):
    """Raised when an optional Python dependency is needed but not installed.

    Carries the pip extra that would satisfy it so the message can tell the
    user exactly what to run.
    """

    def __init__(self, package: str, *, extra: str | None = None, purpose: str = ""):
        self.package = package
        self.extra = extra
        hint = f"pip install 'ytokshorts[{extra}]'" if extra else f"pip install {package}"
        what = f" to {purpose}" if purpose else ""
        super().__init__(f"The '{package}' package is required{what}. Install it with: {hint}")


class ExternalToolError(YtokshortsError):
    """Raised when a required external binary (ffmpeg, ffprobe, yt-dlp) fails.

    ``tool`` is the program name; ``returncode`` and ``stderr`` are populated
    when the failure came from a finished subprocess rather than a missing one.
    """

    def __init__(
        self,
        message: str,
        *,
        tool: str,
        returncode: int | None = None,
        stderr: str | None = None,
    ):
        self.tool = tool
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(message)
