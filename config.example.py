"""
OPERA V5 Night Audit - Per-Machine Configuration

Copy this file to config.py and edit the values below.
config.py is gitignored so your credentials stay out of source control.

After editing, you can update scripts via `git pull` without losing config.
"""

# ============================================================
# API Keys
# ============================================================

# Anthropic API key for Claude vision
# Get one at: https://console.anthropic.com/settings/keys
ANTHROPIC_API_KEY = "sk-ant-YOUR_KEY_HERE"

# Linear API key for alerting when OPERA is down
# Get one at: https://linear.app/settings/account/security
# Leave blank to disable Linear alerting
LINEAR_API_KEY = "lin_api_YOUR_KEY_HERE"


# ============================================================
# OPERA Configuration
# ============================================================

# Full OPERA login URL for this machine
OPERA_URL = "https://win-HOSTNAME:4443/OperaLogin/Welcome.do"

# Optional override for hostname used in Linear alerts
# Leave as None to use socket.gethostname()
HOSTNAME_OVERRIDE = None


# ============================================================
# Paths (usually do not need to change)
# ============================================================

LOG_FILE = r"C:\scripts\automations\operaNightAudit.log"

# Days of log history to retain. Older entries are trimmed at the start of
# each night audit run. Default is 7 days.
LOG_RETENTION_DAYS = 7

# Python executable - "python" uses PATH (recommended if installed via install.bat)
# Override with a full path if you have multiple Python versions
PYTHON_EXE = "python"

IE_PATH = r"C:\Program Files\Internet Explorer\iexplore.exe"


# ============================================================
# Linear Settings (defaults OK)
# ============================================================

# Team the ticket gets filed under. Defaults to PMS Gateway since PMS Expert
# was retired. Other PMS-related teams:
#   PMS Gateway:  515cee73-1094-4fff-8381-d7eb7cb27f13
#   PMS Platform: 5eaff536-f26e-4c52-95e7-bcf6add5c179
#   PMS Product:  3b6017c5-8e28-4d9f-ae0d-e7d5f6fa97fc
#   PMS Support:  cdcd1866-632f-4ba2-8c3d-0c0907b28cd8
LINEAR_TEAM_ID = "515cee73-1094-4fff-8381-d7eb7cb27f13"

# User the ticket is assigned to. Default is David Thomson.
LINEAR_ASSIGNEE_ID = "8ee07a71-a684-4c25-846b-0c0df6690892"

LINEAR_PRIORITY_URGENT = 1
