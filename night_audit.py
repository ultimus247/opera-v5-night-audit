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
    subprocess.Popen([r"C:\scripts\automations\alertOperaisDown.bat"])
    sys.exit(1)

# Phase 1: Login
audit_log("Phase 1: Login")
do_until("Click the Login button on the OPERA login screen.",
         "Is this the OPERA main menu with buttons like PMS and End of Day? If yes no action needed.")

# Phase 2: Navigate to End of Day
audit_log("Phase 2: Navigate to End of Day")
do_until("Click the End of Day button on the OPERA main menu.",
         "Is this the OPERA End of Day Login dialog? If yes no action needed.")

# Phase 3: End of Day Login
audit_log("Phase 3: End of Day Login")
do_until("Click the Login button on the OPERA End of Day Login dialog.",
         "Is there a dialog asking about moving the business date or the End of Day Routine screen? If yes no action needed.")

# Phase 3b: Handle password expired dialog (if present)
check("If you see a dialog saying Password has expired with an OK button, click OK. If no such dialog, no action needed.")
time.sleep(2)

# Phase 4: Safety check - compare roll-to date with system date, then confirm
audit_log("Phase 4: Verify roll-to date and confirm")
business_date = None  # populated from the OPERA confirm dialog; used in final log
try:
    import base64, re as _re
    from anthropic import Anthropic
    from datetime import datetime

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
                {"type": "text", "text": "Look at the OPERA dialog box asking about moving the business date. It reads like 'Are you sure you want to move the business date from MM-DD-YY to MM-DD-YY?'. Reply with ONLY the TO date (the new date) in MM-DD-YY format, nothing else. Look ONLY at the OPERA dialog - ignore any other windows or command prompts."}
            ]
        }]
    )
    roll_to_raw = resp.content[0].text.strip()
    audit_log(f"  Roll-to date from OPERA dialog: {roll_to_raw}")

    # Parse MM-DD-YY and compare to today
    m = _re.search(r"(\d{2})-(\d{2})-(\d{2})", roll_to_raw)
    if m:
        mm, dd, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
        roll_to = datetime(2000 + yy, mm, dd).date()
        today = datetime.now().date()
        audit_log(f"  System date: {today.strftime('%m-%d-%y')}, Roll-to: {roll_to.strftime('%m-%d-%y')}")
        if roll_to > today:
            audit_log(f"ABORT: roll-to date {roll_to} is after system date {today} - not rolling forward")
            do("If you see a dialog asking about moving the business date, click the No button (right side). Do NOT click Yes.")
            time.sleep(3)
            subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
            sys.exit(0)
        # Safe to proceed - remember this date for the final log
        business_date = roll_to.strftime("%m-%d-%y")
    else:
        audit_log(f"  Could not parse roll-to date '{roll_to_raw}' - proceeding anyway")
except Exception as e:
    audit_log(f"  Date safety check failed: {e} - proceeding anyway")

do_until("Click the Yes button to confirm moving the business date.",
         "Is this the End of Day Routine screen showing the list of steps? If yes no action needed.",
         post_wait=1)

# Phase 5: Start End of Day Routine
audit_log("Phase 5: Start End of Day Routine")
do("Click the Start button at the bottom of the End of Day Routine screen.")
time.sleep(5)

# Phase 6: Country/State Check (only if popup appears)
audit_log("Phase 6: Country/State Check")
time.sleep(5)
cs_clean = check("Look at this OPERA screen. ONLY if you see a SEPARATE popup dialog window on top of the End of Day Routine asking about Country or State issues, click Close on that popup. If you only see the End of Day Routine list with steps processing or X marks, there is no dialog - no action needed.")
if not cs_clean:
    audit_log("  Country/State issue detected - handling...")
    time.sleep(5)
    check("If there is still a Country Check dialog visible, click the Close button at the bottom right of the dialog. If no dialog, no action needed.")

# Phase 7: Departures Check (handle DUE OUT guests)
audit_log("Phase 7: Departures Check")
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

# Phase 8: Monitor Remaining Steps (returns when End of Day is complete, does NOT log off)
audit_log("Phase 8: Monitor Remaining Steps")
MONITOR = "Look at this OPERA screen. If you see a dialog saying End of Day Routine is now complete with an OK button, click OK. If you see a Print Final Reports screen with ALL reports showing Filed, click Close. If you see the End of Day Routine list still processing, or Print Final Reports with reports Running, do NOT click anything - reply DONE. Otherwise reply DONE."
wait_and_handle(MONITOR, auto_logoff=False)

# Log the business date we captured from the Phase 4 confirm dialog
if business_date:
    audit_log(f"Business Date (rolled to): {business_date}")
else:
    audit_log("Business Date: UNKNOWN (could not parse from Phase 4 dialog)")

# Phase 9: Log off OPERA
audit_log("Phase 9: Log off OPERA")
do("Click the [Log off] link in the upper left of the OPERA main menu, located under Welcome Opera Supervisor.")
time.sleep(3)

# Phase 10: Close IE
audit_log("Phase 10: Close IE")
subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
time.sleep(2)

audit_log("=== OPERA Night Audit Complete ===")
