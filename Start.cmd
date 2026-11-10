@echo off
setlocal EnableExtensions
cd /d "%~dp0"
XinXuanShopping.exe > run-log.txt 2>&1
set "APP_EXIT=%ERRORLEVEL%"
echo Exit code: %APP_EXIT%>> run-log.txt
if not "%APP_EXIT%"=="0" (
 echo Xin Xuan Shopping exited unexpectedly. Please send run-log.txt.
 pause
)
exit /b %APP_EXIT%
