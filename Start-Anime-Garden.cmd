@echo off
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found.
  echo Install Node.js 22.13 or newer from https://nodejs.org/
  echo Then double-click Start-Anime-Garden.cmd again.
  pause
  exit /b 1
)

echo Starting Anime Garden...
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:3210/#home'"
node --env-file-if-exists=.env server.mjs
pause
