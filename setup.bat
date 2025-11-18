@echo off
REM Setup script for Hierarchical Route Pipeline (Windows)
REM This script automates the initial setup process

echo ================================================================================
echo           HIERARCHICAL ROUTE PIPELINE - SETUP SCRIPT
echo ================================================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Python found:
python --version
echo.

REM Create virtual environment
echo [2/5] Creating virtual environment...
if exist venv (
    echo Virtual environment already exists, skipping...
) else (
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment created successfully
)
echo.

REM Activate virtual environment and install dependencies
echo [3/5] Installing dependencies...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully
echo.

REM Create .env file if it doesn't exist
echo [4/5] Setting up configuration...
if exist .env (
    echo .env file already exists, skipping...
) else (
    copy .env.example .env
    echo .env file created from template
    echo IMPORTANT: Please edit .env file with your database credentials
)
echo.

REM Create logs directory
echo [5/5] Creating directories...
if not exist logs mkdir logs
echo Directories created
echo.

echo ================================================================================
echo                          SETUP COMPLETE!
echo ================================================================================
echo.
echo Next steps:
echo   1. Edit the .env file with your database credentials
echo   2. Activate the virtual environment: venv\Scripts\activate.bat
echo   3. Test configuration: python run_pipeline.py --validate-config
echo   4. Run the pipeline: python run_pipeline.py --test-mode
echo.
echo For more information, see README.md and docs/QUICKSTART.md
echo ================================================================================
pause
