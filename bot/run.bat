@echo off
REM Project Oracle launcher (Windows)
REM This script must live in the bot folder, next to main.py.

setlocal
cd /d "%~dp0"

REM --- Sanity check: are we actually in the bot folder? ---
if not exist "main.py" (
    echo.
    echo [error] main.py not found.
    echo [error] Current directory: %CD%
    echo.
    echo [error] run.bat must live INSIDE the bot folder, next to main.py.
    echo [error] Move run.bat back into:
    echo [error]     C:\Users\malek\Desktop\Project_Oracle\bot\
    echo [error] then double-click it again.
    echo.
    pause
    exit /b 1
)
if not exist "requirements.txt" (
    echo [error] requirements.txt missing in %CD%
    pause
    exit /b 1
)

REM --- Create venv on first run ---
if not exist "venv" (
    echo [setup] Creating virtual environment in %CD%\venv
    python -m venv venv
    if errorlevel 1 (
        echo.
        echo [error] Could not create venv. Make sure Python 3.10+ is installed
        echo [error] and the "Add Python to PATH" box was checked during install.
        echo.
        pause
        exit /b 1
    )
    call "venv\Scripts\activate.bat"
    echo [setup] Upgrading pip...
    python -m pip install --upgrade pip
    echo [setup] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [error] pip install failed. See messages above.
        pause
        exit /b 1
    )
) else (
    call "venv\Scripts\activate.bat"
)

echo [run] Starting Project Oracle from %CD%
python main.py

pause
