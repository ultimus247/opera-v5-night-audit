@echo off
REM ============================================================
REM OPERA V5 Night Audit - Schedule auto-update
REM
REM Creates a Windows scheduled task that runs `git pull` on the
REM automations repo daily at 11:30pm (30 min before night audit).
REM
REM config.py is gitignored so credentials are preserved across pulls.
REM
REM IMPORTANT - do NOT add /it to this task.
REM   /it means "interactive token": the task runs ONLY while the /ru user is
REM   logged on, and is silently skipped otherwise. That is what caused this
REM   task to stop pulling for ~2.5 months, so the LINEAR_ASSIGNEE_ID fix from
REM   2026-05-20 never reached the machines.
REM   update.bat only runs `git pull` + patch_config.py - no GUI, no desktop -
REM   so it must run whether the user is logged on or not. That requires a
REM   stored password (/rp), which is why this prompts.
REM
REM   The OPERA Night Audit task is the opposite: it drives the OPERA GUI via
REM   screenshots and mouse control, so it DOES need /it and a live desktop
REM   session. Use disconnect.bat (tscon) to leave RDP without logging off.
REM
REM Usage:
REM   Right-click -> Run as administrator
REM   Enter the Administrator password when prompted
REM ============================================================

echo Creating "OPERA Auto-Update" task (runs whether logged on or not).
echo You will be prompted for the Administrator password.
echo.

schtasks /create /tn "OPERA Auto-Update" /tr "C:\scripts\automations\update.bat" /sc daily /st 23:30 /ru Administrator /rp * /rl highest /f

if %errorlevel% equ 0 (
    echo.
    echo [OK] Auto-update task scheduled for 11:30pm daily
    echo      Task name: "OPERA Auto-Update"
    echo      Action: git pull in C:\scripts\automations
    echo      Runs whether the user is logged on or not
    echo.
    echo To view the task:  schtasks /query /tn "OPERA Auto-Update"
    echo To delete:         schtasks /delete /tn "OPERA Auto-Update" /f
    echo To run now:        schtasks /run /tn "OPERA Auto-Update"
) else (
    echo [ERROR] Failed to create scheduled task
)

pause
