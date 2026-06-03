"""
Diagnostic: verify the configured Linear API key, team, and assignee.

Run on a Windows machine where ticket creation is failing:
    python C:\\scripts\\automations\\verify_linear.py

Output tells you:
  - Which user the API key belongs to (and which workspace)
  - Whether the configured LINEAR_TEAM_ID exists in that workspace
  - Whether the configured LINEAR_ASSIGNEE_ID exists in that workspace
  - A list of PMS-related teams the key CAN see (so you can pick a working one)
"""
import json
import sys
import urllib.request

try:
    import config
except ImportError:
    print("ERROR: config.py not found")
    sys.exit(1)

API = "https://api.linear.app/graphql"


def gql(query):
    api_key = getattr(config, "LINEAR_API_KEY", "")
    if not api_key or api_key.startswith("lin_api_YOUR"):
        print("ERROR: LINEAR_API_KEY not set in config.py")
        sys.exit(1)
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query}).encode(),
        headers={"Content-Type": "application/json", "Authorization": api_key},
    )
    return json.loads(urllib.request.urlopen(req, timeout=15).read())


def main():
    print("=" * 60)
    print("Linear API Diagnostic")
    print("=" * 60)
    print()

    # 1. Who is the API key?
    print("1. Identifying the API key holder...")
    r = gql("{ viewer { id name email organization { name urlKey } } }")
    v = r["data"]["viewer"]
    print(f"   User:         {v['name']} <{v['email']}>")
    print(f"   User ID:      {v['id']}")
    print(f"   Workspace:    {v['organization']['name']} ({v['organization']['urlKey']})")
    print()

    # 2. Configured team
    team_id = getattr(config, "LINEAR_TEAM_ID", "")
    print(f"2. Checking configured LINEAR_TEAM_ID ({team_id})...")
    r = gql(f'{{ team(id: "{team_id}") {{ id key name archivedAt }} }}')
    team = r.get("data", {}).get("team")
    if team:
        archived = " (ARCHIVED)" if team["archivedAt"] else ""
        print(f"   FOUND: {team['key']} - {team['name']}{archived}")
    else:
        print("   NOT FOUND - this team does not exist in this workspace")
        if r.get("errors"):
            print(f"   Linear errors: {r['errors']}")
    print()

    # 3. Configured assignee
    assignee_id = getattr(config, "LINEAR_ASSIGNEE_ID", None)
    if assignee_id:
        print(f"3. Checking configured LINEAR_ASSIGNEE_ID ({assignee_id})...")
        r = gql(f'{{ user(id: "{assignee_id}") {{ id name email active }} }}')
        u = r.get("data", {}).get("user")
        if u:
            active = "active" if u["active"] else "INACTIVE"
            print(f"   FOUND: {u['name']} <{u['email']}> ({active})")
        else:
            print("   NOT FOUND - this user does not exist in this workspace")
        print()
    else:
        print("3. No LINEAR_ASSIGNEE_ID configured (tickets will be unassigned)")
        print()

    # 4. List PMS-related teams visible to this key
    print("4. PMS-related teams visible to this API key:")
    r = gql("{ teams(first: 100) { nodes { id key name archivedAt } } }")
    nodes = r.get("data", {}).get("teams", {}).get("nodes", []) or []
    pms = [t for t in nodes if "PMS" in (t.get("key") or "") or "pms" in (t.get("name") or "").lower()]
    if pms:
        for t in pms:
            archived = " (ARCHIVED)" if t["archivedAt"] else ""
            marker = "  <- currently configured" if t["id"] == team_id else ""
            print(f"   {t['key']:8s} {t['name']:30s} {t['id']}{archived}{marker}")
    else:
        print("   None - this key may be in a workspace without PMS teams")
    print()

    print("=" * 60)
    print("If the configured team was NOT FOUND but other PMS teams are listed,")
    print("update LINEAR_TEAM_ID in config.py to one of the IDs above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
