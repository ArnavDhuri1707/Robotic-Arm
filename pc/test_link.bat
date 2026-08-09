@echo off
REM test_link.bat -- double-click to test the arm's WiFi + servo link (no webcam).
REM Streams poses to the ESP32; the arm wiggles one joint at a time.

title Robotic Arm - Link Test
cd /d "%~dp0"

echo ============================================
echo   Robotic Arm - Link Test (no camera)
echo ============================================
echo   The arm should wiggle one joint at a time.
echo   Make sure it's powered and on WiFi.
echo   Press  Ctrl+C  to stop.
echo ============================================
echo.

py udp_test.py

echo.
echo --------------------------------------------
echo   Link test stopped.
echo   If the arm never moved: servo supply off,
echo   or the ESP32 is on a new IP (check config).
echo --------------------------------------------
pause >nul
