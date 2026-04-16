"""
Alert helpers: creates urgent Linear tickets for the PMS Expert team.

When run directly (via alertOperaisDown.bat), files an "OPERA is DOWN" ticket.
Also exposes create_ticket(title, description) so night_audit.py can file
tickets for other failure modes (phase timeouts, unexpected screens, etc).

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


def get_hostname():
    return getattr(config, "HOSTNAME_OVERRIDE", None) or socket.gethostname()


def create_ticket(title, description, priority=None):
    """Create a Linear ticket on the PMS Expert team.

    Returns the created issue dict on success, or None on failure.
    """
    api_key = getattr(config, "LINEAR_API_KEY", "") or os.environ.get("LINEAR_API_KEY", "")
    if not api_key or api_key.startswith("lin_api_YOUR"):
        log("LINEAR_API_KEY not set in config.py - cannot create ticket")
        return None

    if priority is None:
        priority = config.LINEAR_PRIORITY_URGENT

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
            "priority": priority,
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
                return None
            issue = data.get("data", {}).get("issueCreate", {}).get("issue", {})
            if issue:
                log(f"Created Linear ticket: {issue.get('identifier')} - {issue.get('url')}")
                return issue
            log(f"Linear API returned no issue: {data}")
            return None
    except Exception as e:
        log(f"Failed to create Linear ticket: {e}")
        return None


def alert_phase_failure(phase_name, reason):
    """File a ticket when a night audit phase fails to reach its expected state."""
    hostname = get_hostname()
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    title = f"URGENT: Night audit failed at {phase_name} on {hostname}"
    description = (
        f"**Night audit script could not complete {phase_name} on {hostname}**\n\n"
        f"- **Hostname:** {hostname}\n"
        f"- **Phase:** {phase_name}\n"
        f"- **Detected at:** {timestamp}\n"
        f"- **Reason:** {reason}\n"
        f"- **Source:** Automated night audit script\n\n"
        f"The script aborted after being unable to reach the expected screen "
        f"during this phase. OPERA may be in an unexpected state, or the UI may "
        f"have changed.\n\n"
        f"**Action required:** Investigate the OPERA state on `{hostname}`, "
        f"manually complete the night audit if needed, and review the logs at "
        f"`C:\\scripts\\automations\\operaNightAudit.log` before the next scheduled run."
    )
    return create_ticket(title, description)


def alert_opera_down():
    """File a ticket when OPERA fails to load at Phase 0."""
    hostname = get_hostname()
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
    return create_ticket(title, description)


# Back-compat alias for any external callers that still use the old name
def create_linear_ticket():
    return alert_opera_down()


if __name__ == "__main__":
    log("OPERA server is down - creating urgent Linear ticket")
    success = alert_opera_down()
    sys.exit(0 if success else 1)
