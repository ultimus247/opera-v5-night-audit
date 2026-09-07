"""
OPERA Night Audit - main workflow script

All machine-specific settings live in config.py (gitignored).
To update this script, run `git pull` in C:\\scripts\\automations.
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

# Catch-up safety limits
MAX_CATCHUP_ITERATIONS = 10  # safety bound; won't ever roll more than 10 days in one run

# A night audit always advances the business date by exactly one day. Any other
# gap means we misread the dialog, not that OPERA is doing something exotic.
EXPECTED_ROLL_DAYS = 1

# Long-edge cap for screenshots sent purely to READ text (dates in dialogs).
# opera_auto sends a fixed 1280x800 because it scales click coordinates back
# from that space - do not reuse this there. Here nothing is clicked, so we
# preserve the aspect ratio and send more pixels, which makes OPERA's small
# dialog text far less likely to be misread (6 vs 8 vs 9).
OCR_MAX_EDGE = 1568


def ocr_screenshot_b64():
    """Screenshot for text reading only. Aspect-preserving, higher resolution
    than the click path. Never derive click coordinates from this image."""
    adapter = LocalAdapter()
    obs = adapter.observe()
    img = Image.open(io.BytesIO(obs.screenshot))
    # Pillow renamed/removed some resampling aliases in 10.0; LANCZOS survived,
    # but fall back rather than crash an unattended 2am run on an odd version.
    img.thumbnail((OCR_MAX_EDGE, OCR_MAX_EDGE), getattr(Image, "LANCZOS", Image.BICUBIC))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def audit_log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}"
    print(line)
    with open(config.LOG_FILE, "a") as lf:
        lf.write(line + "\n")


# Log retention: keep this many days of history in operaNightAudit.log.
# Older entries are trimmed at the start of every run.
LOG_RETENTION_DAYS = getattr(config, "LOG_RETENTION_DAYS", 7)


def rotate_log(log_path, keep_days):
    """Trim a log file in-place to keep only entries from the last `keep_days`.
    Log entries are expected to start with a 'YYYY-MM-DD HH:MM:SS' timestamp.
    Best-effort: any errors are swallowed so a corrupt log can't block the audit.
    """
    from datetime import datetime, timedelta
    if not os.path.exists(log_path):
        return
    try:
        cutoff = (datetime.now() - timedelta(days=keep_days)).strftime("%Y-%m-%d %H:%M:%S")
        with open(log_path, "r") as f:
            lines = f.readlines()
        # Find first line whose leading timestamp is >= cutoff.
        # YYYY-MM-DD HH:MM:SS sorts lexicographically, so string compare works.
        keep_from = None
        for i, line in enumerate(lines):
            ts = line[:19]
            # Only consider lines that look like a valid timestamp
            if len(ts) == 19 and ts[4] == "-" and ts[10] == " " and ts >= cutoff:
                keep_from = i
                break
        if keep_from is None:
            # All entries are older than cutoff - clear the file entirely
            keep_from = len(lines)
        if keep_from > 0:
            removed = keep_from
            with open(log_path, "w") as f:
                f.writelines(lines[keep_from:])
                f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} === Log rotated: removed {removed} entries older than {keep_days} days ===\n")
    except Exception:
        # Don't let log rotation block the audit
        pass


# Rotate the log file before writing anything new this run
rotate_log(config.LOG_FILE, LOG_RETENTION_DAYS)


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


def run_audit_iteration(iteration_label):
    """Run one full night audit (Phases 1-9 - everything except open/close IE).

    Returns:
        roll_to (date) on success - the date OPERA was rolled to.
        None if dates could not be parsed (audit may still have run).
    On failure, calls fail_and_exit (script terminates).
    """
    import base64, re as _re
    from anthropic import Anthropic
    from datetime import datetime, timedelta

    # Phase 1: Login - if we can't reach the main menu, OPERA is not responsive -> file OPERA down ticket
    audit_log(f"[{iteration_label}] Phase 1: Login")
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

    # Phase 2: Navigate to End of Day
    audit_log(f"[{iteration_label}] Phase 2: Navigate to End of Day")
    if not do_until("Click the End of Day button on the OPERA main menu.",
                    "Is this the OPERA End of Day Login dialog? If yes no action needed."):
        fail_and_exit(alert_night_audit_not_run, "Phase 2: Navigate to End of Day",
                      "End of Day button not reachable from the OPERA main menu")

    # Phase 3: End of Day Login
    audit_log(f"[{iteration_label}] Phase 3: End of Day Login")
    if not do_until("Click the Login button on the OPERA End of Day Login dialog.",
                    "Is there a dialog asking about moving the business date, or a password expired dialog, or the End of Day Routine screen? If yes no action needed."):
        fail_and_exit(alert_night_audit_not_run, "Phase 3: End of Day Login",
                      "Could not log in to the End of Day module")

    # Phase 3b: Handle password expired dialog (if present)
    check("If you see a dialog saying Password has expired with an OK button, click OK. If no such dialog, no action needed.")
    time.sleep(2)
    still_expired = not check("Is there still a Password has expired dialog visible on screen? If yes no action needed (the dialog is still visible).")
    if still_expired:
        fail_and_exit(alert_night_audit_not_run, "Phase 3b: Password expired",
                      "Password expired dialog is still visible after OK click - SUPERVISOR password must be changed manually")

    # Phase 4: Read the roll-to date from the confirm dialog, compare against system date, then Yes
    audit_log(f"[{iteration_label}] Phase 4: Verify roll-to date and confirm")
    roll_to = None  # date object - populated from the OPERA confirm dialog
    dates_captured = False
    for date_attempt in range(3):
        try:
            time.sleep(3)
            img_b64 = ocr_screenshot_b64()

            client = Anthropic(api_key=config.ANTHROPIC_API_KEY)
            resp = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=150,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                        {"type": "text", "text": "Look at this OPERA screen. Answer with ONE of these:\n1. If you see a dialog asking 'Are you sure you want to move the business date from MM-DD-YY to MM-DD-YY?', reply with ONLY the two dates in MM-DD-YY format separated by a space. Example: '04-15-26 04-16-26'\n2. If you see the End of Day Routine screen (list of steps like Country and State Check, Departures, etc.), reply ROUTINE\n3. If you see the End of Day Login screen, reply LOGIN\nLook ONLY at OPERA windows - ignore command prompts, taskbars, or other windows."}
                    ]
                }]
            )
            screen_response = resp.content[0].text.strip()
            audit_log(f"  Phase 4 attempt {date_attempt+1}: {screen_response}")

            # Case 1: Roll date confirmation dialog with both dates
            dates = _re.findall(r"(\d{2})-(\d{2})-(\d{2})", screen_response)
            if len(dates) >= 2:
                from_parts, to_parts = dates[0], dates[1]
                roll_from = datetime(2000 + int(from_parts[2]), int(from_parts[0]), int(from_parts[1])).date()
                roll_to_parsed = datetime(2000 + int(to_parts[2]), int(to_parts[0]), int(to_parts[1])).date()
                today = datetime.now().date()
                audit_log(f"  System date: {today.strftime('%m-%d-%y')}, From: {roll_from.strftime('%m-%d-%y')}, To: {roll_to_parsed.strftime('%m-%d-%y')}")

                # A misread digit (6 read as 9) produces a plausible-looking but
                # wrong TO date, which used to surface as a bogus "refusing to roll
                # past real calendar time" abort. The roll is always exactly one
                # day, so anything else means the OCR is wrong - retry the read
                # rather than acting on it or alerting on it.
                gap_days = (roll_to_parsed - roll_from).days
                if gap_days != EXPECTED_ROLL_DAYS:
                    audit_log(
                        f"  Misread: dialog parsed as {roll_from.strftime('%m-%d-%y')} -> "
                        f"{roll_to_parsed.strftime('%m-%d-%y')} ({gap_days} days). "
                        f"A night audit always rolls exactly {EXPECTED_ROLL_DAYS} day. "
                        f"Re-reading (attempt {date_attempt+1}/3)..."
                    )
                    continue

                if roll_from >= today:
                    reason = (f"OPERA business date ({roll_from.strftime('%m-%d-%y')}) is already "
                              f"equal to or ahead of the system date ({today.strftime('%m-%d-%y')}). "
                              f"Night audit appears to have already run today - refusing to roll forward.")
                    do("Click the No button on the dialog asking about moving the business date. Do NOT click Yes.")
                    time.sleep(3)
                    fail_and_exit(alert_night_audit_not_run, "Phase 4: Confirm Roll Business Date", reason)

                if roll_to_parsed > today:
                    reason = (f"Roll-to date ({roll_to_parsed.strftime('%m-%d-%y')}) is after the system date "
                              f"({today.strftime('%m-%d-%y')}). Refusing to roll past real calendar time.")
                    do("Click the No button on the dialog asking about moving the business date. Do NOT click Yes.")
                    time.sleep(3)
                    fail_and_exit(alert_night_audit_not_run, "Phase 4: Confirm Roll Business Date", reason)

                roll_to = roll_to_parsed
                dates_captured = True
                break

            # Case 2: Already at EOD Routine screen (dialog was auto-dismissed)
            if "ROUTINE" in screen_response.upper():
                audit_log("  Already at End of Day Routine screen - roll dialog was auto-handled")
                resp2 = client.messages.create(
                    model="claude-sonnet-4-5-20250929",
                    max_tokens=50,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_b64}},
                            {"type": "text", "text": "Look at the title bar of the End of Day Routine window. It shows a date like 'End of Day - MM-DD-YY'. Reply with ONLY the date in MM-DD-YY format. Ignore other windows."}
                        ]
                    }]
                )
                title_date = resp2.content[0].text.strip()
                title_dates = _re.findall(r"(\d{2})-(\d{2})-(\d{2})", title_date)
                if title_dates:
                    parts = title_dates[0]
                    # The title bar shows the FROM date. Add 1 day for the TO date.
                    title_from = datetime(2000 + int(parts[2]), int(parts[0]), int(parts[1])).date()
                    roll_to = title_from + timedelta(days=1)
                    audit_log(f"  Title bar shows {title_from.strftime('%m-%d-%y')} (FROM); rolling to {roll_to.strftime('%m-%d-%y')} (TO)")
                dates_captured = True
                break

            # Case 3: Still on Login - retry
            if "LOGIN" in screen_response.upper():
                audit_log(f"  Still on Login screen, waiting for roll dialog (attempt {date_attempt+1}/3)...")
                continue

            audit_log("  Unexpected screen state, retrying...")

        except SystemExit:
            raise
        except Exception as e:
            audit_log(f"  Date check attempt {date_attempt+1} errored: {e}")

    if not dates_captured:
        # Previously this proceeded and clicked Yes without ever having read the
        # dialog, which can roll the business date past real calendar time - the
        # exact outcome the safety check exists to prevent. Failing the run is
        # recoverable (run it again); a wrongly rolled business date is not.
        reason = (
            "Could not read the roll-date dialog after 3 attempts, so the roll-to "
            "date was never verified. Refusing to confirm the roll blind. "
            "Check the OPERA screen state on this machine and re-run."
        )
        do("Click the No button on the dialog asking about moving the business date. Do NOT click Yes.")
        time.sleep(3)
        fail_and_exit(alert_night_audit_not_run, "Phase 4: Confirm Roll Business Date", reason)

    # Click Yes (if dialog still visible) and verify EOD Routine screen
    if not do_until("Click the Yes button to confirm moving the business date. If you see the End of Day Routine screen already, no action needed.",
                    "Is this the End of Day Routine screen showing the list of steps? If yes no action needed.",
                    post_wait=1):
        fail_and_exit(alert_night_audit_not_run, "Phase 4: Confirm Roll Business Date",
                      "Could not reach the End of Day Routine screen after confirming the roll")

    # Phase 5: Start End of Day Routine
    audit_log(f"[{iteration_label}] Phase 5: Start End of Day Routine")
    if not do_until("Click the Start button at the bottom of the End of Day Routine screen.",
                    "Is the End of Day Routine now processing? Look for any step marked with an X, a highlighted step, or a dialog like Country/State Check or Departures opening. If yes no action needed.",
                    post_wait=5):
        fail_and_exit(alert_night_audit_not_run, "Phase 5: Start End of Day Routine",
                      "Clicked Start but the End of Day routine did not begin processing")

    # Phase 6: Country/State Check (only if popup appears)
    audit_log(f"[{iteration_label}] Phase 6: Country/State Check")
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

    # Phase 7: Departures Check
    audit_log(f"[{iteration_label}] Phase 7: Departures Check")
    try:
        time.sleep(5)
        cashier = not check("Look at this screen. If you see a dialog asking Do you want to open the Cashier with Yes and No buttons, click the YES button on the LEFT side. Do NOT click No. If no such dialog, no action needed.")
        if cashier:
            audit_log("  Opened Cashier")
            time.sleep(5)

        for guest_num in range(50):
            has_guests = not check("Look at this OPERA screen. If you see an In House Guest Search screen showing guests with DUE OUT status in the list, click on the FIRST guest name in the list. If you see the End of Day Routine list with Departures marked X, there are no guests - no action needed.")
            if not has_guests:
                audit_log(f"  Departures complete ({guest_num} guests checked out)")
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

    # Phase 8: Monitor Remaining Steps
    audit_log(f"[{iteration_label}] Phase 8: Monitor Remaining Steps")
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

    if roll_to:
        audit_log(f"[{iteration_label}] Business Date (rolled to): {roll_to.strftime('%m-%d-%y')}")
    else:
        audit_log(f"[{iteration_label}] Business Date: UNKNOWN (could not parse from Phase 4 dialog)")

    # Phase 9: Log off OPERA (returns us to the login screen, ready for the next iteration)
    audit_log(f"[{iteration_label}] Phase 9: Log off OPERA")
    try:
        do("Click the [Log off] link in the upper left of the OPERA main menu, located under Welcome Opera Supervisor.")
        time.sleep(3)
    except Exception as e:
        fail_and_exit(alert_night_audit_failed, "Phase 9: Log off OPERA",
                      f"Unexpected error clicking Log off: {e}")

    return roll_to


# ============================================================
# MAIN
# ============================================================
audit_log("=== OPERA Night Audit Started ===")

# Phase 0: Open IE Browser to OPERA (once, regardless of how many catch-up iterations)
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

# Run audit iterations until caught up to today (or safety limit)
from datetime import datetime
final_roll_to = None
for iteration in range(MAX_CATCHUP_ITERATIONS):
    label = f"Iteration {iteration+1}"
    audit_log(f"=== {label} ===")
    roll_to = run_audit_iteration(label)
    final_roll_to = roll_to

    if roll_to is None:
        audit_log("Could not determine roll-to date - stopping catch-up loop")
        break

    today = datetime.now().date()
    if roll_to >= today:
        audit_log(f"Caught up: business date is now {roll_to.strftime('%m-%d-%y')}, system date is {today.strftime('%m-%d-%y')}")
        break

    days_behind = (today - roll_to).days
    audit_log(f"Still {days_behind} day(s) behind today ({today.strftime('%m-%d-%y')}). Running another audit to catch up...")
    time.sleep(5)
else:
    audit_log(f"WARNING: Hit MAX_CATCHUP_ITERATIONS ({MAX_CATCHUP_ITERATIONS}) - "
              f"system may still be behind today's date")

# Phase 10: Close IE
audit_log("Phase 10: Close IE")
subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
time.sleep(2)

if final_roll_to:
    audit_log(f"=== OPERA Night Audit Complete - Final Business Date: {final_roll_to.strftime('%m-%d-%y')} ===")
else:
    audit_log("=== OPERA Night Audit Complete ===")
