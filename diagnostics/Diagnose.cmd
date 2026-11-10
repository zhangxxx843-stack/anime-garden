@echo off
setlocal
cd /d "%~dp0"
echo Xin Xuan startup diagnosis> diagnosis-summary.txt
ver >> diagnosis-summary.txt
echo OS_ARCH=%PROCESSOR_ARCHITECTURE%>> diagnosis-summary.txt
echo WOW64_ARCH=%PROCESSOR_ARCHITEW6432%>> diagnosis-summary.txt
if exist glass-last-stage.txt del /q glass-last-stage.txt
if exist basic-last-stage.txt del /q basic-last-stage.txt
echo [1/3] Checking Cangjie runtime...
RuntimeCheck.exe > runtime-check.log 2>&1
echo RuntimeCheck exit=%ERRORLEVEL%>> diagnosis-summary.txt
echo [2/3] Checking a basic window. It should close automatically...
BasicWindow.exe --snapshot basic-window.bmp > basic-window.log 2>&1
echo BasicWindow exit=%ERRORLEVEL%>> diagnosis-summary.txt
echo [3/3] Checking the glass window. It should close automatically...
XinXuanGlassTest.exe --snapshot glass-window.bmp > glass-window.log 2>&1
echo GlassWindow exit=%ERRORLEVEL%>> diagnosis-summary.txt
echo.>> diagnosis-summary.txt
echo --- RUNTIME OUTPUT --->> diagnosis-summary.txt
type runtime-check.log >> diagnosis-summary.txt
echo --- BASIC LAST STAGE --->> diagnosis-summary.txt
if exist basic-last-stage.txt (type basic-last-stage.txt >> diagnosis-summary.txt) else (echo No basic stage file>> diagnosis-summary.txt)
echo --- GLASS LAST STAGE --->> diagnosis-summary.txt
if exist glass-last-stage.txt (type glass-last-stage.txt >> diagnosis-summary.txt) else (echo No glass stage file>> diagnosis-summary.txt)
powershell.exe -NoProfile -Command "Get-WinEvent -FilterHashtable @{LogName='Application';Id=1000,1001;StartTime=(Get-Date).AddMinutes(-15)} -MaxEvents 100 -ErrorAction SilentlyContinue | Where-Object {$_.Message -match 'RuntimeCheck.exe|BasicWindow.exe|XinXuanGlassTest.exe'} | Select-Object TimeCreated,Id,Message | Format-List | Out-String -Width 240" > crash-events.txt 2>&1
echo.
type diagnosis-summary.txt
echo.
echo Please send diagnosis-summary.txt and crash-events.txt.
echo If a test window stays open for more than 30 seconds, close it to continue.
pause
endlocal
