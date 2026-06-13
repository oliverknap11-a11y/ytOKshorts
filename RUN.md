# ▶️ Run cheat-sheet (pinned)

Everything runs from the repo root: `C:\Users\knapo\ytokshorts`.
The tool uses Python 3.12 (`py -3.12`); SadTalker runs in its own `sadtalker\venv`.

## Make ONE Short now
**Double-click `make-short.bat`** — or run:
```powershell
py -3.12 -m ytokshorts news --count 1 --no-llm --avatar --avatar-mode local --avatars .\avatars
```
Output: `work\news\news_01.mp4`

## Post a Short to YouTube (manual, recommended)
Each clip now comes with a ready-to-paste metadata file:
- Video: `work\news\news_01.mp4`
- Title + description + hashtags: `work\news\news_01.txt`

Steps: YouTube Studio → **Create → Upload** → pick `news_01.mp4` → open
`news_01.txt`, copy the **TITLE** into the title field and the **DESCRIPTION**
into the description → set visibility (Public / Schedule) → Publish. It's vertical
and <60s, so it posts as a Short.

## Make Shorts automatically for every NEW story
Register the scheduled task once (runs every 30 min, only new stories):
```powershell
schtasks /Create /SC MINUTE /MO 30 /TN "ytokshorts-news" /TR "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Users\knapo\ytokshorts\watch-shorts.ps1" /F
```
- Run it now to test: `schtasks /Run /TN "ytokshorts-news"`
- Watch the log:        `Get-Content work\news\watch.log -Wait`
- Stop / remove it:     `schtasks /Delete /TN "ytokshorts-news" /F`

## Change the voice
Edit `voice = "..."` under `[news]` in `ytokshorts.toml` (e.g. `en-GB-SoniaNeural`,
`en-US-AriaNeural`). List voices: `py -3.12 -m edge_tts --list-voices`

## Better quality (slower, needs the 512 model)
In `ytokshorts.toml`, change the `local_command` to end with:
`--still --preprocess full --size 512 --enhancer gfpgan`
then clear the cache: `Remove-Item work\news\_avatar_*.png -Force`

## Add a country avatar
Put `avatars\<country>.png` (e.g. `avatars\france.png`) plus `avatars\neutral.png`
(both must be a clear, front-facing face). Replaced an existing one?
`Remove-Item work\news\_avatar_<country>.png -Force`
Recognized countries: england, scotland, wales, ireland, france, spain, germany,
italy, portugal, netherlands, belgium, croatia, poland, switzerland, denmark,
sweden, norway, turkey, greece, brazil, argentina, uruguay, colombia, mexico,
usa, morocco, senegal, nigeria, egypt, ghana, japan, south-korea, saudi-arabia,
australia. (Anything else → neutral.)

## Use Claude for punchier scripts (optional, paid)
Add Anthropic credits, set `ANTHROPIC_API_KEY`, and drop `--no-llm` from the command.
