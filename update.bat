@echo off
REM ============================================================
REM OPERA V5 Night Audit - Update script
REM
REM Pulls latest changes from Git without touching config.py.
REM Safe to run from Task Scheduler (no pause, logs to update.log).
REM ============================================================

cd /d C:\scripts\automations
echo [%date% %time%] Pulling latest from GitHub... >> C:\scripts\automations\update.log
git pull >> C:\scripts\automations\update.log 2>&1
echo [%date% %time%] Update complete. >> C:\scripts\automations\update.log
echo. >> C:\scripts\automations\update.log

REM Only pause when run interactively (not from scheduled task)
if "%SESSIONNAME%"=="Console" goto :eof
if "%1"=="/quiet" goto :eof
echo Update complete. See update.log for details.
pause
