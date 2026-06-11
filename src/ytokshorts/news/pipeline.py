"""Orchestrate the football-news → Shorts pipeline.

    fetch feed → (Claude) script → edge-tts voiceover → caption + compose →
    (optional) schedule/upload → manifest
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .. import media as media_mod
from .. import upload as upload_mod
from ..config import Config
from ..errors import MissingDependencyError
from ..external import require_tool, run
from . import avatar as avatar_mod
from . import background as background_mod
from . import compose as compose_mod
from . import feeds as feeds_mod
from . import portrait as portrait_mod
from . import script as script_mod
from . import tts as tts_mod
from .country import detect_country

log = logging.getLogger("ytokshorts")


@dataclass
class NewsClip:
    """One produced news Short and its metadata."""

    index: int
    title: str
    script: str
    source_link: str
    file: str
    duration: float
    publish_at: str | None = None
    video_id: str | None = None
    country: str = ""


def run_news_pipeline(
    config: Config,
    *,
    count: int | None = None,
    use_llm: bool = True,
    do_upload: bool | None = None,
) -> dict:
    """Generate news Shorts and return a manifest dict (also written to disk)."""
    news = config.news
    n = count or news.count

    work = Path(config.work_dir)
    clips_dir = work / "news"
    clips_dir.mkdir(parents=True, exist_ok=True)
    require_tool("ffmpeg")  # fail early with a friendly message if it's missing

    log.info("Fetching feed: %s", news.feed)
    items = feeds_mod.fetch_feed(news.feed)
    if not items:
        raise ValueError(f"No stories found in feed: {news.feed}")
    items = items[:n]
    log.info("Building %d Short(s) from the top stories.", len(items))

    schedule = upload_mod.compute_schedule_times(
        config.upload.schedule_start, config.upload.interval_hours, len(items)
    )

    # Background: a generated football pitch by default; user media if configured.
    default_bg = _default_background(config, clips_dir)

    results: list[NewsClip] = []
    for i, item in enumerate(items):
        log.info("Story %d/%d: %s", i + 1, len(items), item.title)
        result = script_mod.generate_script(item, news, use_llm=use_llm)

        audio_path = clips_dir / f"news_{i + 1:02d}.mp3"
        log.info("  Synthesizing voiceover...")
        cues = tts_mod.synthesize(result.script, audio_path, voice=news.voice)

        duration = _audio_duration(audio_path, cues)
        if not cues:
            log.warning(
                "TTS returned no word timings; distributing captions evenly "
                "across the voiceover."
            )
            cues = tts_mod.even_cues(result.script, duration)
        captions = compose_mod.group_words_into_captions(cues, news.caption_words)

        # Optional AI presenter (country-specific kit), composited over the pitch.
        presenter, country = _make_presenter(config, item, audio_path, clips_dir, i)
        band = config.avatar.subtitles if presenter else "full"

        ass_path = clips_dir / f"news_{i + 1:02d}.ass"
        ass_path.write_text(
            compose_mod.build_news_ass(
                result.title, captions,
                width=config.reframe.width, height=config.reframe.height,
                duration=duration, font=config.caption.font,
                animate=news.animate, emphasize=news.emphasize,
                style=news.caption_style, band=band,
            )
        )

        background = (
            background_mod.resolve_background(news.background, i)
            if news.background else default_bg
        )
        out_path = clips_dir / f"news_{i + 1:02d}.mp4"
        log.info("  Rendering -> %s", out_path.name)
        if presenter:
            pres_path, has_audio = presenter
            av = config.avatar
            cmd = compose_mod.build_presenter_compose_command(
                ass_path, pres_path, out_path,
                width=config.reframe.width, height=config.reframe.height,
                duration=duration, bg_top=news.bg_top, bg_bottom=news.bg_bottom,
                background=background, scrim=news.scrim,
                presenter_has_audio=has_audio,
                audio_path=None if has_audio else audio_path,
                chroma_color=av.chroma_color, chroma_similarity=av.chroma_similarity,
                chroma_blend=av.chroma_blend, scale=av.scale, position=av.position,
            )
        else:
            cmd = compose_mod.build_compose_command(
                audio_path, ass_path, out_path,
                width=config.reframe.width, height=config.reframe.height,
                duration=duration, bg_top=news.bg_top, bg_bottom=news.bg_bottom,
                background=background, scrim=news.scrim,
            )
        run(cmd)

        results.append(
            NewsClip(
                index=i + 1,
                title=result.title,
                script=result.script,
                source_link=item.link,
                file=str(out_path),
                duration=round(duration, 3),
                publish_at=schedule[i],
                country=country or "",
            )
        )

    should_upload = config.upload.enabled if do_upload is None else do_upload
    if should_upload:
        _upload_clips(results, config)

    manifest = {
        "feed": news.feed,
        "model": news.model if use_llm else "headline-fallback",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clips": [asdict(r) for r in results],
    }
    manifest_path = work / "news_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("Wrote manifest with %d clip(s) -> %s", len(results), manifest_path)
    return manifest


def _make_presenter(
    config: Config, item, audio_path: Path, clips_dir: Path, index: int
) -> tuple[tuple[Path, bool] | None, str | None]:
    """Return ``((presenter_path, has_audio), country)`` or ``(None, country)``.

    ``has_audio`` is True for HeyGen output (lip-synced to our audio, audio
    baked in) and False for user-supplied loop clips (we keep our voiceover).
    """
    av = config.avatar
    if not av.enabled:
        return None, None

    country = detect_country(f"{item.title} {item.summary}")
    if av.mode == "heygen":
        avatar_id = avatar_mod.avatar_id_for_country(country, av)
        out = clips_dir / f"presenter_{index + 1:02d}.mp4"
        avatar_mod.generate_presenter(
            audio_path, avatar_id, av,
            width=config.reframe.width, height=config.reframe.height, out_path=out,
        )
        return (out, True), country

    if av.mode == "photo":
        photo = avatar_mod.resolve_photo(country, av)
        if photo is None:
            log.warning(
                "No avatar image for '%s' in %s; rendering without a presenter.",
                country or "neutral", av.photo_dir,
            )
            return None, country
        green = clips_dir / f"_avatar_{country or 'neutral'}.png"
        if not green.exists():
            portrait_mod.to_green_screen(
                photo, green, color=av.chroma_color or "#00FF00",
                remove_background=av.green_matte,
            )
        out = clips_dir / f"presenter_{index + 1:02d}.mp4"
        avatar_mod.generate_from_photo(
            green, audio_path, av,
            width=config.reframe.width, height=config.reframe.height, out_path=out,
        )
        return (out, True), country

    # clips mode: overlay a per-country loop you supplied (our voiceover is kept).
    clip = avatar_mod.resolve_presenter_clip(country, av)
    if clip is None:
        log.warning(
            "No presenter clip for '%s' in %s; rendering without a presenter.",
            country or "neutral", av.clips_dir,
        )
        return None, country
    return (clip, False), country


def _default_background(config: Config, clips_dir: Path) -> tuple[str, str] | None:
    """Render the football-pitch background once; None falls back to a gradient."""
    pitch = clips_dir / "_pitch.png"
    if not pitch.exists():
        try:
            background_mod.render_pitch(
                config.reframe.width, config.reframe.height, pitch,
                top=config.news.bg_top, bottom=config.news.bg_bottom,
            )
        except MissingDependencyError as exc:
            log.warning("%s — using a plain gradient background instead.", exc)
            return None
    return ("image", str(pitch))


def _audio_duration(audio_path: Path, cues: list[tts_mod.WordCue]) -> float:
    """Best-effort audio duration: ffprobe, falling back to the last word cue."""
    try:
        info = media_mod.probe(audio_path)
        if info.duration > 0:
            return info.duration + 0.4  # small tail so the last word isn't clipped
    except Exception:  # noqa: BLE001 - probe is best-effort here
        pass
    if cues:
        return cues[-1].end + 0.6
    return 1.0


def _upload_clips(results: list[NewsClip], config: Config) -> None:
    """Authenticate once and upload every produced news Short."""
    log.info("Authenticating with YouTube...")
    service = upload_mod.get_authenticated_service(config.upload)
    for r in results:
        description = f"Source: {r.source_link}" if r.source_link else ""
        resource = upload_mod.build_video_resource(
            r.title, description, config.upload, publish_at=r.publish_at
        )
        response = upload_mod.upload_video(service, r.file, resource)
        r.video_id = response.get("id")
