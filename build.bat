@echo off
cd /d "%~dp0"
if "%~1"=="" (
    python bookmaker.py sample_manuscript.md
) else (
    python bookmaker.py "%~1"
)
echo.
pause
