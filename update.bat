@echo off
REM ============================================================
REM OPERA V5 Night Audit - Update script
REM
REM Pulls latest changes from Git without touching config.py.
REM ============================================================

cd /d C:\scripts\automations
echo Pulling latest from GitHub...
git pull
echo.
echo Update complete. config.py was preserved.
pause
