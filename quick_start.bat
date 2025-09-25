@echo off
REM Quick Start - Immediately start recording without menu

title IMU GPS Logger - Recording...
color 0A

echo ============================================================
echo     IMU GPS LOGGER - QUICK START
echo ============================================================
echo.
echo Starting automatic recording...
echo Press ANY KEY to stop and save data
echo (Recording continues during confirmation)
echo.
echo ============================================================

REM Start recording immediately
python main.py --auto

echo.
echo ============================================================
echo Recording stopped. CSV files saved in 'logs' folder
echo ============================================================
pause