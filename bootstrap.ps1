# ============================================================
# OPERA V5 Night Audit - Bootstrap script
#
# Downloads and runs install.bat from GitHub.
# Works on Windows Server 2012 R2 and later (forces TLS 1.2).
#
# Usage (run in Administrator PowerShell):
#   iex (iwr https://raw.githubusercontent.com/ultimus247/opera-v5-night-audit/main/bootstrap.ps1).Content
# ============================================================

# Force TLS 1.2 (required on Server 2012 R2 which defaults to TLS 1.0)
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator." -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as administrator', then re-run this command."
    exit 1
}

$installerUrl = "https://raw.githubusercontent.com/ultimus247/opera-v5-night-audit/main/install.bat"
$installerPath = "$env:TEMP\install.bat"

Write-Host "Downloading installer from $installerUrl..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath -UseBasicParsing
} catch {
    Write-Host "ERROR: Failed to download installer: $_" -ForegroundColor Red
    exit 1
}

Write-Host "Running installer..." -ForegroundColor Cyan
& cmd.exe /c $installerPath
