# OPERA V5 Night Audit Automation

Automated nightly End of Day routine for Oracle OPERA PMS v5 (on-premise) using Claude API vision and Windows screen automation.

## Architecture

| File | Purpose |
|------|---------|
| `opera_auto.py` | Reusable library: screenshot capture, Claude API vision, mouse/keyboard control |
| `night_audit.py` | Night audit workflow (Phases 0-11) |
| `analyze_recording.py` | Analyzes OpenAdapt recordings to auto-generate automation scripts |
| `run_night_audit.bat` | Batch launcher with API key |
| `alertOperaisDown.bat` | Alert script triggered when OPERA fails to load |
| `alert_opera_down.py` | Creates urgent Linear ticket on PMS Expert team when OPERA is down |

## Deployment to a New Machine

### Prerequisites
- Windows Server 2019 or later
- Python 3.14 installed at `C:\Users\Administrator\AppData\Local\Python\pythoncore-3.14-64\`
- IE configured with OPERA URL as homepage (credentials saved)
- Anthropic API key

### Step 1: Install Python packages
```cmd
pip install openadapt_evals openadapt-ml anthropic Pillow pywin32 mss
```

### Step 2: Create scripts directory and clone repo
```cmd
mkdir C:\scripts
cd C:\scripts
git clone https://github.com/ultimus247/opera-v5-night-audit.git .
```

### Step 3: Configure for this machine
Edit `night_audit.py` and update the OPERA URL on line ~XX:
```python
OPERA_URL = "https://win-XXXXXXXX:4443/OperaLogin/Welcome.do"
```

Edit `run_night_audit.bat` and set your API key:
```batch
set ANTHROPIC_API_KEY=sk-ant-...
```

Set the Linear API key as a system environment variable (used by the alert script when OPERA is down):
```cmd
setx LINEAR_API_KEY "lin_api_..."
```
Get a Linear API key from https://linear.app/settings/account/security

### Step 4: Test
```cmd
C:\scripts\run_night_audit.bat
```

### Step 5: Set up auto-logon (survives reboots)
```cmd
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v AutoAdminLogon /t REG_SZ /d 1 /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultUserName /t REG_SZ /d Administrator /f
reg add "HKLM\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon" /v DefaultPassword /t REG_SZ /d "PASSWORD" /f
```

### Step 6: Schedule the task
```cmd
schtasks /create /tn "OPERA Night Audit" /tr "C:\scripts\run_night_audit.bat" /sc daily /st 02:00 /ru Administrator /rp * /rl highest /it
```

### Step 7: Disconnect RDP without logging off
After verifying everything works, disconnect from RDP using:
```cmd
tscon %sessionname% /dest:console
```
This keeps the desktop session alive so the scheduled task can run with screen access.

## How It Works

1. **Phase 0**: Opens IE to OPERA URL, verifies login screen
2. **Phase 1**: Clicks Login (credentials are pre-filled)
3. **Phase 2**: Clicks End of Day button on main menu
4. **Phase 3**: Clicks Login on End of Day Login dialog
5. **Phase 4**: Confirms rolling business date (Yes button)
6. **Phase 5**: Clicks Start on End of Day Routine
7. **Phase 6**: Handles Country/State Check popup if guests have missing data
8. **Phase 7**: Handles Departures Check — opens Cashier, checks out each DUE OUT guest:
   - Click guest → Billing → Payment → Post → No receipt → Check Out → OK → close printer dialogs → Close billing
   - After all guests: Close In House Guest Search → Close Cashier dialogs until Departures has X
9. **Phase 8**: Monitors remaining steps (Roll Date, Posting Room/Tax, Run Additional, Print Final Reports)
10. **Phase 9**: Detects return to OPERA main menu, clicks Log off
11. **Phase 10**: Closes IE

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

**Log shows "OPERA did not load"**
- IE failed to open or OPERA server is unreachable. Check the URL and network connectivity.

## Adding New Automation Tasks

Use `analyze_recording.py` to bootstrap a new automation:

1. Record the task with OpenAdapt: `openadapt capture start --name TaskName`
2. Stop recording when done
3. Analyze: `python C:\scripts\analyze_recording.py TaskName`
4. Review generated `C:\scripts\analysis\TaskName\summary.txt` and `draft_automation.py`
5. Edit and test

## Notion Page

Full project documentation: [OpenAdapt Installation Guide](https://www.notion.so/32781468615181ab9ac1e82ed9ba2b69)
