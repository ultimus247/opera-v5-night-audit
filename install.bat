@echo off
REM ============================================================
REM OPERA V5 Night Audit - One-shot installer
REM
REM Installs Git + Python (if missing), pip dependencies,
REM clones the repo to C:\scripts, and creates config.py from the template.
REM
REM Usage:
REM   1. Download this file to the target machine
REM   2. Right-click -> Run as administrator
REM ============================================================

setlocal
set REPO_URL=https://github.com/ultimus247/opera-v5-night-audit.git
set INSTALL_DIR=C:\scripts
set PYTHON_WINGET_ID=Python.Python.3.12
set GIT_WINGET_ID=Git.Git

echo.
echo ============================================
echo OPERA V5 Night Audit - Installer
echo ============================================
echo.

REM Must run as administrator
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This installer must be run as Administrator.
    echo Right-click install.bat and select "Run as administrator".
    pause
    exit /b 1
)

REM ---------- Check winget availability ----------
set HAS_WINGET=0
where winget >nul 2>&1
if %errorlevel% equ 0 set HAS_WINGET=1

REM ---------- Step 1: Install Git if missing ----------
where git >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Git is already installed
    goto :install_python
)

echo [--] Git not found. Attempting to install...

if %HAS_WINGET% equ 1 (
    echo      Installing Git via winget...
    winget install --id %GIT_WINGET_ID% -e --source winget --accept-source-agreements --accept-package-agreements
    if %errorlevel% equ 0 (
        echo [OK] Git installed via winget
        goto :refresh_git_path
    )
    echo      winget install failed, falling back to manual download...
)

REM Fallback: download Git for Windows installer via PowerShell
echo      Downloading Git installer...
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

:refresh_git_path
set "PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Git installed but not found in PATH.
    echo Close this window, open a NEW Administrator command prompt, then re-run install.bat
    pause
    exit /b 1
)
echo [OK] Git ready

:install_python
REM ---------- Step 2: Install Python if missing ----------
where python >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Python is already installed
    python --version
    goto :install_deps
)

echo [--] Python not found. Attempting to install...

if %HAS_WINGET% equ 1 (
    echo      Installing Python via winget...
    winget install --id %PYTHON_WINGET_ID% -e --source winget --accept-source-agreements --accept-package-agreements --scope machine
    if %errorlevel% equ 0 (
        echo [OK] Python installed via winget
        goto :refresh_python_path
    )
    echo      winget install failed, falling back to manual download...
)

REM Fallback: download Python installer
echo      Downloading Python 3.12 installer...
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile '%TEMP%\python-installer.exe' -UseBasicParsing; exit 0 } catch { exit 1 }"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to download Python installer
    echo Please install Python manually from https://www.python.org/downloads/
    pause
    exit /b 1
)

echo      Running Python installer silently...
"%TEMP%\python-installer.exe" /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
if %errorlevel% neq 0 (
    echo [ERROR] Python installer failed
    pause
    exit /b 1
)

:refresh_python_path
REM Try common Python install locations
set "PATH=%PATH%;C:\Program Files\Python312;C:\Program Files\Python312\Scripts;C:\Python312;C:\Python312\Scripts"
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python installed but not found in PATH.
    echo Close this window, open a NEW Administrator command prompt, then re-run install.bat
    pause
    exit /b 1
)
echo [OK] Python ready
python --version

:install_deps
REM ---------- Step 3: Install pip dependencies ----------
echo.
echo [--] Installing Python dependencies (this may take a few minutes)...
python -m pip install --upgrade pip
python -m pip install openadapt_evals openadapt-ml anthropic Pillow pywin32 mss
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed

REM ---------- Step 4: Clone or update repo ----------
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

REM ---------- Step 5: Create config.py from template ----------
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
echo    C:\scripts\update.bat
echo    (or: cd C:\scripts ^&^& git pull)
echo.
echo To test the night audit:
echo    C:\scripts\run_night_audit.bat
echo.
echo To schedule daily at 2am:
echo    schtasks /create /tn "OPERA Night Audit" /tr "C:\scripts\run_night_audit.bat" /sc daily /st 02:00 /ru Administrator /rp * /rl highest /it
echo.
pause
endlocal
