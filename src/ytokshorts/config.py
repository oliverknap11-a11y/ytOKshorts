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
class NewsConfig:
    """The news-to-Short generator: feed → AI script → voiceover → captions."""

    # A free football RSS feed. Override with any RSS 2.0 sports feed.
    feed: str = "https://feeds.bbci.co.uk/sport/football/rss.xml"
    # How many stories to turn into Shorts per run.
    count: int = 3
    # Claude model used to write the scripts (only when LLM scripting is on).
    model: str = "claude-opus-4-8"
    # Reasoning effort: low | medium | high | max. Low is plenty for short scripts.
    effort: str = "low"
    # edge-tts neural voice for the AI voiceover (free, no API key).
    voice: str = "en-US-GuyNeural"
    # Rough word budget per Short (~60 words ≈ 25s of speech).
    words_target: int = 60
    # Words shown per on-screen caption chunk (bold, word-by-word feel).
    caption_words: int = 3
    # Caption layout: "stack" builds subtitles down the screen (each line stays
    # as the next appears under it); "pop" shows one centered chunk at a time.
    caption_style: str = "stack"
    # Background: empty = a drawn football pitch; or a path to an image/video/folder
    # you own or are licensed to use (cover-cropped to 9:16).
    background: str = ""
    # Darkening applied over image/video backgrounds (0–1) so captions stay legible.
    scrim: float = 0.4
    # Pitch / gradient colours (top → bottom), as #RRGGBB.
    bg_top: str = "#1B6B34"
    bg_bottom: str = "#0A2A14"
    # Caption pop/fade animation and gold number highlighting.
    animate: bool = True
    emphasize: bool = True

    def __post_init__(self) -> None:
        if self.effort not in ("low", "medium", "high", "max"):
            raise ConfigError("news.effort must be one of: low, medium, high, max")
        if self.count < 1:
            raise ConfigError("news.count must be >= 1")
        if self.words_target < 10:
            raise ConfigError("news.words_target must be >= 10")
        if self.caption_words < 1:
            raise ConfigError("news.caption_words must be >= 1")
        if self.caption_style not in ("stack", "pop"):
            raise ConfigError("news.caption_style must be 'stack' or 'pop'")
        if not 0.0 <= self.scrim <= 1.0:
            raise ConfigError("news.scrim must be between 0 and 1")


@dataclass
class AvatarConfig:
    """An AI presenter composited in front of the pitch (news Shorts only).

    Two engines: ``clips`` overlays per-country presenter videos you supply
    (free; you render the lip-synced looks yourself), and ``heygen`` generates a
    lip-synced talking head per story via the HeyGen API (paid, needs a key).
    """

    enabled: bool = False
    # "clips"  — overlay per-country presenter clips you supply (free)
    # "photo"  — lip-sync per-country still images via a provider (your own avatar)
    # "local"  — lip-sync per-country stills with a LOCAL tool (SadTalker), free
    # "heygen" — generate from a HeyGen-hosted avatar_id
    mode: str = "clips"
    # clips mode: a folder with <country>.mp4 (e.g. england.mp4) + neutral.mp4
    clips_dir: str = "presenters"
    # photo mode: a folder with <country>.png (e.g. portugal.png) + neutral.png
    photo_dir: str = "avatars"
    # photo/local: matte the subject onto a green screen so we can key her onto the
    # pitch (set False if your images already have a green/transparent background).
    green_matte: bool = True
    # Framing of a still before lip-sync: "auto" crops a full-body shot to head &
    # shoulders (so the talking face is large); "upper" always crops; "full" never.
    framing: str = "auto"
    use_avatar_iv: bool = True          # HeyGen Avatar IV motion engine (photo mode)
    # local mode (SadTalker etc.): the command run per clip, with {image} {audio}
    # {result_dir} substituted, and the directory to run it in.
    local_command: str = (
        'python inference.py --source_image "{image}" --driven_audio "{audio}" '
        '--result_dir "{result_dir}" --still --preprocess full'
    )
    local_cwd: str = "SadTalker"
    # API key env var, plus heygen-mode country -> avatar_id map.
    api_key_env: str = "HEYGEN_API_KEY"
    avatar_map: dict = field(default_factory=dict)   # country -> HeyGen avatar_id
    neutral_avatar: str = ""                          # avatar_id for neutral / your-logo kit
    # Green-screen key colour to drop out of the presenter ("" = alpha video, no key).
    chroma_color: str = "#00FF00"
    chroma_similarity: float = 0.18
    chroma_blend: float = 0.10
    # Presenter size (fraction of frame height) and placement.
    scale: float = 0.62
    position: str = "bottom"            # "bottom" | "center"
    # Where subtitles sit when a presenter is present (above her head by default).
    subtitles: str = "top"              # "top" | "center" | "full"

    def __post_init__(self) -> None:
        if self.mode not in ("clips", "photo", "local", "heygen"):
            raise ConfigError("avatar.mode must be 'clips', 'photo', 'local', or 'heygen'")
        if self.framing not in ("auto", "upper", "full"):
            raise ConfigError("avatar.framing must be 'auto', 'upper', or 'full'")
        if self.position not in ("bottom", "center"):
            raise ConfigError("avatar.position must be 'bottom' or 'center'")
        if self.subtitles not in ("top", "center", "full"):
            raise ConfigError("avatar.subtitles must be 'top', 'center', or 'full'")
        if not 0.1 < self.scale <= 1.0:
            raise ConfigError("avatar.scale must be in (0.1, 1.0]")


@dataclass
class Config:
    """Top-level configuration assembled from all stages."""

    download: DownloadConfig = field(default_factory=DownloadConfig)
    highlights: HighlightConfig = field(default_factory=HighlightConfig)
    caption: CaptionConfig = field(default_factory=CaptionConfig)
    reframe: ReframeConfig = field(default_factory=ReframeConfig)
    upload: UploadConfig = field(default_factory=UploadConfig)
    news: NewsConfig = field(default_factory=NewsConfig)
    avatar: AvatarConfig = field(default_factory=AvatarConfig)
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
    "NewsConfig": NewsConfig,
    "AvatarConfig": AvatarConfig,
}
