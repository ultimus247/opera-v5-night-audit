"""
OPERA Night Audit - main workflow script

All machine-specific settings live in config.py (gitignored).
To update this script, run `git pull` in C:\\scripts\\.
"""
import os
import sys
import subprocess

# Load config BEFORE importing opera_auto so ANTHROPIC_API_KEY is available
try:
    import config
except ImportError:
    print("ERROR: config.py not found. Copy config.example.py to config.py and edit it.")
    sys.exit(1)

os.environ["ANTHROPIC_API_KEY"] = config.ANTHROPIC_API_KEY
if getattr(config, "LINEAR_API_KEY", None):
    os.environ["LINEAR_API_KEY"] = config.LINEAR_API_KEY

from opera_auto import *
from alert_opera_down import (
    alert_opera_down,
    alert_night_audit_not_run,
    alert_night_audit_failed,
)


def audit_log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    with open(config.LOG_FILE, "a") as lf:
        lf.write(line + "\n")


def do_until(instruction, verify, retries=3, post_wait=0):
    for attempt in range(retries):
        log(f"  Attempt {attempt+1}/{retries}")
        do(instruction)
        if post_wait:
            log(f"  Waiting {post_wait}s...")
            time.sleep(post_wait)
        else:
            time.sleep(3)
        if check(verify):
            log("  Verified - moving on")
            return True
    log("  WARNING: Could not verify after retries")
    return False


def fail_and_exit(alert_fn, phase_name, reason, exit_code=1):
    """Log a reason, file a Linear ticket, close IE, and exit the script."""
    audit_log(f"FAIL [{phase_name}]: {reason}")
    try:
        alert_fn(phase_name, reason)
    except Exception as e:
        audit_log(f"  Failed to file Linear ticket: {e}")
    try:
        subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
    except Exception:
        pass
    audit_log("=== OPERA Night Audit ABORTED ===")
    sys.exit(exit_code)


audit_log("=== OPERA Night Audit Started ===")

# Phase 0: Open IE Browser to OPERA
audit_log("Phase 0: Opening IE Browser")
subprocess.Popen([config.IE_PATH, config.OPERA_URL])
time.sleep(4)

opera_loaded = check("Is this the OPERA login screen with username and password fields? If yes no action needed.")
if not opera_loaded:
    time.sleep(10)
    opera_loaded = check("Is this the OPERA login screen with username and password fields? If yes no action needed.")
if not opera_loaded:
    audit_log("ALERT: OPERA did not load - server may be down")
    try:
        alert_opera_down()
    except Exception as e:
        audit_log(f"  Failed to file Linear ticket: {e}")
    try:
        subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
    except Exception:
        pass
    audit_log("=== OPERA Night Audit ABORTED ===")
    sys.exit(1)

# Phase 1: Login - if we can't reach the main menu, OPERA is not responsive -> file OPERA down ticket
audit_log("Phase 1: Login")
if not do_until("Click the Login button on the OPERA login screen.",
                "Is this the OPERA main menu with buttons like PMS and End of Day? If yes no action needed."):
    audit_log("FAIL [Phase 1]: Could not reach OPERA main menu after clicking Login")
    try:
        alert_opera_down()
    except Exception as e:
        audit_log(f"  Failed to file Linear ticket: {e}")
    try:
        subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
    except Exception:
        pass
    audit_log("=== OPERA Night Audit ABORTED ===")
    sys.exit(1)

# Phase 2: Navigate to End of Day - if End of Day button not clickable, night audit did not run
audit_log("Phase 2: Navigate to End of Day")
if not do_until("Click the End of Day button on the OPERA main menu.",
                "Is this the OPERA End of Day Login dialog? If yes no action needed."):
    fail_and_exit(alert_night_audit_not_run, "Phase 2: Navigate to End of Day",
                  "End of Day button not reachable from the OPERA main menu")

# Phase 3: End of Day Login - if we can't log in to End of Day module, night audit did not run
audit_log("Phase 3: End of Day Login")
if not do_until("Click the Login button on the OPERA End of Day Login dialog.",
                "Is there a dialog asking about moving the business date, or a password expired dialog, or the End of Day Routine screen? If yes no action needed."):
    fail_and_exit(alert_night_audit_not_run, "Phase 3: End of Day Login",
                  "Could not log in to the End of Day module")

# Phase 3b: Handle password expired dialog (if present) - if it lingers, password needs changing
check("If you see a dialog saying Password has expired with an OK button, click OK. If no such dialog, no action needed.")
time.sleep(2)
still_expired = not check("Is there still a Password has expired dialog visible on screen? If yes no action needed (the dialog is still visible).")
if still_expired:
    fail_and_exit(alert_night_audit_not_run, "Phase 3b: Password expired",
                  "Password expired dialog is still visible after OK click - SUPERVISOR password must be changed manually")

