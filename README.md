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

It can **also generate Shorts from scratch** — no source video required. The
`news` command turns a football (or any) RSS feed into faceless news Shorts:
fetch headlines → write a punchy script with Claude → AI voiceover (edge-tts) →
9:16 video with a gradient background and bold word-by-word captions → optional
schedule/upload.

---

## Install

The base install handles downloading and analysis. The heavier pieces
(transcription, upload) are opt-in extras so you only pull in what you use.

```bash
pip install -e .                 # core: download + highlight + reframe
pip install -e '.[captions]'     # + Whisper transcription
pip install -e '.[upload]'       # + YouTube Data API upload
pip install -e '.[news]'         # + AI news Shorts (Claude + edge-tts)
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

## AI news Shorts (no source video needed)

Generate faceless news Shorts straight from an RSS feed:

```bash
pip install -e '.[news]'
export ANTHROPIC_API_KEY=sk-ant-...        # for Claude-written scripts

# 3 football Shorts: headline → script → voiceover → captioned 9:16 video
ytokshorts news --count 3

# No API key? Script straight from the headline/summary instead:
ytokshorts news --count 3 --no-llm

# Different feed + voice, then schedule one upload per day:
ytokshorts news --feed "https://www.theguardian.com/football/rss" \
  --voice en-GB-RyanNeural --upload --schedule-start 2026-06-12T09:00:00Z
```

Outputs `work/news/news_01.mp4 …` plus `work/news_manifest.json`. The scripts use
Claude (`claude-opus-4-8` by default, configurable) with structured outputs; the
voiceover uses the free Microsoft **edge-tts** (no key), and its word-boundary
timings drive the on-screen captions.

By default captions use the **`stack`** style: each spoken line fades in *under*
the previous one (the just-spoken lines dim, the newest stays bright), so the
subtitles build down the screen and longer scripts fill more of it — paging to a
fresh top when they reach the bottom. Numbers/scores are highlighted in gold. Set
`news.caption_style = "pop"` for one centered, popping chunk at a time instead.

**Background:** by default it draws a stylized **football pitch** (no assets,
no rights issues). Point `--background` at your own image, video, or a folder
(cycled per clip) to use that instead — it's cover-cropped to 9:16 with a dark
scrim so the captions stay readable:

```bash
ytokshorts news --count 3 --background ./my_broll/      # folder of clips/images
ytokshorts news --count 3 --background stadium.jpg      # a single image
```

> ⚠️ Use feeds/footage you're allowed to repost. This tool writes original
> scripts and generates its own visuals/voiceover — it does **not** scrape
> broadcast footage or club media (which would risk copyright strikes).

### Optional: an AI presenter (country kit) in front of the pitch

Add a talking presenter composited over the pitch, with subtitles kept above her
head and a kit chosen from the country the story is about (neutral stories use a
your-logo kit). The country is detected from the headline; the presenter is
chroma-keyed (green screen) onto the pitch.

Three engines (`avatar.mode`):

- **`clips`** (free) — supply per-country presenter clips in a folder
  (`presenters/england.mp4`, `presenters/neutral.mp4`, …); overlaid with your
  edge-tts voiceover kept. Render the looks once however you like.
- **`photo`** (paid lip-sync) — supply your **own per-country avatar images**
  (`avatars/portugal.png`, `avatars/neutral.png`, …). The tool mattes each onto
  a green screen (`rembg`), auto-crops a full-body shot to head-and-shoulders
  (`framing`), lip-syncs it via **HeyGen Talking Photo**, then keys her onto the pitch.
- **`local`** (free, needs a GPU) — same image flow, but lip-synced by a **local
  tool you install** (e.g. [SadTalker](https://github.com/OpenTalker/SadTalker)).
  No per-clip cost. Configure `avatar.local_command` / `avatar.local_cwd`:
  ```bash
  git clone https://github.com/OpenTalker/SadTalker && cd SadTalker
  pip install -r requirements.txt && bash scripts/download_models.sh   # ~2GB weights
  ```
  Then `ytokshorts news --avatar --avatar-mode local --avatars ./avatars`.
- **`heygen`** (paid) — generate from a HeyGen-hosted `avatar_id` per country
  (`[avatar.avatar_map]`).

```bash
ytokshorts news --count 3 --avatar --presenters ./presenters            # clips
ytokshorts news --count 3 --avatar --avatar-mode photo --avatars ./avatars  # your image, lip-synced
ytokshorts news --count 3 --avatar --avatar-mode heygen                 # hosted avatar
```

Install the matting extra for `photo` mode: `pip install -e '.[avatar]'`, and set
`HEYGEN_API_KEY`. Tip: generate your avatar images **on a plain green or
transparent background** for the cleanest key (then `green_matte` is optional).

> ⚠️ **Official national kits/crests are trademarked.** Using them is your
> content-rights decision, and the avatar provider's content policy may flag
> third-party logos. The safe alternative is a generic kit in the nation's
> colours, or your own-logo kit for every story.

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
