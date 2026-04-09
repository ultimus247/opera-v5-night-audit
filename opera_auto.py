import ctypes, time, re, subprocess, os, io
from PIL import Image
from openadapt_evals import ApiAgent
from openadapt_evals.adapters import LocalAdapter
from openadapt_evals.adapters.base import BenchmarkTask, BenchmarkObservation

SEND_W, SEND_H = 1280, 800

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} {msg}")

def click_raw(x, y):
    ctypes.windll.user32.SetCursorPos(x, y)
    time.sleep(0.3)
    ctypes.windll.user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.1)
    ctypes.windll.user32.mouse_event(0x0004, 0, 0, 0, 0)
    log(f"  Clicked ({x},{y})")

def press_key(key_name):
    keys = {"enter": 0x0D, "tab": 0x09, "escape": 0x1B, "space": 0x20}
    vk = keys.get(key_name.lower(), 0)
    if vk:
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        log(f"  Pressed {key_name}")

def type_text(text):
    for ch in text:
        vk = ctypes.windll.user32.VkKeyScanW(ord(ch))
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
    log(f"  Typed: {text}")

def do(instruction, wait=3):
    log(f"  Task: {instruction}")
    agent = ApiAgent(provider="anthropic")
    adapter = LocalAdapter()
    task = BenchmarkTask(task_id="auto", instruction=instruction, domain="opera")
    obs = adapter.observe()
    orig_w, orig_h = obs.viewport
    img = Image.open(io.BytesIO(obs.screenshot))
    resized = img.resize((SEND_W, SEND_H))
    buf = io.BytesIO()
    resized.save(buf, format="PNG")
    new_obs = BenchmarkObservation(screenshot=buf.getvalue(), viewport=(SEND_W, SEND_H))
    action = agent.act(new_obs, task)
    raw = (action.raw_action or {}).get("code", "")
    log(f"  Claude: {raw} type={action.type}")
    sx, sy = orig_w / SEND_W, orig_h / SEND_H
    m = re.search(r"click\((\d+),\s*(\d+)\)", raw)
    if m:
        x = int(int(m.group(1)) * sx)
        y = int(int(m.group(2)) * sy)
        click_raw(x, y)
    km = re.search(r"press\('(\w+)'\)", raw)
    if km:
        press_key(km.group(1))
    tm = re.search(r"type\('([^']+)'\)", raw)
    if tm:
        type_text(tm.group(1))
    time.sleep(wait)
    return action.type, raw

def check(question, wait=3):
    result, _ = do(question + " If no action is needed, reply DONE.", wait=wait)
    return result == "done"

def open_opera():
    log("Opening IE with OPERA...")
    subprocess.Popen([r"C:\Program Files\Internet Explorer\iexplore.exe"])
    time.sleep(15)

def login():
    log("Logging into OPERA...")
    do("Click the Login button on the OPERA login screen. Username and password are already filled in.")
    time.sleep(5)

def navigate(button_name):
    log(f"Navigating to {button_name}...")
    do(f"Click the {button_name} button on the OPERA main menu.")
    time.sleep(5)

def wait_and_handle(prompt, max_checks=30, interval=30):
    for i in range(max_checks):
        log(f"  Monitor check {i+1}/{max_checks}")
        is_done = check(prompt, wait=0)
        if is_done:
            at_menu = check("Are you on the OPERA main menu showing PMS, End of Day, SFA buttons, with a [Log off] link in the upper left of the window under Welcome Opera Supervisor? If yes no action needed.")
            if at_menu:
                log("  Back at main menu - clicking Log off")
                do("Click the [Log off] link in the upper left of the OPERA main menu, located under Welcome Opera Supervisor.")
                time.sleep(3)
                return True
            log("  No action needed, waiting...")
        time.sleep(interval)
        if i > 10:
            # Check if Print Final Reports with all Filed - click Close
            check("If you see Print Final Reports with ALL reports showing Filed status, click the Close button. Otherwise no action needed.", wait=5)
            time.sleep(10)
            result, _ = do("Look at the End of Day Routine screen. Do ALL 6 steps have X marks? If yes, click the EXIT button at the BOTTOM of the End of Day Routine window - it is next to Start and Setup buttons. Do NOT click End of Day on the main menu. If not all steps complete, reply DONE.")
            if result != "done":
                log("  End of Day complete, exiting")
                return True
    return False
