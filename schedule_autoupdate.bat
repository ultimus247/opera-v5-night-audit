@echo off
REM ============================================================
REM OPERA V5 Night Audit - Schedule auto-update
REM
REM Creates a Windows scheduled task that runs `git pull` on the
REM automations repo daily at 11:30pm (30 min before night audit).
REM
REM config.py is gitignored so credentials are preserved across pulls.
REM
REM Usage:
REM   Right-click -> Run as administrator
REM ============================================================

schtasks /create /tn "OPERA Auto-Update" /tr "C:\scripts\automations\update.bat" /sc daily /st 23:30 /ru Administrator /rl highest /it /f

if %errorlevel% equ 0 (
    echo.
    echo [OK] Auto-update task scheduled for 11:30pm daily
    echo      Task name: "OPERA Auto-Update"
    echo      Action: git pull in C:\scripts\automations
    echo.
    echo To view the task:  schtasks /query /tn "OPERA Auto-Update"
    echo To delete:         schtasks /delete /tn "OPERA Auto-Update" /f
    echo To run now:        schtasks /run /tn "OPERA Auto-Update"
) else (
    echo [ERROR] Failed to create scheduled task
)

pause
