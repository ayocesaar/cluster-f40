@echo off
rem Abre el cluster F40 en Windows con doble clic.
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 main.py
) else (
    python main.py
)
if errorlevel 1 pause
