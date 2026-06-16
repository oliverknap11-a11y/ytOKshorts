# ============================================================
#  Make Shorts for every NEW football story (used by Task Scheduler).
#  Only processes stories not seen before (work\seen.json), so it
#  won't repeat. Logs to work\news\watch.log.
# ============================================================
Set-Location $PSScriptRoot
New-Item -ItemType Directory -Force -Path work\news | Out-Null
py -3.12 -m ytokshorts news --new-only --count 3 --no-llm --avatar --avatar-mode local --avatars .\avatars *>> work\news\watch.log 2>&1
