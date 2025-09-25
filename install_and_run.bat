@echo off
title IMU GPS Logger - Setup and Run
color 0B

echo ============================================================
echo     IMU GPS LOGGER - INITIAL SETUP
echo ============================================================
echo.

REM Check Python installation
echo [1/3] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ERROR: Python is not installed!
    echo.
    echo Please install Python 3.8 or higher from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
python --version
echo OK - Python is installed

echo.
echo [2/3] Installing required packages...
pip install pyserial psutil
if errorlevel 1 (
    color 0C
    echo ERROR: Failed to install packages
    pause
    exit /b 1
)
echo OK - Packages installed

echo.
echo [3/3] Testing STM32 connection...
python -c "from core.connection_manager import ConnectionManager; cm = ConnectionManager(); ports = cm.scan_ports(); print(f'Found {len(ports)} port(s)'); [print(f'  - {p.device}: {p.description}') for p in ports]"
if errorlevel 1 (
    color 0E
    echo WARNING: Could not detect ports. Make sure STM32 is connected.
)

echo.
color 0A
echo ============================================================
echo     SETUP COMPLETE - STARTING LOGGER
echo ============================================================
echo.
timeout /t 2 >nul

REM Start the main logger
python main.py --auto

echo.
echo ============================================================
echo Recording complete. Check 'logs' folder for CSV files
echo ============================================================
pause