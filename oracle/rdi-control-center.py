#!/usr/bin/env python3
"""RDI control center: guarded local service monitoring for Oracle.

Default is read-only. --repair restarts only allowlisted failed services,
with cooldown and bounded restart attempts. No station or playlist edits.
"""
import argparse
import datetime as dt
import json
import pathlib
import subprocess
import time
import urllib.request

STATION_API = 'https://radio-romanii-italia.duckdns.org/api/nowplaying/1'

SERVICES = ("radio-youtube-visual.service",)
STATE = pathlib.Path("/var/lib/rdi-control-center/restarts.json")
COOLDOWN = 3600
MAX_RESTARTS_24H = 3

def systemctl(*args):
    return subprocess.run(["systemctl", *args], capture_output=True, text=True, timeout=15)

def probe_station():
    try:
        request = urllib.request.Request(STATION_API, headers={"User-Agent": "RDI-Control-Center/1.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            data = json.load(response)
        return {
            "api": "ok",
            "station_is_online": data.get("is_online") if isinstance(data.get("is_online"), bool) else None,
            "listeners_current": (data.get("listeners") or {}).get("current"),
            "note": "API only, not proof of audible stream",
        }
    except (OSError, ValueError, TypeError) as exc:
        return {"api": "error", "error_type": type(exc).__name__}


def probe_encoder():
    try:
        process = subprocess.run(["pgrep", "-x", "ffmpeg"], capture_output=True, text=True, timeout=5)
        pids = [pid for pid in process.stdout.splitlines() if pid.isdigit()]
        return {"ffmpeg_running": bool(pids), "ffmpeg_process_count": len(pids)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ffmpeg_running": None, "error_type": type(exc).__name__}


def inspect(repair=False):
    now = time.time()
    try:
        history = json.loads(STATE.read_text())
        if not isinstance(history, dict):
            history = {}
    except (OSError, ValueError):
        history = {}
    report = []
    for service in SERVICES:
        unit = systemctl("show", service, "--property=LoadState,ActiveState,SubState", "--no-pager")
        fields = dict(line.split("=", 1) for line in unit.stdout.splitlines() if "=" in line)
        active = fields.get("ActiveState", "unknown")
        load = fields.get("LoadState", "unknown")
        result = {"service": service, "load": load, "state": active, "action": "none"}
        recent = [t for t in history.get(service, []) if isinstance(t, (int, float)) and 0 <= now - t < 86400]
        if load == "loaded" and active == "failed":
            if not repair:
                result["action"] = "restart_available"
            elif len(recent) >= MAX_RESTARTS_24H or (recent and now - recent[-1] < COOLDOWN):
                result["action"] = "restart_blocked_cooldown"
            else:
                # Save before attempting to prevent restart storms after a crash.
                history[service] = recent + [now]
                STATE.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
                STATE.write_text(json.dumps(history))
                STATE.chmod(0o600)
                restarted = systemctl("restart", service)
                result["action"] = "restart_attempted" if restarted.returncode == 0 else "restart_failed"
        report.append(result)
    return {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(), "services": report, "azuracast": probe_station(), "encoder": probe_encoder()}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true")
    args = parser.parse_args()
    print(json.dumps(inspect(args.repair), indent=2))
