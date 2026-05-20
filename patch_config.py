"""
Self-healing config patcher.

Runs from update.bat after `git pull` to bring older config.py files
in line with new defaults from config.example.py.

Idempotent: safe to run repeatedly. Only touches keys that are missing
or have known-stale values. API keys, OPERA_URL, and other
machine-specific values are never overwritten.
"""
import os
import re
import sys
from datetime import datetime

CONFIG_PATH = r"C:\scripts\automations\config.py"
EXAMPLE_PATH = r"C:\scripts\automations\config.example.py"

# Known-stale values that should be auto-upgraded.
# Maps key name -> (old_value_to_replace, new_value, comment)
STALE_VALUES = {
    "LINEAR_TEAM_ID": (
        "1c9cf14c-07e8-4c83-b8d7-1f5cce95d540",  # old PMS Expert team
        "515cee73-1094-4fff-8381-d7eb7cb27f13",  # PMS Gateway team
        "PMS Expert team was retired; tickets now go to PMS Gateway",
    ),
}

# Keys that should exist; if missing, add them.
# Maps key name -> (default_value_literal, comment)
REQUIRED_KEYS = {
    "LINEAR_ASSIGNEE_ID": (
        '"8ee07a71-a684-4c25-846b-0c0df6690892"',  # David Thomson
        "Assign all OPERA night audit tickets to David Thomson",
    ),
    "LOG_RETENTION_DAYS": (
        "7",
        "Days of log history to retain in operaNightAudit.log",
    ),
}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"{ts} patch_config: {msg}")


def patch():
    if not os.path.exists(CONFIG_PATH):
        log(f"config.py not found at {CONFIG_PATH} - skipping patch (fresh install will create it)")
        return 0

    with open(CONFIG_PATH, "r") as f:
        content = f.read()

    original = content
    changes = []

    # Replace stale values
    for key, (old, new, comment) in STALE_VALUES.items():
        # Match: KEY = "old_value"   (with optional whitespace, single or double quotes)
        pattern = re.compile(
            rf'^(\s*{re.escape(key)}\s*=\s*["\']){re.escape(old)}(["\'])',
            re.MULTILINE,
        )
        if pattern.search(content):
            content = pattern.sub(rf'\g<1>{new}\g<2>', content)
            changes.append(f"  Updated {key}: {old} -> {new} ({comment})")

    # Add missing required keys
    for key, (default_literal, comment) in REQUIRED_KEYS.items():
        # Check if key is already defined (matches KEY = ... at start of line)
        key_pattern = re.compile(rf'^\s*{re.escape(key)}\s*=', re.MULTILINE)
        if not key_pattern.search(content):
            # Append at end of file
            if not content.endswith("\n"):
                content += "\n"
            content += f"\n# {comment} (auto-added by patch_config.py)\n"
            content += f"{key} = {default_literal}\n"
            changes.append(f"  Added missing key {key} = {default_literal}")

    if not changes:
        log("config.py is up to date - no changes needed")
        return 0

    # Back up the old file before writing
    backup_path = CONFIG_PATH + ".bak"
    with open(backup_path, "w") as f:
        f.write(original)

    with open(CONFIG_PATH, "w") as f:
        f.write(content)

    log(f"Patched config.py ({len(changes)} change(s)):")
    for c in changes:
        log(c)
    log(f"Backup saved to {backup_path}")
    return 0


if __name__ == "__main__":
    sys.exit(patch())
