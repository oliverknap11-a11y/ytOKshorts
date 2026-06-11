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
from ..external import require_tool, run
from . import compose as compose_mod
from . import feeds as feeds_mod
from . import script as script_mod
from . import tts as tts_mod

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

    results: list[NewsClip] = []
    for i, item in enumerate(items):
        log.info("Story %d/%d: %s", i + 1, len(items), item.title)
        result = script_mod.generate_script(item, news, use_llm=use_llm)

        audio_path = clips_dir / f"news_{i + 1:02d}.mp3"
        log.info("  Synthesizing voiceover...")
        cues = tts_mod.synthesize(result.script, audio_path, voice=news.voice)

        duration = _audio_duration(audio_path, cues)
        captions = compose_mod.group_words_into_captions(cues, news.caption_words)
        ass_path = clips_dir / f"news_{i + 1:02d}.ass"
        ass_path.write_text(
            compose_mod.build_news_ass(
                result.title, captions,
                width=config.reframe.width, height=config.reframe.height,
                duration=duration, font=config.caption.font,
            )
        )

        out_path = clips_dir / f"news_{i + 1:02d}.mp4"
        log.info("  Rendering -> %s", out_path.name)
        cmd = compose_mod.build_compose_command(
            audio_path, ass_path, out_path,
            width=config.reframe.width, height=config.reframe.height,
            duration=duration, bg_top=news.bg_top, bg_bottom=news.bg_bottom,
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
