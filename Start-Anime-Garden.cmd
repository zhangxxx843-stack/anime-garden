@echo off
cd /d "%~dp0"

set "NODE_EXE=%~dp0runtime\node.exe"
if exist "%NODE_EXE%" goto start_app

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js was not found.
  echo This package does not contain runtime\node.exe.
  echo Download the portable package again, or install Node.js 22.13 or newer.
  pause
  exit /b 1
)
set "NODE_EXE=node"

:start_app
echo Starting Anime Garden...
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:3210/#home'"
"%NODE_EXE%" --env-file-if-exists=.env server.mjs
pause