# Phase 4: Read the roll-to date from the confirm dialog, compare against system date, then Yes
audit_log("Phase 4: Verify roll-to date and confirm")
business_date = None  # populated from the OPERA confirm dialog; used in final log
try:
    import base64, re as _re
    from anthropic import Anthropic
    from datetime import datetime, timedelta

    adapter = LocalAdapter()
    obs = adapter.observe()
    img = Image.open(io.BytesIO(obs.screenshot))
    resized = img.resize((1280, 800))
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
    resp = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=100,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                {"type": "text", "text": "Look at the OPERA dialog box asking about moving the business date. It reads like 'Are you sure you want to move the business date from MM-DD-YY to MM-DD-YY?'. Reply with ONLY the FROM date and TO date separated by a space in MM-DD-YY format. Example: '04-15-26 04-16-26'. Look ONLY at the OPERA dialog - ignore other windows."}
            ]
        }]
    )
    dates_raw = resp.content[0].text.strip()
    audit_log(f"  Dates from OPERA dialog: {dates_raw}")

    dates = _re.findall(r"(\d{2})-(\d{2})-(\d{2})", dates_raw)
    if len(dates) >= 2:
        from_parts, to_parts = dates[0], dates[1]
        roll_from = datetime(2000 + int(from_parts[2]), int(from_parts[0]), int(from_parts[1])).date()
        roll_to = datetime(2000 + int(to_parts[2]), int(to_parts[0]), int(to_parts[1])).date()
        today = datetime.now().date()
        audit_log(f"  System date: {today.strftime('%m-%d-%y')}, From: {roll_from.strftime('%m-%d-%y')}, To: {roll_to.strftime('%m-%d-%y')}")

        if roll_from >= today:
            reason = (f"OPERA business date ({roll_from.strftime('%m-%d-%y')}) is already "
                      f"equal to or ahead of the system date ({today.strftime('%m-%d-%y')}). "
                      f"Night audit appears to have already run today - refusing to roll forward.")
            do("Click the No button on the dialog asking about moving the business date. Do NOT click Yes.")
            time.sleep(3)
            fail_and_exit(alert_night_audit_not_run, "Phase 4: Confirm Roll Business Date", reason)

        if roll_to > today:
            reason = (f"Roll-to date ({roll_to.strftime('%m-%d-%y')}) is after the system date "
                      f"({today.strftime('%m-%d-%y')}). Refusing to roll past real calendar time.")
            do("Click the No button on the dialog asking about moving the business date. Do NOT click Yes.")
            time.sleep(3)
            fail_and_exit(alert_night_audit_not_run, "Phase 4: Confirm Roll Business Date", reason)

        business_date = roll_to.strftime("%m-%d-%y")
    else:
        audit_log(f"  Could not parse from/to dates from '{dates_raw}' - proceeding without safety check")
except SystemExit:
    raise
except Exception as e:
    audit_log(f"  Date safety check errored: {e} - proceeding anyway")

if not do_until("Click the Yes button to confirm moving the business date.",
                "Is this the End of Day Routine screen showing the list of steps? If yes no action needed.",
                post_wait=1):
    fail_and_exit(alert_night_audit_not_run, "Phase 4: Confirm Roll Business Date",
                  "Clicked Yes on the roll dialog but End of Day Routine screen never appeared")

# Phase 5: Start End of Day Routine - must verify it actually began
audit_log("Phase 5: Start End of Day Routine")
if not do_until("Click the Start button at the bottom of the End of Day Routine screen.",
                "Is the End of Day Routine now processing? Look for any step marked with an X, a highlighted step, or a dialog like Country/State Check or Departures opening. If yes no action needed.",
                post_wait=5):
    fail_and_exit(alert_night_audit_not_run, "Phase 5: Start End of Day Routine",
                  "Clicked Start but the End of Day routine did not begin processing")

# Phase 6: Country/State Check (only if popup appears)
audit_log("Phase 6: Country/State Check")
try:
    time.sleep(5)
    cs_clean = check("Look at this OPERA screen. ONLY if you see a SEPARATE popup dialog window on top of the End of Day Routine asking about Country or State issues, click Close on that popup. If you only see the End of Day Routine list with steps processing or X marks, there is no dialog - no action needed.")
    if not cs_clean:
        audit_log("  Country/State issue detected - handling...")
        time.sleep(5)
        check("If there is still a Country Check dialog visible, click the Close button at the bottom right of the dialog. If no dialog, no action needed.")
except Exception as e:
    fail_and_exit(alert_night_audit_failed, "Phase 6: Country/State Check",
                  f"Unexpected error: {e}")

