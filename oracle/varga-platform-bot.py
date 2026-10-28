#!/usr/bin/env python3
"""Dedicated health monitor and bounded recovery for Varga Cantieri/Gestionale only."""
from __future__ import annotations

import datetime as dt
import json
import os
import pathlib
import socket
import subprocess
import time
import urllib.error
import urllib.request

STATE_DIR = pathlib.Path(os.environ.get("VARGA_BOT_STATE", "/var/lib/varga-platform-bot"))
STATUS_FILE = STATE_DIR / "status.json"
STATE_FILE = STATE_DIR / "state.json"
AUDIT_FILE = STATE_DIR / "actions.jsonl"

# Explicit allowlist: application web/API containers only. Never add DB, shadow,
# backup, radio, or unrelated Oracle containers here.
PLATFORMS = {
    "cantieri": {
        "label": "Varga Cantieri",
        "services": {
            "web": {"container": "varga-cantieri-web", "kind": "http", "url": "http://127.0.0.1:18081/"},
            "api": {"container": "varga-cantieri-api", "kind": "tcp", "host": "127.0.0.1", "port": 18082},
        },
        "dependencies": {},
    },
    "gestionale": {
        "label": "Varga Gestionale",
        "services": {
            "web": {"container": "varga-gestionale-oracle-varga-gestionale-web-1", "kind": "http", "url": "http://127.0.0.1:18086/"},
            "api": {"container": "vg-gestionale-oracle-api-1", "kind": "tcp", "host": "127.0.0.1", "port": 18098},
        },
        "dependencies": {"api": "vg-gestionale-oracle-db-1"},
    },
}
FAILURES_BEFORE_RESTART = 2
RESTART_COOLDOWN_SECONDS = 1800
MAX_RESTARTS_24H = 3


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime | None = None) -> str:
    return (value or now()).isoformat(timespec="seconds")


def command(args: list[str], timeout: int = 12) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def container_state(name: str) -> dict:
    result = command(["/usr/bin/docker", "inspect", "--format",
                      "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}",
                      name])
    if result.returncode:
        return {"exists": False, "state": "missing", "health": "unknown"}
    parts = result.stdout.strip().split("|", 1)
    return {"exists": True, "state": parts[0], "health": parts[1] if len(parts) > 1 else "unknown"}


def probe(service: dict) -> dict:
    try:
        if service["kind"] == "http":
            req = urllib.request.Request(service["url"], headers={"User-Agent": "VargaPlatformBot/1.0"})
            try:
                with urllib.request.urlopen(req, timeout=8) as response:
                    code = response.status
            except urllib.error.HTTPError as exc:
                code = exc.code
            return {"kind": "http", "http": code, "reachable": 200 <= code < 400,
                    "target": service["url"]}
        with socket.create_connection((service["host"], service["port"]), timeout=5):
            return {"kind": "tcp", "reachable": True,
                    "target": f'{service["host"]}:{service["port"]}'}
    except Exception as exc:
        return {"kind": service["kind"], "reachable": False,
                "error_type": type(exc).__name__,
                "target": service.get("url", f'{service.get("host")}:{service.get("port")}')}


def dependency_ok(name: str | None) -> bool:
    if not name:
        return True
    state = container_state(name)
    return state["exists"] and state["state"] == "running" and state["health"] in ("healthy", "not-configured")


def check_service(service: dict) -> dict:
    container = container_state(service["container"])
    network = probe(service)
    container_ok = (container["exists"] and container["state"] == "running"
                    and container["health"] not in ("unhealthy",))
    healthy = container_ok and network["reachable"]
    return {
        "state": "ok" if healthy else "degraded",
        "container": service["container"],
        "container_state": container["state"],
        "container_health": container["health"],
        "probe": network,
    }


def read_state() -> dict:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_json(path: pathlib.Path, data: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def record_action(event: dict) -> None:
    with AUDIT_FILE.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False) + "\n")


