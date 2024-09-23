@echo off

:: Colors for output
set "GREEN="
set "RED="
set "NC="

:: Function to check and install a pip package
:install_pip_package
echo Installing %1 via pip...
pip install %1
goto :eof

:: Check if Python 3 is installed
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

:: List of pip dependencies
set dependencies=openai prompt_toolkit

:: Check and install pip dependencies
for %%d in (%dependencies%) do (
    pip show %%d >nul 2>&1
    if %errorlevel% neq 0 (
        echo %%d not found. Installing...
        call :install_pip_package %%d
    )
)

:: Run the Python script
echo Starting AIShellBrain.py...
python AIShellBrain.py -y
