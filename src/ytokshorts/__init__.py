"""ytOKshorts — long videos in, publish-ready YouTube Shorts out.

The package is split into small, single-purpose modules:

- :mod:`ytokshorts.config`     — typed configuration and TOML loading
- :mod:`ytokshorts.download`   — fetch source videos with yt-dlp
- :mod:`ytokshorts.media`      — probe metadata / extract audio (ffprobe, ffmpeg)
- :mod:`ytokshorts.highlights` — score audio energy and pick the best segments
- :mod:`ytokshorts.captions`   — transcribe and render SRT/ASS subtitles
- :mod:`ytokshorts.clip`       — cut + vertically reframe + burn captions
- :mod:`ytokshorts.upload`     — schedule and upload to YouTube
- :mod:`ytokshorts.pipeline`   — glue that runs the whole thing end-to-end

Heavy or credential-bound dependencies (Whisper, the Google API client, numpy)
are imported lazily so the core stays importable and unit-testable without them.
"""

from .errors import (
    ConfigError,
    ExternalToolError,
    MissingDependencyError,
    YtokshortsError,
)
from .highlights import Segment, find_highlights

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "Segment",
    "find_highlights",
    "YtokshortsError",
    "ConfigError",
    "ExternalToolError",
    "MissingDependencyError",
]
