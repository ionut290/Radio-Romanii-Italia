#!/usr/bin/env python3
"""Oracle fallback for RDI's daily thought publication."""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import time
import urllib.error
import urllib.request
from zoneinfo import ZoneInfo

OWNER = "ionut290"
REPO = "Radio-Romanii-Italia"
WORKFLOW = "daily-thought.yml"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
FEED = "https://radioromanii.duckdns.org/data/calendario-filosofico-oggi.json"
ROME = ZoneInfo("Europe/Rome")
STATE = Path(os.getenv("RDI_DAILY_THOUGHT_WATCHDOG_STATE", "/var/lib/rdi-daily-thought-watchdog/last_dispatch"))
TOKEN_FILE = Path(os.getenv("RDI_GITHUB_TOKEN_FILE", "/home/ubuntu/rdi-monitor/github-token"))
COOLDOWN_SECONDS = 45 * 60


def request(url: str, token: str | None = None, method: str = "GET", payload: dict | None = None) -> dict:
    headers = {"User-Agent": "RDI-Daily-Thought-Oracle-Watchdog/1", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer " + token
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    data = json.dumps(payload).encode() if payload else None
    if data:
        headers["Content-Type"] = "application/json"
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers, method=method), timeout=20) as response:
        return json.loads(response.read()) if response.status != 204 else {}


def recently_dispatched(now: float) -> bool:
    try:
        return now - float(STATE.read_text(encoding="utf-8").strip()) < COOLDOWN_SECONDS
    except (OSError, ValueError):
        return False


def main() -> None:
    now = time.time()
    local_now = dt.datetime.now(ROME)
    if local_now.hour < 1:
        print("Before 01:00 Europe/Rome: no check required")
        return
    expected = local_now.date().isoformat()
    feed = request(FEED + "?watch=" + str(int(now)))
    if feed.get("date") == expected and feed.get("status") == "published" and str(feed.get("quote", "")).strip():
        print(f"OK: daily thought {expected}")
        return
    print(f"Daily thought missing or invalid: expected={expected}, got={feed.get('date')!r}")
    if recently_dispatched(now):
        print("Recovery already requested recently; cooldown active")
        return
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise RuntimeError("The existing Oracle GitHub token is empty")
    for status in ("in_progress", "queued", "waiting", "pending", "requested"):
        if request(API + f"/actions/workflows/{WORKFLOW}/runs?status={status}&per_page=10", token).get("total_count", 0):
            print(f"Daily thought workflow already {status}; no duplicate dispatch")
            return
    STATE.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    STATE.write_text(str(now), encoding="utf-8")
    os.chmod(STATE, 0o600)
    request(API + f"/actions/workflows/{WORKFLOW}/dispatches", token, "POST", {"ref": "main"})
    print("Recovery dispatch accepted by GitHub")


if __name__ == "__main__":
    try:
        main()
    except (OSError, KeyError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"Watchdog error: {type(exc).__name__}: {exc}")
        raise SystemExit(1)
