@echo off
setlocal EnableExtensions
cd /d "%~dp0"
RuntimeCheck.exe > startup-check.log 2>&1
set "TEST_EXIT_CODE=%ERRORLEVEL%"
echo Runtime exit=%TEST_EXIT_CODE%>> startup-check.log
if not "%TEST_EXIT_CODE%"=="0" (
  echo Startup check failed. Please send startup-check.log.
  pause
  exit /b 1
)
echo Capturing the initial window. Please wait...
XinXuanGlassTest.exe --snapshot window.bmp > capture-log.txt 2>&1
set "TEST_EXIT_CODE=%ERRORLEVEL%"
echo Window exit=%TEST_EXIT_CODE%>> capture-log.txt
if "%TEST_EXIT_CODE%"=="0" (
  echo Please send window.bmp and capture-log.txt.
) else (
  echo Please send capture-log.txt and glass-last-stage.txt if present.
)
pause
endlocal
