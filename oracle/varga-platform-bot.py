#!/usr/bin/env python3
"""Dedicated monitor and bounded recovery for Varga Cantieri/Gestionale only."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request

STATE_DIR = pathlib.Path(os.environ.get("VARGA_BOT_STATE", "/var/lib/varga-platform-bot"))
STATUS_FILE = STATE_DIR / "status.json"
STATE_FILE = STATE_DIR / "state.json"
AUDIT_FILE = STATE_DIR / "actions.jsonl"

# Explicit restart allowlist. Databases, shadow/replica and backup containers
# are monitored only and can never be restarted by this bot.
PLATFORMS = {
    "cantieri": {
        "label": "Varga Cantieri",
        "database": {
            "container": "db-postgres-1",
            "user": "varga",
            "database": "varga_cantieri",
        },
        "services": {
            "web": {
                "container": "varga-cantieri-web",
                "kind": "http",
                "url": "http://127.0.0.1:18081/",
                "expected_status": "2xx_or_3xx",
                "restart_on_http_5xx": False,
            },
            "api": {
                "container": "varga-cantieri-api",
                "kind": "http_any",
                "url": "http://127.0.0.1:18082/",
                "expected_status": "any_http_response_below_500",
                "note": "API senza route salute dedicata: controllata risposta HTTP e database separatamente",
                "restart_on_http_5xx": True,
            },
        },
    },
    "gestionale": {
        "label": "Varga Gestionale",
        "database": {
            "container": "vg-gestionale-oracle-db-1",
            "user": "varga_gestionale",
            "database": "varga_gestionale",
        },
        "services": {
            "web": {
                "container": "varga-gestionale-oracle-varga-gestionale-web-1",
                "kind": "http",
                "url": "http://127.0.0.1:18086/",
                "expected_status": "2xx_or_3xx",
                "restart_on_http_5xx": False,
            },
            "api": {
                "container": "vg-gestionale-oracle-api-1",
                "kind": "http_json",
                "url": "http://127.0.0.1:18098/api/gestionale/v1/health",
                "json_key": "ready",
                "json_expected": True,
                "expected_status": "HTTP 2xx and JSON ready=true",
                "note": "Endpoint ufficiale: verifica connessione API e query SELECT 1 sul database",
                "restart_on_http_5xx": True,
            },
        },
    },
}

RESTART_ALLOWLIST = frozenset(
    service["container"]
    for platform in PLATFORMS.values()
    for service in platform["services"].values()
)
FAILURES_BEFORE_RESTART = 2
RESTART_COOLDOWN_SECONDS = 1800
MAX_RESTARTS_24H = 3
DB_PROBE_TIMEOUT = 10


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def iso(value: dt.datetime | None = None) -> str:
    return (value or now()).isoformat(timespec="seconds")


def command(args: list[str], timeout: int = 12) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def container_state(name: str) -> dict:
    result = command([
        "/usr/bin/docker", "inspect", "--format",
        "{{.State.Status}}|{{if .State.Health}}{{.State.Health.Status}}{{else}}not-configured{{end}}|{{.RestartCount}}|{{.State.StartedAt}}",
        name,
    ])
    if result.returncode:
        return {"exists": False, "state": "missing", "health": "unknown",
                "restart_count": None, "started_at": None}
    parts = result.stdout.strip().split("|", 3)
    try:
        restart_count = int(parts[2])
    except (IndexError, ValueError):
        restart_count = None
    return {
        "exists": True,
        "state": parts[0],
        "health": parts[1] if len(parts) > 1 else "unknown",
        "restart_count": restart_count,
        "started_at": parts[3] if len(parts) > 3 else None,
    }


def probe(service: dict) -> dict:
    started = time.monotonic()
    try:
        kind = service["kind"]
        if kind in ("http", "http_any", "http_json"):
            req = urllib.request.Request(
                service["url"],
                headers={"User-Agent": "VargaPlatformBot/2.0", "Accept": "application/json,*/*"},
            )
            body = b""
            try:
                with urllib.request.urlopen(req, timeout=8) as response:
                    code = response.status
                    if kind == "http_json":
                        body = response.read(8192)
            except urllib.error.HTTPError as exc:
                code = exc.code
                if kind == "http_json":
                    body = exc.read(8192)
            elapsed = round((time.monotonic() - started) * 1000)
            if kind == "http":
                reachable = 200 <= code < 400
            elif kind == "http_any":
                reachable = 200 <= code < 500
            else:
                reachable = 200 <= code < 300
            result = {
                "kind": kind,
                "http": code,
                "reachable": reachable,
                "target": service["url"],
                "response_ms": elapsed,
                "expected": service.get("expected_status"),
            }
            if kind == "http_json":
                try:
                    payload = json.loads(body.decode("utf-8"))
                    ready = payload.get(service["json_key"]) is service["json_expected"]
                except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                    ready = False
                result["application_ready"] = ready
                result["reachable"] = reachable and ready
            if service.get("note"):
                result["note"] = service["note"]
            return result

        with socket.create_connection((service["host"], service["port"]), timeout=5):
            elapsed = round((time.monotonic() - started) * 1000)
            return {
                "kind": "tcp",
                "reachable": True,
                "target": f'{service["host"]}:{service["port"]}',
                "response_ms": elapsed,
            }
    except Exception as exc:
        return {
            "kind": service["kind"],
            "reachable": False,
            "error_type": type(exc).__name__,
            "target": service.get("url", f'{service.get("host")}:{service.get("port")}'),
            "response_ms": round((time.monotonic() - started) * 1000),
            "expected": service.get("expected_status"),
            **({"note": service["note"]} if service.get("note") else {}),
        }


def check_database(config: dict) -> dict:
    name = config["container"]
    container = container_state(name)
    probe_result = {"kind": "postgres_readiness"}
    if container["exists"] and container["state"] == "running":
        result = command([
            "/usr/bin/docker", "exec", name, "pg_isready",
            "-U", config["user"], "-d", config["database"],
        ], timeout=DB_PROBE_TIMEOUT)
        probe_result.update({
            "reachable": result.returncode == 0,
            "result": "accepting_connections" if result.returncode == 0 else "not_ready",
        })
    else:
        probe_result.update({"reachable": False, "result": "container_not_running"})
    healthy = (
        container["exists"]
        and container["state"] == "running"
        and container["health"] == "healthy"
        and probe_result["reachable"]
    )
    return {
        "state": "ok" if healthy else "degraded",
        "container": name,
        "container_state": container["state"],
        "container_health": container["health"],
        "restart_count": container["restart_count"],
        "started_at": container["started_at"],
        "probe": probe_result,
        "automatic_restart": False,
    }


def host_metrics() -> dict:
    result = {"state": "ok"}
    try:
        usage = shutil.disk_usage("/")
        result["disk_percent"] = round(usage.used * 100 / usage.total, 1)
        result["disk_free_bytes"] = usage.free
    except OSError:
        result["disk_percent"] = None
    try:
        memory = {}
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            memory[key] = int(value.strip().split()[0])
        total = memory["MemTotal"]
        available = memory["MemAvailable"]
        result["memory_percent"] = round((total - available) * 100 / total, 1)
    except (OSError, KeyError, ValueError):
        result["memory_percent"] = None
    try:
        result["load_average"] = [round(float(x), 2) for x in pathlib.Path("/proc/loadavg").read_text().split()[:3]]
    except (OSError, ValueError):
        result["load_average"] = None
    if (result.get("disk_percent") is not None and result["disk_percent"] >= 90) or (
        result.get("memory_percent") is not None and result["memory_percent"] >= 92
    ):
        result["state"] = "warning"
    return result


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


def status_transition(state: dict, key: str, label: str, current: str, report: dict) -> None:
    previous = state.setdefault("service_states", {}).get(key)
    if previous in ("ok", "degraded", "warning") and previous != current:
        event = {
            "at": iso(),
            "kind": "status_transition",
            "target": label,
            "from": previous,
            "to": current,
        }
        record_action(event)
        report["actions"].append(event)
    state["service_states"][key] = current


def restart_allowed(state: dict, key: str) -> tuple[bool, str]:
    actions = [x for x in state.get("restarts", {}).get(key, [])
               if now().timestamp() - float(x) < 86400]
    state.setdefault("restarts", {})[key] = actions
    if len(actions) >= MAX_RESTARTS_24H:
        return False, "limite di 3 riavvii nelle ultime 24 ore raggiunto"
    if actions and now().timestamp() - float(actions[-1]) < RESTART_COOLDOWN_SECONDS:
        return False, "intervallo minimo di 30 minuti non ancora trascorso"
    return True, ""


def restart_signal(result: dict, service: dict) -> bool:
    if result["container_state"] != "running" or result["container_health"] == "unhealthy":
        return True
    if result["probe"].get("error_type"):
        return True
    code = result["probe"].get("http")
    return bool(service.get("restart_on_http_5xx") and code is not None and code >= 500)


def check_service(service: dict) -> dict:
    container = container_state(service["container"])
    network = probe(service)
    container_ok = (
        container["exists"]
        and container["state"] == "running"
        and container["health"] not in ("unhealthy",)
    )
    healthy = container_ok and network["reachable"]
    return {
        "state": "ok" if healthy else "degraded",
        "container": service["container"],
        "container_state": container["state"],
        "container_health": container["health"],
        "restart_count": container["restart_count"],
        "started_at": container["started_at"],
        "probe": network,
    }


def inspect_all(repair: bool) -> dict:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state = read_state()
    state.setdefault("failures", {})
    state.setdefault("restarts", {})
    report = {
        "schema_version": 2,
        "checked_at": iso(),
        "scope": ["Varga Cantieri", "Varga Gestionale"],
        "overall": "ok",
        "host": host_metrics(),
        "platforms": {},
        "actions": [],
        "safety": {
            "restart_allowlist": sorted(RESTART_ALLOWLIST),
            "database_restart": False,
            "backup_containers_touched": False,
            "shadow_container_touched": False,
            "other_platforms_touched": False,
            "failures_before_restart": FAILURES_BEFORE_RESTART,
            "restart_cooldown_minutes": RESTART_COOLDOWN_SECONDS // 60,
            "max_restarts_per_container_24h": MAX_RESTARTS_24H,
        },
    }
    if report["host"]["state"] != "ok":
        report["overall"] = "degraded"

    for platform_key, platform in PLATFORMS.items():
        db_result = check_database(platform["database"])
        status_transition(
            state, f"{platform_key}.database",
            f'{platform["label"]} · database', db_result["state"], report,
        )
        services_out = {}
        for service_key, service in platform["services"].items():
            key = f"{platform_key}.{service_key}"
            result = check_service(service)
            dependency_ok = (
                db_result["state"] == "ok"
                if service_key in ("api",) else True
            )
            result["dependency_ok"] = dependency_ok
            if not dependency_ok:
                result["state"] = "degraded"
                result["dependency_note"] = "Database non pronto: riavvio API sospeso"
            old_streak = int(state["failures"].get(key, 0))
            state["failures"][key] = old_streak + 1 if result["state"] != "ok" else 0
            streak = state["failures"][key]
            result["failure_streak"] = streak

            if (
                repair
                and service["container"] in RESTART_ALLOWLIST
                and result["state"] != "ok"
                and streak >= FAILURES_BEFORE_RESTART
            ):
                allowed, reason = restart_allowed(state, key)
                if not dependency_ok:
                    allowed, reason = False, "dipendenza database non sana; riavvio API sospeso"
                elif not restart_signal(result, service):
                    allowed, reason = False, "risposta HTTP applicativa: nessun riavvio automatico del web"
                if result["container_state"] != "missing" and allowed:
                    started = iso()
                    action = command(
                        ["/usr/bin/docker", "restart", "--time", "10", service["container"]],
                        timeout=35,
                    )
                    item = {
                        "at": started,
                        "kind": "automatic_recovery",
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
                        for _ in range(6):
                            time.sleep(2)
                            result = check_service(service)
                            result["dependency_ok"] = dependency_ok
                            if result["state"] == "ok":
                                break
                        item["verification"] = result["state"]
                    record_action(item)
                    report["actions"].append(item)
                    result["failure_streak"] = 0 if result["state"] == "ok" else streak
                    state["failures"][key] = result["failure_streak"]
                elif result["container_state"] != "missing":
                    report["actions"].append({
                        "at": iso(),
                        "kind": "recovery_guard",
                        "platform": platform["label"],
                        "service": service_key,
                        "action": "restart skipped",
                        "reason": reason,
                    })

            status_transition(state, key, f'{platform["label"]} · {service_key}', result["state"], report)
            services_out[service_key] = result
            if result["state"] != "ok":
                report["overall"] = "degraded"

        if db_result["state"] != "ok":
            report["overall"] = "degraded"
        report["platforms"][platform_key] = {
            "label": platform["label"],
            "state": "ok" if db_result["state"] == "ok" and all(
                service["state"] == "ok" for service in services_out.values()
            ) else "degraded",
            "database": db_result,
            "services": services_out,
        }

    save_json(STATE_FILE, state)
    save_json(STATUS_FILE, report)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true", help="allowlisted web/API restart after repeated failures")
    parser.add_argument("--once", action="store_true", help="read-only status check")
    args = parser.parse_args()
    print(json.dumps(inspect_all(repair=args.repair), ensure_ascii=False, indent=2))