def restart_allowed(state: dict, key: str) -> tuple[bool, str]:
    actions = [x for x in state.get("restarts", {}).get(key, [])
               if now().timestamp() - float(x) < 86400]
    state.setdefault("restarts", {})[key] = actions
    if len(actions) >= MAX_RESTARTS_24H:
        return False, "limite di 3 riavvii nelle ultime 24 ore raggiunto"
    if actions and now().timestamp() - float(actions[-1]) < RESTART_COOLDOWN_SECONDS:
        return False, "intervallo minimo di 30 minuti non ancora trascorso"
    return True, ""


def inspect_all(repair: bool) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = read_state()
    state.setdefault("failures", {})
    state.setdefault("restarts", {})
    report = {
        "schema_version": 1,
        "checked_at": iso(),
        "scope": ["Varga Cantieri", "Varga Gestionale"],
        "overall": "ok",
        "platforms": {},
        "actions": [],
        "safety": {
            "restart_allowlist": sorted(
                svc["container"] for platform in PLATFORMS.values()
                for svc in platform["services"].values()),
            "databases_restarted": False,
            "backup_containers_touched": False,
            "other_platforms_touched": False,
            "failures_before_restart": FAILURES_BEFORE_RESTART,
            "max_restarts_per_container_24h": MAX_RESTARTS_24H,
        },
    }
    for platform_key, platform in PLATFORMS.items():
        services_out = {}
        for service_key, service in platform["services"].items():
            key = f"{platform_key}.{service_key}"
            result = check_service(service)
            dependency = platform["dependencies"].get(service_key)
            result["dependency_ok"] = dependency_ok(dependency)
            old_streak = int(state["failures"].get(key, 0))
            state["failures"][key] = old_streak + 1 if result["state"] != "ok" else 0
            streak = state["failures"][key]
            result["failure_streak"] = streak

            if repair and result["state"] != "ok" and streak >= FAILURES_BEFORE_RESTART:
                allowed, reason = restart_allowed(state, key)
                # Do not restart an API when its known database dependency is unhealthy.
                if not result["dependency_ok"]:
                    allowed, reason = False, "dipendenza database non sana; riavvio API sospeso"
                if not result["container_state"] == "missing" and allowed:
                    started = iso()
                    action = command(["/usr/bin/docker", "restart", "--time", "10",
                                      service["container"]], timeout=35)
                    item = {
                        "at": started,
                        "platform": platform["label"],
                        "service": service_key,
                        "container": service["container"],
                        "action": "docker restart",
                        "result": "requested" if action.returncode == 0 else "failed",
                    }
                    if action.returncode != 0:
                        item["error"] = (action.stderr or "docker restart failed").strip()[:240]
                    else:
                        state["restarts"].setdefault(key, []).append(now().timestamp())
                        # Re-check after the container has had a short time to come up.
                        for _ in range(5):
                            time.sleep(2)
                            result = check_service(service)
                            if result["state"] == "ok":
                                break
                        item["verification"] = result["state"]
                    record_action(item)
                    report["actions"].append(item)
                    result["failure_streak"] = 0 if result["state"] == "ok" else streak
                    state["failures"][key] = result["failure_streak"]
                elif result["container_state"] != "missing":
                    report["actions"].append({
                        "at": iso(), "platform": platform["label"], "service": service_key,
                        "container": service["container"], "action": "restart skipped",
                        "reason": reason,
                    })
            services_out[service_key] = result
            if result["state"] != "ok":
                report["overall"] = "degraded"
        report["platforms"][platform_key] = {
            "label": platform["label"],
            "state": "ok" if all(s["state"] == "ok" for s in services_out.values()) else "degraded",
            "services": services_out,
        }
    save_json(STATE_FILE, state)
    save_json(STATUS_FILE, report)
    return report


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true", help="allowlisted web/API restart after repeated failures")
    parser.add_argument("--once", action="store_true", help="read-only status check")
    args = parser.parse_args()
    print(json.dumps(inspect_all(repair=args.repair), ensure_ascii=False, indent=2))
