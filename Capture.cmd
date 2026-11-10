@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "CAPTURE_DATA=%TEMP%\XinXuanShopping-Capture-%RANDOM%-%RANDOM%"
XinXuanShopping.exe --test-data-dir "%CAPTURE_DATA%" --snapshot window.bmp > capture-log.txt 2>&1
echo Screenshot: window.bmp
echo Isolated capture data: %CAPTURE_DATA%
pause
