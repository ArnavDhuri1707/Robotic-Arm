@echo off
REM run_arm.bat -- double-click to start the MediaPipe arm mimicry.
REM Runs arm_mimic.py under Python 3.12 (needed for MediaPipe) from this folder.

title Robotic Arm - MediaPipe Mimic
cd /d "%~dp0"

echo ============================================
echo   Robotic Arm - MediaPipe Mimic
echo ============================================
echo   Raise your LEFT arm in view of the webcam.
echo   Press  q  in the video window to stop.
echo.
echo   Make sure the arm is powered and on WiFi.
echo ============================================
echo.

py -3.12 arm_mimic.py

echo.
echo --------------------------------------------
echo   Arm mimic stopped.
echo   If it closed instantly with an error above,
echo   copy the message and send it to Claude.
echo --------------------------------------------
pause >nul
