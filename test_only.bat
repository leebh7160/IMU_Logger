@echo off
title IMU GPS Logger - Test Mode
color 0E

echo ============================================================
echo     IMU GPS LOGGER - TEST MODE
echo ============================================================
echo.
echo [1] Test Port Connection
echo [2] Test Data Reading (5 seconds)
echo [3] Test CSV Writing
echo [4] Test Data Validation
echo [5] Test Performance Monitor
echo [6] Run All Tests
echo [7] Back to Main Menu
echo.
set /p test="Select test (1-7): "

if "%test%"=="1" goto test_port
if "%test%"=="2" goto test_read
if "%test%"=="3" goto test_csv
if "%test%"=="4" goto test_validation
if "%test%"=="5" goto test_performance
if "%test%"=="6" goto test_all
if "%test%"=="7" start start_logger.bat & exit

echo Invalid option
timeout /t 2 >nul
goto start

:test_port
cls
echo Testing Port Connection...
echo ============================================================
python test\test_port_scan.py
pause
goto end

:test_read
cls
echo Testing Data Reading for 5 seconds...
echo ============================================================
python test\test_batch_read.py
pause
goto end

:test_csv
cls
echo Testing CSV Writing...
echo ============================================================
python test\test_csv_logger.py
pause
goto end

:test_validation
cls
echo Testing Data Validation...
echo ============================================================
python test\test_data_validator.py
pause
goto end

:test_performance
cls
echo Testing Performance Monitor...
echo ============================================================
python test\test_performance_monitor.py
pause
goto end

:test_all
cls
echo Running All Tests...
echo ============================================================
echo.
echo [1/5] Port Scan Test
python test\test_port_scan.py
echo.
echo Press any key for next test...
pause >nul

echo [2/5] Connection Test
python test\test_connection.py
echo.
echo Press any key for next test...
pause >nul

echo [3/5] Batch Read Test
python test\test_batch_read.py
echo.
echo Press any key for next test...
pause >nul

echo [4/5] Data Validation Test
python test\test_data_validator.py
echo.
echo Press any key for next test...
pause >nul

echo [5/5] CSV Logger Test
python test\test_csv_logger.py
echo.
echo All tests complete!
pause
goto end

:end
cls
goto start