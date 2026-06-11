"""Command-line interface for ytOKshorts.

Subcommands map to pipeline stages so you can run the whole thing
(``ytokshorts run``) or drive a single step (``download``, ``highlights``,
``clip``, ``captions``, ``upload``) for debugging and one-offs.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__
from .config import Config
from .errors import YtokshortsError

log = logging.getLogger("ytokshorts")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    _setup_logging(args.verbose, args.quiet)

    if not getattr(args, "func", None):
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except YtokshortsError as exc:
        log.error("%s", exc)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        log.error("Interrupted.")
        return 130


# --------------------------------------------------------------------------- #
# Argument parsing
# --------------------------------------------------------------------------- #

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ytokshorts",
        description="Turn long videos into publish-ready YouTube Shorts.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose (debug) logging.")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only log warnings and errors.")
    parser.add_argument("--config", metavar="FILE", help="Path to a ytokshorts.toml config file.")
    sub = parser.add_subparsers(dest="command")

    # run -------------------------------------------------------------------
    p_run = sub.add_parser("run", help="Run the full pipeline on a URL or local file.")
    p_run.add_argument("source", help="Video URL, or a local file path with --local.")
    p_run.add_argument("--local", action="store_true", help="Treat SOURCE as a local file, not a URL.")
    p_run.add_argument("--work-dir", help="Directory for intermediate and output files.")
    p_run.add_argument("--count", type=int, help="Number of clips to produce.")
    p_run.add_argument("--no-captions", action="store_true", help="Skip caption generation.")
    p_run.add_argument("--caption-model", help="faster-whisper model (tiny/base/small/medium/large-v3).")
    p_run.add_argument("--reframe-mode", choices=["crop", "blur"], help="Vertical reframing style.")
    up = p_run.add_mutually_exclusive_group()
    up.add_argument("--upload", action="store_true", help="Upload the clips to YouTube.")
    up.add_argument("--no-upload", action="store_true", help="Do not upload (default).")
    p_run.add_argument("--schedule-start", help="ISO-8601 time for the first scheduled publish.")
    p_run.add_argument("--interval-hours", type=float, help="Hours between scheduled publishes.")
    p_run.add_argument("--privacy", choices=["private", "unlisted", "public"], help="Upload privacy.")
    p_run.add_argument("--title", help="Title template; use {source} and {n}.")
    p_run.set_defaults(func=_cmd_run)

    # download --------------------------------------------------------------
    p_dl = sub.add_parser("download", help="Download a source video.")
    p_dl.add_argument("url")
    p_dl.add_argument("--out", default="work/download", help="Destination directory.")
    p_dl.set_defaults(func=_cmd_download)

    # highlights ------------------------------------------------------------
    p_hl = sub.add_parser("highlights", help="Detect highlight segments and print them.")
    p_hl.add_argument("source", help="Local video file to analyze.")
    p_hl.add_argument("--json", metavar="FILE", help="Write segments as JSON to FILE.")
    p_hl.set_defaults(func=_cmd_highlights)

    # clip ------------------------------------------------------------------
    p_clip = sub.add_parser("clip", help="Render a single vertical clip from a time range.")
    p_clip.add_argument("source", help="Local video file.")
    p_clip.add_argument("--start", type=float, required=True, help="Start time (seconds).")
    p_clip.add_argument("--end", type=float, required=True, help="End time (seconds).")
    p_clip.add_argument("--out", required=True, help="Output mp4 path.")
    p_clip.add_argument("--reframe-mode", choices=["crop", "blur"], help="Vertical reframing style.")
    p_clip.add_argument("--captions", action="store_true", help="Transcribe and burn in captions.")
    p_clip.set_defaults(func=_cmd_clip)

    # captions --------------------------------------------------------------
    p_cap = sub.add_parser("captions", help="Transcribe a video to an SRT file.")
    p_cap.add_argument("source", help="Local video/audio file.")
    p_cap.add_argument("--out", help="Output .srt path (default: stdout).")
    p_cap.add_argument("--model", help="faster-whisper model size.")
    p_cap.add_argument("--language", help="ISO 639-1 language code (default: auto-detect).")
    p_cap.set_defaults(func=_cmd_captions)

    # news ------------------------------------------------------------------
    p_news = sub.add_parser(
        "news", help="Generate AI-scripted news Shorts (voiceover + captions)."
    )
    p_news.add_argument("--count", type=int, help="Number of Shorts to produce.")
    p_news.add_argument("--feed", help="RSS feed URL (default: BBC Sport football).")
    p_news.add_argument("--voice", help="edge-tts voice (e.g. en-US-GuyNeural).")
    p_news.add_argument("--model", help="Claude model for scripts (default: claude-opus-4-8).")
    p_news.add_argument("--no-llm", action="store_true", help="Script from the headline; skip Claude.")
    p_news.add_argument("--work-dir", help="Directory for intermediate and output files.")
    nup = p_news.add_mutually_exclusive_group()
    nup.add_argument("--upload", action="store_true", help="Upload the Shorts to YouTube.")
    nup.add_argument("--no-upload", action="store_true", help="Do not upload (default).")
    p_news.add_argument("--schedule-start", help="ISO-8601 time for the first scheduled publish.")
    p_news.add_argument("--interval-hours", type=float, help="Hours between scheduled publishes.")
    p_news.add_argument("--privacy", choices=["private", "unlisted", "public"], help="Upload privacy.")
    p_news.set_defaults(func=_cmd_news)

    # upload ----------------------------------------------------------------
    p_up = sub.add_parser("upload", help="Upload a single finished clip.")
    p_up.add_argument("file", help="Video file to upload.")
    p_up.add_argument("--title", required=True, help="Video title.")
    p_up.add_argument("--description", default="", help="Video description.")
    p_up.add_argument("--publish-at", help="ISO-8601 scheduled publish time (implies private).")
    p_up.add_argument("--privacy", choices=["private", "unlisted", "public"], help="Privacy status.")
    p_up.set_defaults(func=_cmd_upload)

    return parser


# --------------------------------------------------------------------------- #
# Command implementations
# --------------------------------------------------------------------------- #

def _cmd_run(args: argparse.Namespace) -> int:
    from .pipeline import run_pipeline

    config = _load_config(args)
    # Apply run-specific overrides onto the loaded config.
    if args.work_dir:
        config.work_dir = args.work_dir
    if args.count:
        config.highlights.target_count = args.count
    if args.no_captions:
        config.caption.enabled = False
    if args.caption_model:
        config.caption.model = args.caption_model
    if args.reframe_mode:
        config.reframe.mode = args.reframe_mode
    if args.schedule_start:
        config.upload.schedule_start = args.schedule_start
    if args.interval_hours is not None:
        config.upload.interval_hours = args.interval_hours
    if args.privacy:
        config.upload.privacy = args.privacy

    do_upload = True if args.upload else (False if args.no_upload else None)
    title_template = args.title or "{source} — Highlight {n}"

    manifest = run_pipeline(
        args.source,
        config,
        source_is_url=not args.local,
        do_upload=do_upload,
        title_template=title_template,
    )
    print(f"\nDone. {len(manifest['clips'])} clip(s):")
    for c in manifest["clips"]:
        when = f"  publish: {c['publish_at']}" if c["publish_at"] else ""
        vid = f"  id: {c['video_id']}" if c.get("video_id") else ""
        print(f"  #{c['index']:>2}  {c['file']}  ({c['duration']:.1f}s){when}{vid}")
    return 0


def _cmd_news(args: argparse.Namespace) -> int:
    from .news.pipeline import run_news_pipeline

    config = _load_config(args)
    if args.work_dir:
        config.work_dir = args.work_dir
    if args.count:
        config.news.count = args.count
    if args.feed:
        config.news.feed = args.feed
    if args.voice:
        config.news.voice = args.voice
    if args.model:
        config.news.model = args.model
    if args.schedule_start:
        config.upload.schedule_start = args.schedule_start
    if args.interval_hours is not None:
        config.upload.interval_hours = args.interval_hours
    if args.privacy:
        config.upload.privacy = args.privacy

    do_upload = True if args.upload else (False if args.no_upload else None)
    manifest = run_news_pipeline(
        config,
        count=args.count,
        use_llm=not args.no_llm,
        do_upload=do_upload,
    )
    print(f"\nDone. {len(manifest['clips'])} news Short(s):")
    for c in manifest["clips"]:
        when = f"  publish: {c['publish_at']}" if c["publish_at"] else ""
        vid = f"  id: {c['video_id']}" if c.get("video_id") else ""
        print(f"  #{c['index']:>2}  {c['file']}  ({c['duration']:.1f}s)  {c['title']}{when}{vid}")
    return 0


def _cmd_download(args: argparse.Namespace) -> int:
    from .download import download

    config = _load_config(args)
    path = download(args.url, args.out, config.download)
    print(path)
    return 0


def _cmd_highlights(args: argparse.Namespace) -> int:
    from . import media as media_mod
    from .highlights import compute_window_energies, find_highlights

    config = _load_config(args)
    info = media_mod.probe(args.source)
    if not info.has_audio:
        log.error("Source has no audio track to analyze.")
        return 1
    pcm = media_mod.extract_pcm(args.source)
    energies = compute_window_energies(pcm, media_mod.ANALYSIS_SAMPLE_RATE, config.highlights.window)
    segments = find_highlights(
        energies,
        config.highlights.window,
        min_duration=config.highlights.min_duration,
        max_duration=config.highlights.max_duration,
        target_count=config.highlights.target_count,
        spacing=config.highlights.spacing,
    )
    if args.json:
        payload = [{"start": s.start, "end": s.end, "duration": s.duration, "score": s.score} for s in segments]
        Path(args.json).write_text(json.dumps(payload, indent=2))
        print(f"Wrote {len(segments)} segment(s) to {args.json}")
    else:
        for s in segments:
            print(s)
    return 0


def _cmd_clip(args: argparse.Namespace) -> int:
    from . import captions as captions_mod
    from .clip import render_clip

    config = _load_config(args)
    if args.reframe_mode:
        config.reframe.mode = args.reframe_mode
    if args.end <= args.start:
        log.error("--end must be greater than --start.")
        return 1

    ass_path = None
    if args.captions:
        all_caps = captions_mod.transcribe(args.source, model=config.caption.model, language=config.caption.language)
        cues = captions_mod.clip_captions(all_caps, args.start, args.end)
        if cues:
            ass_file = Path(args.out).with_suffix(".ass")
            ass_file.write_text(captions_mod.to_ass(cues, config.caption, width=config.reframe.width, height=config.reframe.height))
            ass_path = str(ass_file)

    out = render_clip(
        args.source, args.out,
        start=args.start, duration=args.end - args.start,
        reframe=config.reframe, ass_path=ass_path,
    )
    print(out)
    return 0


def _cmd_captions(args: argparse.Namespace) -> int:
    from .captions import to_srt, transcribe

    config = _load_config(args)
    model = args.model or config.caption.model
    language = args.language or config.caption.language
    cues = transcribe(args.source, model=model, language=language)
    srt = to_srt(cues)
    if args.out:
        Path(args.out).write_text(srt)
        print(f"Wrote {len(cues)} cue(s) to {args.out}")
    else:
        sys.stdout.write(srt)
    return 0


def _cmd_upload(args: argparse.Namespace) -> int:
    from .upload import build_video_resource, get_authenticated_service, upload_video

    config = _load_config(args)
    if args.privacy:
        config.upload.privacy = args.privacy
    resource = build_video_resource(args.title, args.description, config.upload, publish_at=args.publish_at)
    service = get_authenticated_service(config.upload)
    response = upload_video(service, args.file, resource)
    print(f"Uploaded: https://youtu.be/{response.get('id')}")
    return 0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _load_config(args: argparse.Namespace) -> Config:
    path = getattr(args, "config", None)
    if path is None and Path("ytokshorts.toml").exists():
        path = "ytokshorts.toml"
    return Config.load(path)


def _setup_logging(verbose: bool, quiet: bool) -> None:
    level = logging.INFO
    if verbose:
        level = logging.DEBUG
    elif quiet:
        level = logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s %(message)s", stream=sys.stderr)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
