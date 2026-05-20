@echo off
REM ============================================================
REM OPERA V5 Night Audit - Update script
REM
REM Pulls latest changes from Git without touching config.py.
REM Window closes automatically so it never blocks the night audit.
REM Runs patch_config.py to self-heal any stale or missing config keys.
REM ============================================================

cd /d C:\scripts\automations
echo [%date% %time%] Pulling latest from GitHub... >> C:\scripts\automations\update.log
git pull >> C:\scripts\automations\update.log 2>&1
echo [%date% %time%] Running config patcher... >> C:\scripts\automations\update.log
python C:\scripts\automations\patch_config.py >> C:\scripts\automations\update.log 2>&1
echo [%date% %time%] Update complete. >> C:\scripts\automations\update.log
echo. >> C:\scripts\automations\update.log
exit
