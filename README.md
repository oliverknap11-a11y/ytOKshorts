# ytOKshorts

Turn long videos into publish-ready **YouTube Shorts** — automatically.

`ytokshorts` runs a five-stage pipeline:

1. **Download** a long video from YouTube (or any yt-dlp-supported URL).
2. **Auto-clip highlights** by analyzing the audio energy and selecting the most
   eventful, non-overlapping moments.
3. **Reframe** each clip from 16:9 to vertical 9:16 (blurred-bars or center-crop).
4. **Caption** it with burned-in subtitles transcribed by Whisper.
5. **Schedule / upload** the finished Shorts to YouTube via the Data API.

Each stage is also a standalone subcommand, so you can run the whole thing or
drive a single step.

---

## Install

The base install handles downloading and analysis. The heavier pieces
(transcription, upload) are opt-in extras so you only pull in what you use.

```bash
pip install -e .                 # core: download + highlight + reframe
pip install -e '.[captions]'     # + Whisper transcription
pip install -e '.[upload]'       # + YouTube Data API upload
pip install -e '.[fast]'         # + numpy (faster audio analysis)
pip install -e '.[all]'          # everything, including dev tools
```

You also need two command-line tools on your `PATH`:

- **ffmpeg / ffprobe** — `apt install ffmpeg` or `brew install ffmpeg`
- **yt-dlp** — installed automatically as a dependency

---

## Quick start

```bash
# Full pipeline: download, cut 5 highlights, reframe, caption — no upload.
ytokshorts run "https://www.youtube.com/watch?v=VIDEO_ID"

# Produce 3 clips, center-crop instead of blurred bars, no captions.
ytokshorts run "https://youtu.be/VIDEO_ID" --count 3 --reframe-mode crop --no-captions

# From a local file you already have.
ytokshorts run ./podcast.mp4 --local

# Cut + reframe + caption, then schedule one upload per day starting tomorrow 9am UTC.
ytokshorts run "https://youtu.be/VIDEO_ID" \
  --upload --schedule-start 2026-06-12T09:00:00Z --interval-hours 24
```

Outputs land in the working directory (default `work/`):

```
work/
├── download/            # the source video
├── clips/
│   ├── clip_01.mp4      # vertical, captioned Shorts
│   ├── clip_01.ass      # the burned-in subtitle track
│   └── ...
└── manifest.json        # every clip: timing, score, title, schedule, video id
```

---

## Individual commands

```bash
ytokshorts download URL --out work/download         # just fetch the source
ytokshorts highlights video.mp4 --json segs.json    # detect segments, print/export
ytokshorts clip video.mp4 --start 65 --end 120 --out short.mp4 --captions
ytokshorts captions video.mp4 --out video.srt       # transcribe to SRT
ytokshorts upload short.mp4 --title "Best moment" --publish-at 2026-06-12T09:00:00Z
```

Run `ytokshorts <command> --help` for the full flag list.

---

## Configuration

Defaults are sensible, but you can override everything via a `ytokshorts.toml`
in the working directory (auto-detected) or `--config path.toml`. Copy
[`ytokshorts.example.toml`](./ytokshorts.example.toml) to get started. Highlights:

| Section       | Key             | Default  | Notes                                       |
|---------------|-----------------|----------|---------------------------------------------|
| `highlights`  | `target_count`  | `5`      | Clips to cut per source                     |
| `highlights`  | `max_duration`  | `58`     | Clip length cap (must be ≤ 60)              |
| `reframe`     | `mode`          | `blur`   | `blur` (fit + blurred bars) or `crop`       |
| `caption`     | `model`         | `base`   | Whisper size: tiny…large-v3                 |
| `upload`      | `schedule_start`| —        | First publish time (UTC); requires `private`|

---

## How highlight detection works

The source audio is decoded to mono 16 kHz PCM and reduced to an RMS-loudness
value per short window. The envelope is smoothed (so one loud transient doesn't
dominate), then a greedy selector picks the highest-energy, non-overlapping
windows — keeping a configurable gap between clips. It's intentionally simple
and dependency-light; loud, sustained passages (laughter, applause, music drops,
emphatic speech) are a strong proxy for "the good part." Sources with no audio
fall back to evenly spaced clips.

---

## YouTube upload setup

Uploading needs an OAuth client for the **YouTube Data API v3**:

1. In the [Google Cloud Console](https://console.cloud.google.com/), enable the
   YouTube Data API v3 and create an **OAuth client ID** (type: *Desktop app*).
2. Download the JSON as `client_secret.json` next to where you run the tool.
3. The first `--upload` run opens a browser consent flow and caches the result
   to `token.json` for subsequent non-interactive runs.

Scheduled publishing (`--schedule-start`) requires `privacy = private`; YouTube
flips the video public at the scheduled time. Credentials and tokens are
git-ignored — never commit them.

---

## Development

```bash
pip install -e '.[all]'
pytest                  # the pure pipeline logic is fully unit-tested
```

The design keeps all heavy/credential-bound dependencies (Whisper, the Google
API client, numpy) behind lazy imports, so the core stays importable and the
test suite runs with zero external services or binaries.

## License

MIT
