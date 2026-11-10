@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Checking startup compatibility...
RuntimeCheck.exe > startup-check.log 2>&1
set "TEST_EXIT_CODE=%ERRORLEVEL%"
echo Runtime exit=%TEST_EXIT_CODE%>> startup-check.log
if not "%TEST_EXIT_CODE%"=="0" goto runtime_failed
echo Starting Xin Xuan Shopping window test...
XinXuanGlassTest.exe > run-log.txt 2>&1
set "TEST_EXIT_CODE=%ERRORLEVEL%"
echo Window exit=%TEST_EXIT_CODE%>> run-log.txt
if not "%TEST_EXIT_CODE%"=="0" goto window_failed
exit /b 0
:runtime_failed
echo The startup check failed. Collecting its crash trace...
TraceStartup.exe RuntimeCheck.exe > startup-trace.txt 2>&1
echo Please send startup-check.log and startup-trace.txt.
pause
exit /b 1
:window_failed
echo Please send run-log.txt and glass-last-stage.txt if present.
pause
exit /b 1
