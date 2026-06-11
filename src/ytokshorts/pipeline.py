"""End-to-end orchestration: source video → published-ready Shorts.

``run_pipeline`` ties the stages together:

    download → probe → analyze audio → pick highlights → (transcribe) →
    render vertical captioned clips → (schedule/upload) → write a manifest.

Each stage lives in its own module; this file is just the glue and the
bookkeeping (work dirs, titles, schedule assignment, manifest)."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import captions as captions_mod
from . import clip as clip_mod
from . import download as download_mod
from . import media as media_mod
from . import upload as upload_mod
from .config import Config
from .highlights import Segment, compute_window_energies, find_highlights

log = logging.getLogger("ytokshorts")


@dataclass
class ClipResult:
    """One produced Short and everything we know about it."""

    index: int
    start: float
    end: float
    duration: float
    score: float
    file: str
    title: str
    publish_at: str | None = None
    video_id: str | None = None


def even_segments(duration: float, cfg) -> list[Segment]:
    """Fallback selection: evenly spaced clips when there's no usable audio.

    Used when the source has no audio track (nothing to score), so we still emit
    sensible candidates instead of nothing.
    """
    clip_len = min(cfg.max_duration, duration)
    if clip_len < cfg.min_duration:
        return []
    count = min(cfg.target_count, max(1, int(duration // clip_len)))
    if count == 1:
        return [Segment(start=0.0, end=round(clip_len, 3), score=1.0)]
    # Distribute starts across the timeline, leaving room for the last clip.
    span = duration - clip_len
    step = span / (count - 1)
    return [
        Segment(start=round(i * step, 3), end=round(i * step + clip_len, 3), score=1.0)
        for i in range(count)
    ]


def select_segments(source_video: Path, info: media_mod.MediaInfo, cfg: Config) -> list[Segment]:
    """Choose highlight segments, falling back to even spacing for silent video."""
    if not info.has_audio:
        log.info("Source has no audio track; using evenly spaced segments.")
        return even_segments(info.duration, cfg.highlights)

    log.info("Analyzing audio energy...")
    pcm = media_mod.extract_pcm(source_video)
    energies = compute_window_energies(
        pcm, media_mod.ANALYSIS_SAMPLE_RATE, cfg.highlights.window
    )
    segments = find_highlights(
        energies,
        cfg.highlights.window,
        min_duration=cfg.highlights.min_duration,
        max_duration=cfg.highlights.max_duration,
        target_count=cfg.highlights.target_count,
        spacing=cfg.highlights.spacing,
    )
    if not segments:
        log.info("No strong highlights found; using evenly spaced segments.")
        return even_segments(info.duration, cfg.highlights)
    return segments


def run_pipeline(
    source: str,
    config: Config,
    *,
    source_is_url: bool = True,
    do_upload: bool | None = None,
    title_template: str = "{source} — Highlight {n}",
) -> dict:
    """Run the full pipeline and return a manifest dict (also written to disk).

    ``do_upload`` overrides ``config.upload.enabled`` when set. ``title_template``
    accepts ``{source}`` and ``{n}`` (1-based clip number).
    """
    work = Path(config.work_dir)
    clips_dir = work / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    # 1. Acquire the source video.
    if source_is_url:
        source_video = download_mod.download(source, work / "download", config.download)
    else:
        source_video = Path(source)
        if not source_video.exists():
            raise FileNotFoundError(f"Source video not found: {source_video}")
    source_title = source_video.stem

    # 2. Probe + 3. select highlight segments.
    info = media_mod.probe(source_video)
    log.info("Source: %.1fs, %dx%d, audio=%s", info.duration, info.width, info.height, info.has_audio)
    segments = select_segments(source_video, info, config)
    if not segments:
        raise ValueError(
            "Source is too short to produce a Short "
            f"(needs >= {config.highlights.min_duration:.0f}s)."
        )
    log.info("Selected %d highlight segment(s).", len(segments))

    # 4. Transcribe once (whole source) if captions are on, then slice per clip.
    all_caps: list[captions_mod.Caption] = []
    if config.caption.enabled:
        log.info("Transcribing audio for captions...")
        all_caps = captions_mod.transcribe(
            source_video, model=config.caption.model, language=config.caption.language
        )

    # 5. Assign publish times across the produced clips.
    schedule = upload_mod.compute_schedule_times(
        config.upload.schedule_start, config.upload.interval_hours, len(segments)
    )

    # 6. Render each clip (reframe + burn-in captions).
    results: list[ClipResult] = []
    for i, seg in enumerate(segments):
        out_path = clips_dir / f"clip_{i + 1:02d}.mp4"
        ass_path: str | None = None
        if config.caption.enabled:
            cues = captions_mod.clip_captions(all_caps, seg.start, seg.end)
            if cues:
                ass_file = clips_dir / f"clip_{i + 1:02d}.ass"
                ass_file.write_text(
                    captions_mod.to_ass(
                        cues, config.caption,
                        width=config.reframe.width, height=config.reframe.height,
                    )
                )
                ass_path = str(ass_file)
        log.info("Rendering clip %d/%d -> %s", i + 1, len(segments), out_path.name)
        clip_mod.render_clip(
            source_video, out_path,
            start=seg.start, duration=seg.duration,
            reframe=config.reframe, ass_path=ass_path,
        )
        results.append(
            ClipResult(
                index=i + 1,
                start=seg.start,
                end=seg.end,
                duration=round(seg.duration, 3),
                score=seg.score,
                file=str(out_path),
                title=title_template.format(source=source_title, n=i + 1),
                publish_at=schedule[i],
            )
        )

    # 7. Optionally upload.
    should_upload = config.upload.enabled if do_upload is None else do_upload
    if should_upload:
        _upload_clips(results, config)

    # 8. Write manifest.
    manifest = {
        "source": source,
        "source_video": str(source_video),
        "duration": info.duration,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clips": [asdict(r) for r in results],
    }
    manifest_path = work / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    log.info("Wrote manifest with %d clip(s) -> %s", len(results), manifest_path)
    return manifest


def _upload_clips(results: list[ClipResult], config: Config) -> None:
    """Authenticate once and upload every produced clip, recording video ids."""
    log.info("Authenticating with YouTube...")
    service = upload_mod.get_authenticated_service(config.upload)
    for r in results:
        resource = upload_mod.build_video_resource(
            r.title, "", config.upload, publish_at=r.publish_at
        )
        response = upload_mod.upload_video(service, r.file, resource)
        r.video_id = response.get("id")
