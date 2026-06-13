@echo off
REM ============================================================
REM  Make ONE football-news Short right now.
REM  Double-click this file, or run it from PowerShell.
REM ============================================================
cd /d "%~dp0"
py -3.12 -m ytokshorts news --count 1 --no-llm --avatar --avatar-mode local --avatars .\avatars
echo.
echo Done. Opening the output folder...
explorer work\news
pause
