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
    subprocess.Popen([r"C:\scripts\alertOperaisDown.bat"])
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

# Phase 4: Confirm Roll Business Date
audit_log("Phase 4: Confirm Roll Business Date")
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

# Phase 8: Monitor Remaining Steps
audit_log("Phase 8: Monitor Remaining Steps")
MONITOR = "Look at this OPERA screen. If you see a dialog saying End of Day Routine is now complete with an OK button, click OK. If you see a Print Final Reports screen with ALL reports showing Filed, click Close. If you see the End of Day Routine list still processing, or Print Final Reports with reports Running, do NOT click anything - reply DONE. Otherwise reply DONE."
wait_and_handle(MONITOR)

# Phase 9: Exit End of Day
audit_log("Phase 9: Exit End of Day")
do("Click the Exit button at the bottom of the End of Day Routine screen, next to Start and Setup.")
time.sleep(5)

# Phase 10: Log off OPERA
audit_log("Phase 10: Log off OPERA")
do("Click the Log off link on the OPERA main menu. It is in the left panel under Welcome Opera Supervisor.")
time.sleep(5)

# Phase 11: Close IE
audit_log("Phase 11: Close IE")
subprocess.run("taskkill /F /IM iexplore.exe", shell=True, capture_output=True)
time.sleep(2)

# Read business date for log
audit_log("Reading business date from final screen...")
adapter = LocalAdapter()
obs = adapter.observe()
img = Image.open(io.BytesIO(obs.screenshot))
resized = img.resize((1280, 800))
buf = io.BytesIO()
resized.save(buf, format="PNG")
new_obs = BenchmarkObservation(screenshot=buf.getvalue(), viewport=(1280, 800))
agent = ApiAgent(provider="anthropic")
task = BenchmarkTask(task_id="read",
                     instruction="What is the Business Date shown on this screen? Reply ONLY with the date, nothing else. Do NOT click anything.",
                     domain="opera")
action = agent.act(new_obs, task)
raw = (action.raw_action or {}).get("code", str(action.raw_action))
audit_log(f"Business Date from screen: {raw}")
audit_log("=== OPERA Night Audit Complete ===")