# Phase 7: Departures Check (handle DUE OUT guests)
audit_log("Phase 7: Departures Check")
try:
    time.sleep(5)
    # Open Cashier dialog
    cashier = not check("Look at this screen. If you see a dialog asking Do you want to open the Cashier with Yes and No buttons, click the YES button on the LEFT side. Do NOT click No. If no such dialog, no action needed.")
    if cashier:
        audit_log("  Opened Cashier")
        time.sleep(5)

    # Loop through DUE OUT guests
    for guest_num in range(50):
        has_guests = not check("Look at this OPERA screen. If you see an In House Guest Search screen showing guests with DUE OUT status in the list, click on the FIRST guest name in the list. If you see the End of Day Routine list with Departures marked X, there are no guests - no action needed.")
        if not has_guests:
            audit_log(f"  Departures complete ({guest_num} guests checked out)")
            # Close In House Guest Search and handle cashier dialogs
            do("The guest list is empty. Click the Close button on the right side of the In House Guest Search window.")
            time.sleep(3)
            do("If you see a dialog asking Do you want to close the Cashier, click the YES button on the LEFT side.")
            time.sleep(3)
            do("If you see a Cashier Closure Summary screen, click the OK button.")
            time.sleep(3)
            do("If you see a Cashier Closure or Shift Drop screen, click the OK button.")
            time.sleep(3)
            do("If you see a dialog asking to verify your cash drop before closing, click Yes on the LEFT side. If no dialog, reply DONE.")
            time.sleep(3)
            do("If you see a Cashier Closed dialog with an OK button, click OK.")
            time.sleep(3)
            break
        audit_log(f"  Checking out guest {guest_num + 1}...")
        time.sleep(3)
        do("Click the Billing button for this guest.")
        time.sleep(3)
        do("Click the Payment button on the billing screen.")
        time.sleep(3)
        do("Click the Post button to post the payment and zero the balance.")
        time.sleep(3)
        do("If you see a dialog asking about printing a receipt, click No.")
        time.sleep(3)
        do("Click the Check Out button to complete checkout for this guest.")
        time.sleep(3)
        do("If you see a Check Out Options dialog, click OK.")
        time.sleep(3)
        do("If you see any printer preview or print dialog windows, close them by clicking the X button in the top right corner of the dialog. If no print dialogs, reply DONE.")
        time.sleep(3)
        do("If there are still any printer or preview dialogs open, close them by clicking the X button. If none, reply DONE.")
        time.sleep(3)
        do("Click the Close button at the bottom right of the billing screen to return to the guest list.")
except SystemExit:
    raise
except Exception as e:
    fail_and_exit(alert_night_audit_failed, "Phase 7: Departures Check",
                  f"Unexpected error during guest checkout loop: {e}")

# Phase 8: Monitor Remaining Steps (returns when End of Day is complete, does NOT log off)
audit_log("Phase 8: Monitor Remaining Steps")
try:
    MONITOR = "Look at this OPERA screen. If you see a dialog saying End of Day Routine is now complete with an OK button, click OK. If you see a Print Final Reports screen with ALL reports showing Filed, click Close. If you see the End of Day Routine list still processing, or Print Final Reports with reports Running, do NOT click anything - reply DONE. Otherwise reply DONE."
    reached_menu = wait_and_handle(MONITOR, auto_logoff=False)
    if not reached_menu:
        fail_and_exit(alert_night_audit_failed, "Phase 8: Monitor Remaining Steps",
                      "Monitor exhausted max checks without detecting the OPERA main menu - "
                      "End of Day routine may be stuck or the completion dialog was not handled")
except SystemExit:
    raise
except Exception as e:
    fail_and_exit(alert_night_audit_failed, "Phase 8: Monitor Remaining Steps",
                  f"Unexpected error while monitoring End of Day routine: {e}")

# Log the business date we captured from the Phase 4 confirm dialog
if business_date:
    audit_log(f"Business Date (rolled to): {business_date}")
else:
    audit_log("Business Date: UNKNOWN (could not parse from Phase 4 dialog)")

# Phase 9: Log off OPERA
audit_log("Phase 9: Log off OPERA")
try:
    do("Click the [Log off] link in the upper left of the OPERA main menu, located under Welcome Opera Supervisor.")
    time.sleep(3)
except Exception as e:
    fail_and_exit(alert_night_audit_failed, "Phase 9: Log off OPERA",
                  f"Unexpected error clicking Log off: {e}")

# Phase 10: Close IE (best-effort cleanup, no alert even if it fails)
audit_log("Phase 10: Close IE")
subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
time.sleep(2)

audit_log("=== OPERA Night Audit Complete ===")
