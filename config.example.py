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

LOG_FILE = r"C:\scripts\operaNightAudit.log"
PYTHON_EXE = r"C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\python.exe"
IE_PATH = r"C:\Program Files\Internet Explorer\iexplore.exe"


# ============================================================
# Linear Settings (defaults OK)
# ============================================================

# PMS Expert team in Linear
LINEAR_TEAM_ID = "1c9cf14c-07e8-4c83-b8d7-1f5cce95d540"
LINEAR_PRIORITY_URGENT = 1
