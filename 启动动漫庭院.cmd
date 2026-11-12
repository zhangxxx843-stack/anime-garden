@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo 未检测到 Node.js。
  echo 请先安装 Node.js 22.13 或更新版本：https://nodejs.org/
  echo 安装完成后，重新双击“启动动漫庭院.cmd”。
  pause
  exit /b 1
)
echo 正在启动动漫庭院……
start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:3210/#home'"
node --env-file-if-exists=.env server.mjs
pause
