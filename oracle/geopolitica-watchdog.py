#!/usr/bin/env python3
"""RDI Oracle watchdog: trigger GitHub geopolitica only when its published feed is stale."""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

OWNER = "ionut290"
REPO = "Radio-Romanii-Italia"
WORKFLOW = "geopolitica.yml"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
FEED = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main/data/geopolitica-news.json"
STATE = pathlib.Path(os.getenv("RDI_WATCHDOG_STATE", "/var/lib/rdi-geopolitica-watchdog/last_dispatch"))
STALE_SECONDS = 60 * 60
COOLDOWN_SECONDS = 40 * 60

def request(url, token=None, method="GET", payload=None):
    headers = {"User-Agent": "RDI-Geopolitica-Oracle-Watchdog/1", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer " + token
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    data = json.dumps(payload).encode() if payload is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=20) as r:
        return json.loads(r.read()) if r.status != 204 else {}

def main():
    now = time.time()
    feed = request(FEED + "?t=" + str(int(now)))
    updated = dt.datetime.fromisoformat(feed["updated_at"].replace("Z", "+00:00"))
    age = now - updated.timestamp()
    if age < -300:
        raise RuntimeError("Future feed timestamp, refusing dispatch")
    print(f"Geopolitica feed age: {max(age,0)/60:.1f} minutes", flush=True)
    if age <= STALE_SECONDS:
        print("OK: no action required")
        return
    token = os.environ.get("RDI_GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("Stale feed, but RDI_GITHUB_TOKEN not configured")
    try:
        last = float(STATE.read_text().strip())
    except (OSError, ValueError):
        last = 0
    if now - last < COOLDOWN_SECONDS:
        print("Recovery already attempted recently; cooldown")
        return
    for status in ("in_progress", "queued", "waiting", "pending", "requested"):
        data = request(API + f"/actions/workflows/{WORKFLOW}/runs?status={status}&per_page=10", token)
        if data.get("total_count", 0):
            print(f"Workflow already {status}; no duplicate dispatch")
            return
    # Persist attempt before dispatch so API response loss cannot cause repeated triggers.
    STATE.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    STATE.write_text(str(now))
    os.chmod(STATE, 0o600)
    request(API + f"/actions/workflows/{WORKFLOW}/dispatches", token, "POST", {"ref": "main"})
    print("Recovery dispatch accepted by GitHub (HTTP 204)")

if __name__ == "__main__":
    try:
        main()
    except (KeyError, ValueError, urllib.error.URLError, RuntimeError) as exc:
        print(f"Watchdog error: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
