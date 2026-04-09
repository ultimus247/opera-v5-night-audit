@echo off
REM ============================================================
REM OPERA Night Audit Launcher
REM Edit ANTHROPIC_API_KEY below with your key before running.
REM ============================================================

set ANTHROPIC_API_KEY=YOUR_ANTHROPIC_API_KEY_HERE

cd /d C:\scripts
C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe C:\scripts\night_audit.py
