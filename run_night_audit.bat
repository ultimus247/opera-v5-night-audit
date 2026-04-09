@echo off
REM ============================================================
REM OPERA Night Audit Launcher
REM
REM All configuration lives in config.py (gitignored).
REM Copy config.example.py to config.py and edit before running.
REM ============================================================

cd /d C:\scripts

REM Use Python from config, fall back to default path if not found
set PYTHON_EXE=C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe

%PYTHON_EXE% C:\scripts\night_audit.py
