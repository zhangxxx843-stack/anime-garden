@echo off
setlocal
cd /d "%~dp0"
ver > startup-summary.txt
echo [1/2] Original startup files...
TraceStartup.exe RuntimeCheck-Baseline.exe > baseline-trace.txt 2>&1
echo Baseline tracer exit=%ERRORLEVEL%>> startup-summary.txt
echo [2/2] Compatibility startup files...
TraceStartup.exe RuntimeCheck-Compat.exe > compat-trace.txt 2>&1
echo Compatibility tracer exit=%ERRORLEVEL%>> startup-summary.txt
echo.>> startup-summary.txt
echo --- BASELINE RESULT --->> startup-summary.txt
findstr /c:"NATIVE_TRACER_ENTERED" /c:"RUNTIME_OK" /c:"CHILD_EXIT" /c:"FAILED" /c:"INSTRUCTION " baseline-trace.txt >> startup-summary.txt
echo --- COMPATIBILITY RESULT --->> startup-summary.txt
findstr /c:"NATIVE_TRACER_ENTERED" /c:"RUNTIME_OK" /c:"CHILD_EXIT" /c:"FAILED" /c:"INSTRUCTION " compat-trace.txt >> startup-summary.txt
echo.
type startup-summary.txt
echo.
echo Please send startup-summary.txt, baseline-trace.txt and compat-trace.txt.
pause
endlocal
