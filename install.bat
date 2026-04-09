@echo off
REM ============================================================
REM OPERA V5 Night Audit - One-shot installer
REM
REM Installs Git (if missing), clones the repo to C:\scripts,
REM and creates config.py from the template.
REM
REM Usage:
REM   1. Download this file to the target machine
REM   2. Right-click -> Run as administrator
REM ============================================================

setlocal
set REPO_URL=https://github.com/ultimus247/opera-v5-night-audit.git
set INSTALL_DIR=C:\scripts

echo.
echo ============================================
echo OPERA V5 Night Audit - Installer
echo ============================================
echo.

REM ---------- Step 1: Install Git if missing ----------
where git >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Git is already installed
    goto :clone
)

echo [--] Git not found. Attempting to install...

REM Try winget first (built into Windows Server 2019+)
where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo      Installing via winget...
    winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
    if %errorlevel% equ 0 (
        echo [OK] Git installed via winget
        goto :refresh_path
    )
)

REM Fallback: download Git for Windows installer via PowerShell
echo      winget unavailable or failed - downloading Git installer...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/Git-2.43.0-64-bit.exe' -OutFile '%TEMP%\git-installer.exe' -UseBasicParsing; exit 0 } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download Git installer
    echo Please install Git manually from https://git-scm.com/download/win
    pause
    exit /b 1
)

echo      Running Git installer silently...
"%TEMP%\git-installer.exe" /VERYSILENT /NORESTART /NOCANCEL /SP- /COMPONENTS="icons,ext\reg\shellhere,assoc,assoc_sh"
if %errorlevel% neq 0 (
    echo [ERROR] Git installer failed
    pause
    exit /b 1
)
echo [OK] Git installed

:refresh_path
REM Refresh PATH so git is available in this session
set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git installed but not found in PATH. Close this window and open a NEW command prompt, then re-run install.bat
    pause
    exit /b 1
)

:clone
REM ---------- Step 2: Clone or update repo ----------
if not exist %INSTALL_DIR% mkdir %INSTALL_DIR%
cd /d %INSTALL_DIR%

if exist %INSTALL_DIR%\.git (
    echo [--] Repo already exists at %INSTALL_DIR% - pulling latest...
    git pull
) else (
    echo [--] Cloning repo to %INSTALL_DIR%...
    git clone %REPO_URL% .
    if %errorlevel% neq 0 (
        echo [ERROR] git clone failed. Check the URL and network connection.
        pause
        exit /b 1
    )
)

REM ---------- Step 3: Create config.py from template ----------
if exist %INSTALL_DIR%\config.py (
    echo [OK] config.py already exists - not overwriting
) else (
    echo [--] Creating config.py from template...
    copy %INSTALL_DIR%\config.example.py %INSTALL_DIR%\config.py >nul
    echo [OK] config.py created
    echo.
    echo ============================================
    echo NEXT: Edit config.py with your API keys and OPERA URL
    echo ============================================
    notepad %INSTALL_DIR%\config.py
)

echo.
echo ============================================
echo Installation complete!
echo ============================================
echo.
echo To update in the future, just run:
echo    cd C:\scripts ^&^& git pull
echo.
echo To test the night audit:
echo    C:\scripts\run_night_audit.bat
echo.
echo To schedule daily at 2am:
echo    schtasks /create /tn "OPERA Night Audit" /tr "C:\scripts\run_night_audit.bat" /sc daily /st 02:00 /ru Administrator /rp * /rl highest /it
echo.
pause
endlocal
