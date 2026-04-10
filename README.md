# OPERA V5 Night Audit Automation

Automated nightly End of Day routine for Oracle OPERA PMS v5 (on-premise) using Claude API vision and Windows screen automation.

## Architecture

| File | Purpose |
|------|---------|
| `config.example.py` | Template for per-machine configuration (copy to `config.py`) |
| `config.py` | **Your** machine settings (gitignored - never committed) |
| `opera_auto.py` | Reusable library: screenshot capture, Claude API vision, mouse/keyboard control |
| `night_audit.py` | 11-phase night audit workflow |
| `analyze_recording.py` | Analyzes OpenAdapt recordings to bootstrap new automations |
| `alert_opera_down.py` | Creates urgent Linear ticket on PMS Expert team when OPERA is down |
| `run_night_audit.bat` | Main launcher |
| `alertOperaisDown.bat` | Alert launcher (called by night_audit.py on failure) |
| `install.bat` | One-shot installer (installs Git, clones repo, creates config) |
| `update.bat` | Pulls latest changes without touching config.py |

## Deployment to a New Machine

### Step 1: Run the bootstrap installer as Administrator

**Option A — PowerShell (works on Server 2012 R2 and later):**

Open PowerShell as Administrator and run:

```powershell
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
iex (iwr https://raw.githubusercontent.com/ultimus247/opera-v5-night-audit/main/bootstrap.ps1 -UseBasicParsing).Content
```

**Option B — CMD (Server 2019+):**

Open an Administrator command prompt and run:

```cmd
powershell -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/ultimus247/opera-v5-night-audit/main/install.bat' -OutFile '%TEMP%\install.bat' -UseBasicParsing" && "%TEMP%\install.bat"
```

The installer will:
1. **Install Git** (via winget on Server 2019+, or download the Git for Windows installer as fallback)
2. **Install Python 3.12** (via winget on Server 2019+, or download the Python installer as fallback)
3. **Install pip dependencies** (`openadapt_evals openadapt-ml anthropic Pillow pywin32 mss`)
4. **Clone this repo** to `C:\scripts\`
5. **Create `config.py`** from the template
6. **Open `config.py`** in notepad for you to edit

> **Server 2012 R2 Note:** winget isn't available on 2012 R2, so the installer will use the manual download fallback for Git and Python. TLS 1.2 is forced in all download commands to work around the old default.

### Step 2: Edit config.py

Set these values in `C:\scripts\config.py`:

```python
ANTHROPIC_API_KEY = "sk-ant-..."                      # Claude API key
LINEAR_API_KEY = "lin_api_..."                        # Linear API key (for alerts)
OPERA_URL = "https://win-HOSTNAME:4443/OperaLogin/Welcome.do"  # Per-machine OPERA URL
```

- Claude API key: https://console.anthropic.com/settings/keys
- Linear API key: https://linear.app/settings/account/security

### Step 3: Test

```cmd
C:\scripts\run_night_audit.bat
```

### Step 4: Schedule daily runs

Auto-logon (survives reboots):
```cmd
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v AutoAdminLogon /t REG_SZ /d 1 /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultUserName /t REG_SZ /d Administrator /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultPassword /t REG_SZ /d "PASSWORD" /f
```

Task Scheduler:
```cmd
schtasks /create /tn "OPERA Night Audit" /tr "C:\scripts\run_night_audit.bat" /sc daily /st 02:00 /ru Administrator /rp * /rl highest /it
```

Disconnect RDP without logging off (keeps desktop session alive):
```cmd
tscon %sessionname% /dest:console
```

### Step 5: Prerequisites

- **Windows Server 2019 or later** (winget is built-in on Server 2019+)
- **Internet Explorer** with OPERA URL set as homepage and credentials saved
- **Administrator access** to run the installer
- **Anthropic API key** from https://console.anthropic.com/settings/keys
- **Linear API key** from https://linear.app/settings/account/security

## Updating Scripts

To pull the latest version without losing your `config.py`:

```cmd
C:\scripts\update.bat
```

or manually:

```cmd
cd C:\scripts && git pull
```

`config.py` is gitignored so your credentials are preserved.

## How It Works

1. **Phase 0**: Opens IE to OPERA URL from config, verifies login screen (alerts Linear if it fails)
2. **Phase 1**: Clicks Login (credentials pre-filled by IE)
3. **Phase 2**: Clicks End of Day button on main menu
4. **Phase 3**: Clicks Login on End of Day Login dialog
5. **Phase 4**: Confirms rolling business date (Yes button)
6. **Phase 5**: Clicks Start on End of Day Routine
7. **Phase 6**: Handles Country/State Check popup if guests have missing data
8. **Phase 7**: Handles Departures Check — opens Cashier, checks out each DUE OUT guest:
   - Click guest → Billing → Payment → Post → No receipt → Check Out → OK → close printer dialogs → Close billing
   - After all guests: Close In House Guest Search → Close Cashier dialogs until Departures has X
9. **Phase 8**: Monitors remaining steps (Roll Date, Posting Room/Tax, Run Additional, Print Final Reports)
10. **Phase 9**: Clicks Exit on End of Day Routine
11. **Phase 10**: Clicks Log off on main menu
12. **Phase 11**: Closes IE

## Alerting

If OPERA fails to load at Phase 0, the script runs `alertOperaisDown.bat` which calls `alert_opera_down.py` to create an **urgent priority** ticket in Linear on the **PMS Expert** team:

- Title: `URGENT: OPERA is DOWN on <hostname>`
- Description includes hostname, timestamp, and action items
- Uses `LINEAR_API_KEY` from `config.py`

## Cost Estimate

- ~$0.50–1.00 per night audit run (15-25 Claude API calls)
- Happy path (no guests): ~$0.30
- With guest checkouts: ~$1.00+ depending on guest count
- 6 machines × 30 days = ~$90–180/month

## Logs

All activity is logged to `C:\scripts\operaNightAudit.log` with timestamps for each phase.

## Troubleshooting

**Mouse clicks don't work in RDP**
- We use `SetCursorPos` + `mouse_event` (Windows API). `pynput` and `pyautogui` don't work in RDP.

**Claude clicks the wrong location**
- Screenshots are resized to 1280x800 before sending to Claude. Coordinates returned by Claude are scaled back to actual screen dimensions in `opera_auto.py`.

**Script gets stuck in monitor loop**
- Phase 8 waits up to 30 checks for End of Day to complete. If your hotel has many reports, increase `max_checks` in `wait_and_handle()`.

**"config.py not found" error**
- Copy `config.example.py` to `config.py` and edit it, or run `install.bat` again.

**Git pull conflicts with config.py**
- This shouldn't happen since `config.py` is gitignored. If it does, commit your config.py changes locally first.

## Adding New Automation Tasks

Use `analyze_recording.py` to bootstrap a new automation:

1. Record the task with OpenAdapt: `openadapt capture start --name TaskName`
2. Stop recording when done
3. Analyze: `python C:\scripts\analyze_recording.py TaskName`
4. Review generated `C:\scripts\analysis\TaskName\summary.txt` and `draft_automation.py`
5. Edit and test

## Notion Page

Full project documentation: [OpenAdapt Installation Guide](https://www.notion.so/32781468615181ab9ac1e82ed9ba2b69)
