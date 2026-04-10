@echo off
REM ============================================================
REM OPERA Night Audit Launcher
REM
REM All configuration lives in config.py (gitignored).
REM Copy config.example.py to config.py and edit before running.
REM ============================================================

cd /d C:\scripts

REM Use python from PATH (set up by install.bat via winget)
python C:\scripts\night_audit.py
