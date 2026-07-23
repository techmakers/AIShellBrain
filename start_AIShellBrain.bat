@echo off
setlocal

cd /d "%~dp0"

:: Check if Python is installed
where /q python
if %errorlevel% neq 0 (
    echo Python 3 not found. Please install Python 3 and add it to your PATH.
    exit /b 1
)

:: Check if pip is installed
python -m pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo pip not found. Installing...
    python -m ensurepip
    python -m pip install --upgrade pip
)

:: Install Python dependencies
echo Installing dependencies from requirements.txt...
python -m pip install -r requirements.txt

:: Create .env from the example on first run
if not exist .env (
    if exist .env.example (
        echo Creating .env from .env.example. Edit it to set your provider/API key.
        copy .env.example .env >nul
    )
)

:: Run ShellBrain
echo Starting ShellBrain...
python shellbrain.py %*
