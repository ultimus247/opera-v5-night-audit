"""
Alert script: Creates an urgent Linear ticket when OPERA server is down.
Posts to the PMS Expert team.

Reads LINEAR_API_KEY and team settings from config.py.
"""
import os
import sys
import socket
import json
import time
import urllib.request

# Load config
try:
    import config
except ImportError:
    print("ERROR: config.py not found")
    sys.exit(1)

LINEAR_API_URL = "https://api.linear.app/graphql"


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} ALERT: {msg}"
    print(line)
    try:
        with open(config.LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def create_linear_ticket():
    api_key = getattr(config, "LINEAR_API_KEY", "") or os.environ.get("LINEAR_API_KEY", "")
    if not api_key or api_key.startswith("lin_api_YOUR"):
        log("LINEAR_API_KEY not set in config.py - cannot create ticket")
        return False

    hostname = getattr(config, "HOSTNAME_OVERRIDE", None) or socket.gethostname()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")

    title = f"URGENT: OPERA is DOWN on {hostname}"
    description = (
        f"**OPERA PMS server is unreachable on {hostname}**\n\n"
        f"- **Hostname:** {hostname}\n"
        f"- **Detected at:** {timestamp}\n"
        f"- **Source:** Automated night audit script\n\n"
        f"The night audit script attempted to open the OPERA login page in IE "
        f"and could not detect the login screen after multiple retries. This indicates "
        f"the OPERA server is down or unreachable from this machine.\n\n"
        f"**Action required:** Investigate OPERA server status on `{hostname}` and "
        f"manually run the night audit if needed before the next business day rolls."
    )

    mutation = """
    mutation IssueCreate($input: IssueCreateInput!) {
        issueCreate(input: $input) {
            success
            issue { id identifier url }
        }
    }
    """
    variables = {
        "input": {
            "teamId": config.LINEAR_TEAM_ID,
            "title": title,
            "description": description,
            "priority": config.LINEAR_PRIORITY_URGENT,
        }
    }

    payload = json.dumps({"query": mutation, "variables": variables}).encode()
    req = urllib.request.Request(
        LINEAR_API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            if "errors" in data:
                log(f"Linear API error: {data['errors']}")
                return False
            issue = data.get("data", {}).get("issueCreate", {}).get("issue", {})
            if issue:
                log(f"Created Linear ticket: {issue.get('identifier')} - {issue.get('url')}")
                return True
            log(f"Linear API returned no issue: {data}")
            return False
    except Exception as e:
        log(f"Failed to create Linear ticket: {e}")
        return False


if __name__ == "__main__":
    log("OPERA server is down - creating urgent Linear ticket")
    success = create_linear_ticket()
    sys.exit(0 if success else 1)
