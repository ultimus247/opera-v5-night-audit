@echo off
REM ============================================================
REM Alert: OPERA Server Down
REM Creates an urgent Linear ticket on the PMS Expert team.
REM Requires LINEAR_API_KEY environment variable.
REM ============================================================

python C:\scripts\automations\alert_opera_down.py
