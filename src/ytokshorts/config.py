"""Typed configuration for the Shorts pipeline.

Config can come from a TOML file (``ytokshorts.toml``), be overridden per-run by
CLI flags, and falls back to sensible defaults. Each stage of the pipeline owns
a small dataclass so the knobs stay discoverable and validated in one place.
"""

from __future__ import annotations

try:
    import tomllib  # Python 3.11+
except ModuleNotFoundError:  # pragma: no cover - exercised only on 3.9/3.10
    import tomli as tomllib  # type: ignore[no-redef]

from dataclasses import dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

from .errors import ConfigError


@dataclass
class DownloadConfig:
    """How source videos are fetched."""

    # yt-dlp format selector. Caps height at 1080 by default — Shorts are
    # vertical and 1080p source is plenty, while 4K just wastes bandwidth/disk.
    format: str = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
    # Optional cookies file (e.g. for age-restricted / members-only sources).
    cookies: str | None = None


@dataclass
class HighlightConfig:
    """How candidate Short segments are chosen from the source audio."""

    # Shorts must be <= 60s; we keep a little headroom by default.
    min_duration: float = 15.0
    max_duration: float = 58.0
    # How many clips to produce from one source video.
    target_count: int = 5
    # Seconds of breathing room kept between chosen segments.
    spacing: float = 5.0
    # Audio analysis window (seconds) used to build the energy curve.
    window: float = 0.5

    def __post_init__(self) -> None:
        if self.min_duration <= 0:
            raise ConfigError("highlights.min_duration must be > 0")
        if self.max_duration > 60:
            raise ConfigError("highlights.max_duration must be <= 60 (YouTube Shorts limit)")
        if self.max_duration < self.min_duration:
            raise ConfigError("highlights.max_duration must be >= min_duration")
        if self.target_count < 1:
            raise ConfigError("highlights.target_count must be >= 1")
        if self.window <= 0:
            raise ConfigError("highlights.window must be > 0")


@dataclass
class CaptionConfig:
    """Subtitle generation + burn-in styling."""

    enabled: bool = True
    # faster-whisper model size: tiny | base | small | medium | large-v3
    model: str = "base"
    # ISO 639-1 code, or None to auto-detect.
    language: str | None = None
    font: str = "Arial"
    font_size: int = 18
    # ASS primary colour as &HBBGGAA (white) and outline (black).
    primary_color: str = "&H00FFFFFF"
    outline_color: str = "&H00000000"
    outline: int = 2
    # Vertical anchor of the caption block: "bottom" | "center" | "top".
    position: str = "bottom"

    def __post_init__(self) -> None:
        if self.position not in ("bottom", "center", "top"):
            raise ConfigError("caption.position must be one of: bottom, center, top")


@dataclass
class ReframeConfig:
    """16:9 → 9:16 vertical reframing."""

    width: int = 1080
    height: int = 1920
    # "crop"      — zoom + center-crop to fill the frame (loses the sides)
    # "blur"      — fit the whole frame, fill letterbox bars with a blurred copy
    mode: str = "blur"

    def __post_init__(self) -> None:
        if self.mode not in ("crop", "blur"):
            raise ConfigError("reframe.mode must be 'crop' or 'blur'")
        if self.width <= 0 or self.height <= 0:
            raise ConfigError("reframe.width/height must be > 0")

    @property
    def aspect(self) -> float:
        return self.width / self.height


@dataclass
class UploadConfig:
    """YouTube Data API upload + scheduling."""

    enabled: bool = False
    client_secrets: str = "client_secret.json"
    token: str = "token.json"
    # "private" is the only privacy value that supports scheduled publishing.
    privacy: str = "private"
    category_id: str = "22"  # "People & Blogs"
    tags: list[str] = field(default_factory=lambda: ["shorts"])
    made_for_kids: bool = False
    # Scheduling: publish the first clip at this ISO-8601 time (UTC), then space
    # the rest out by ``interval_hours``. Leave start empty to upload immediately.
    schedule_start: str | None = None
    interval_hours: float = 24.0
    # Appended to every title so the platform treats the upload as a Short.
    title_suffix: str = "#shorts"

    def __post_init__(self) -> None:
        if self.privacy not in ("private", "unlisted", "public"):
            raise ConfigError("upload.privacy must be private, unlisted, or public")
        if self.schedule_start and self.privacy != "private":
            raise ConfigError("upload.schedule_start requires upload.privacy = 'private'")


@dataclass
class Config:
    """Top-level configuration assembled from all stages."""

    download: DownloadConfig = field(default_factory=DownloadConfig)
    highlights: HighlightConfig = field(default_factory=HighlightConfig)
    caption: CaptionConfig = field(default_factory=CaptionConfig)
    reframe: ReframeConfig = field(default_factory=ReframeConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    # Working directory for intermediate + final artifacts.
    work_dir: str = "work"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Config":
        """Build a Config from a plain dict (e.g. parsed TOML).

        Unknown keys raise rather than being silently dropped — a typo'd option
        should be loud, not a no-op.
        """
        return _build_dataclass(cls, data, path="")

    @classmethod
    def load(cls, path: str | Path | None) -> "Config":
        """Load config from ``path``; return defaults if path is None/missing."""
        if path is None:
            return cls()
        p = Path(path)
        if not p.exists():
            raise ConfigError(f"Config file not found: {p}")
        try:
            data = tomllib.loads(p.read_text())
        except tomllib.TOMLDecodeError as exc:  # pragma: no cover - message passthrough
            raise ConfigError(f"Invalid TOML in {p}: {exc}") from exc
        return cls.from_dict(data)


def _build_dataclass(cls: type, data: dict[str, Any], *, path: str) -> Any:
    """Recursively construct a (possibly nested) dataclass from a dict.

    Validates that every key in ``data`` maps to a real field and recurses into
    nested dataclass fields so e.g. ``[highlights]`` tables populate
    :class:`HighlightConfig`.
    """
    if not isinstance(data, dict):
        raise ConfigError(f"Expected a table for {path or 'config'}, got {type(data).__name__}")

    field_types = {f.name: f.type for f in fields(cls)}
    field_defaults = {f.name for f in fields(cls)}
    kwargs: dict[str, Any] = {}
    for key, value in data.items():
        if key not in field_defaults:
            where = f"{path}.{key}" if path else key
            valid = ", ".join(sorted(field_defaults))
            raise ConfigError(f"Unknown config option '{where}'. Valid keys: {valid}")
        ftype = field_types[key]
        nested = _resolve_nested_dataclass(ftype)
        if nested is not None:
            child_path = f"{path}.{key}" if path else key
            kwargs[key] = _build_dataclass(nested, value, path=child_path)
        else:
            kwargs[key] = value
    try:
        return cls(**kwargs)
    except TypeError as exc:  # pragma: no cover - defensive
        raise ConfigError(f"Could not build {cls.__name__}: {exc}") from exc


def _resolve_nested_dataclass(ftype: Any) -> type | None:
    """Return the dataclass referenced by a field type, if any.

    Field types can arrive as real classes or as forward-ref strings (because
    ``from __future__ import annotations`` is in effect). Handle the handful of
    nested config classes by name.
    """
    if is_dataclass(ftype):
        return ftype  # type: ignore[return-value]
    if isinstance(ftype, str):
        return _CONFIG_CLASSES.get(ftype)
    return None


_CONFIG_CLASSES: dict[str, type] = {
    "DownloadConfig": DownloadConfig,
    "HighlightConfig": HighlightConfig,
    "CaptionConfig": CaptionConfig,
    "ReframeConfig": ReframeConfig,
    "UploadConfig": UploadConfig,
}
