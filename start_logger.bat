@echo off
title IMU GPS Logger - 104Hz Data Recording System
color 0A

echo ============================================================
echo           IMU GPS LOGGER - 104Hz Data Recording
echo ============================================================
echo.
echo [1] Auto Mode - Start Recording (Continuous)
echo [2] Timed Recording (10 seconds)
echo [3] Timed Recording (30 seconds)
echo [4] Timed Recording (60 seconds)
echo [5] Manual Port Selection
echo [6] Install Requirements
echo [7] Test Connection Only
echo [8] Exit
echo.
set /p choice="Select option (1-8): "

if "%choice%"=="1" goto auto_continuous
if "%choice%"=="2" goto auto_10s
if "%choice%"=="3" goto auto_30s
if "%choice%"=="4" goto auto_60s
if "%choice%"=="5" goto manual_port
if "%choice%"=="6" goto install_requirements
if "%choice%"=="7" goto test_connection
if "%choice%"=="8" goto end

echo Invalid option. Please try again.
timeout /t 2 >nul
goto start

:auto_continuous
cls
echo ============================================================
echo Starting Continuous Recording (Press Ctrl+C to stop)
echo ============================================================
python main.py --auto
goto finish

:auto_10s
cls
echo ============================================================
echo Starting 10 Second Recording
echo ============================================================
python main.py --auto --duration 10
goto finish

:auto_30s
cls
echo ============================================================
echo Starting 30 Second Recording
echo ============================================================
python main.py --auto --duration 30
goto finish

:auto_60s
cls
echo ============================================================
echo Starting 60 Second Recording
echo ============================================================
python main.py --auto --duration 60
goto finish

:manual_port
cls
set /p port="Enter COM port (e.g., COM3): "
echo ============================================================
echo Starting Recording on %port% (Press Ctrl+C to stop)
echo ============================================================
python main.py --port %port%
goto finish

:install_requirements
cls
echo ============================================================
echo Installing Required Packages
echo ============================================================
pip install pyserial psutil
echo.
echo Installation complete!
pause
cls
goto start

:test_connection
cls
echo ============================================================
echo Testing Connection
echo ============================================================
python test\test_connection.py
pause
cls
goto start

:finish
echo.
echo ============================================================
echo Recording Complete! Files saved in 'logs' folder
echo ============================================================
echo.
echo Press any key to return to menu...
pause >nul
cls
goto start

:end
exit