#!/usr/bin/env python3
"""RDI Control Center: Oracle health probes and narrowly guarded recovery.

Monitoring is read-only. The only automated service recovery is the already
configured primary YouTube relay, and only when systemd reports it failed,
the unit remains enabled, and visual mode is not active. AzuraCast playlists
and all other services are never changed by this agent.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent
SITE = "https://radioromanii.duckdns.org"
STREAM_URL = "https://radio-romanii-italia.duckdns.org/listen/radio-romanii-italia/radio.mp3"
STATION_API = "https://radio-romanii-italia.duckdns.org/api/nowplaying/1"
REPO_API = "https://api.github.com/repos/ionut290/Radio-Romanii-Italia/actions"
STATE = pathlib.Path(os.environ.get("RDI_CONTROL_CENTER_STATE", "/var/lib/rdi-control-center"))
REPORT = STATE / "status.json"
RESTARTS = STATE / "restarts.json"
AUDIT = STATE / "actions.jsonl"
CHECK_HISTORY = STATE / "checks.jsonl"
BROADCAST_HISTORY = pathlib.Path("/var/lib/rdi-geopolitica/broadcast-history.json")
GITHUB_ACTIONS_RUNS = "https://api.github.com/repos/ionut290/Radio-Romanii-Italia/actions/runs?per_page=100"
WORKFLOW_NAMES = {
    "editorial.yml": "Redazione editoriale",
    "news.yml": "Notizie radio",
    "geopolitica.yml": "Feed geopolitico",
    "geopolitica-radio.yml": "Notiziario geopolitico MP3",
    "editorial-check.yml": "Controllo editoriale",
}
COOLDOWN = 3600
MAX_RESTARTS_24H = 3
AZURA_CACHE_SECONDS = 900
MAX_JSON_BYTES = 5_000_000
PRIMARY_YOUTUBE = "radio-youtube.service"
VISUAL_YOUTUBE = "radio-youtube-visual.service"


def utcnow() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def run_command(args: list[str], timeout: int = 15) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)


def load_json(path: pathlib.Path, default):
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError):
        return default


def fetch(url: str, timeout: int = 8, limit: int = MAX_JSON_BYTES) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "RDI-Control-Center/2.0", "Accept": "application/json, text/html, audio/mpeg, */*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError("response exceeds size limit")
        return response.status, dict(response.headers.items()), body


def fetch_json(url: str, timeout: int = 8):
    code, headers, body = fetch(url, timeout)
    return code, json.loads(body.decode("utf-8")), headers


def systemd_unit(name: str) -> dict:
    try:
        result = run_command([
            "systemctl", "show", name,
            "--property=LoadState,ActiveState,SubState,UnitFileState,MainPID,NRestarts",
            "--no-pager",
        ])
        fields = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        return {
            "unit": name,
            "load": fields.get("LoadState", "unknown"),
            "state": fields.get("ActiveState", "unknown"),
            "substate": fields.get("SubState", "unknown"),
            "enabled": fields.get("UnitFileState", "unknown") in ("enabled", "enabled-runtime", "static", "indirect"),
            "main_pid": int(fields.get("MainPID", "0") or 0),
            "restarts": int(fields.get("NRestarts", "0") or 0),
            "probe": "ok" if result.returncode == 0 else "error",
        }
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"unit": name, "load": "unknown", "state": "unknown", "substate": "unknown",
                "enabled": False, "main_pid": 0, "probe": "error", "error_type": type(exc).__name__}


def probe_site() -> dict:
    pages = {}
    for name, url in {
        "home": SITE + "/",
        "editorial_status": SITE + "/data/editorial-status.json",
        "news_summaries": SITE + "/data/news-summaries.json",
        "geopolitica_feed": SITE + "/data/geopolitica-news.json",
        "geopolitica_articles": SITE + "/data/geopolitica-articles.json",
        "geopolitica_radio_verified": SITE + "/data/geopolitica-radio-verified.json",
    }.items():
        try:
            code, headers, body = fetch(url, timeout=10)
            item = {"http": code, "bytes": len(body), "state": "ok" if 200 <= code < 300 else "error"}
            if name != "home":
                try:
                    data = json.loads(body.decode("utf-8"))
                    item["json"] = "valid"
                    if isinstance(data, dict):
                        if name == "editorial_status":
                            for key in ("news_updated_at", "editorial_updated_at", "feed_total",
                                        "pending_total", "archived_editorials"):
                                if key in data:
                                    item[key] = data[key]
                        elif name == "geopolitica_feed":
                            item["items"] = len(data.get("items", [])) if isinstance(data.get("items"), list) else None
                            item["updated_at"] = data.get("updated_at")
                        elif name == "geopolitica_articles":
                            records = data.get("items", {})
                            item["items"] = len(records) if isinstance(records, dict) else None
                            item["unreviewed"] = sum(
                                1 for x in records.values() if isinstance(x, dict)
                                and x.get("editorial_status") != "editorially_reviewed"
                            ) if isinstance(records, dict) else None
                        elif name == "geopolitica_radio_verified":
                            records = data.get("items", [])
                            item["items"] = len(records) if isinstance(records, list) else None
                            item["updated_at"] = data.get("updated_at")
                    elif isinstance(data, list):
                        item["items"] = len(data)
                except (UnicodeDecodeError, ValueError):
                    item["json"] = "invalid"
                    item["state"] = "error"
            pages[name] = item
        except (OSError, ValueError, urllib.error.URLError) as exc:
            pages[name] = {"state": "error", "error_type": type(exc).__name__}
    status = "ok" if all(x.get("state") == "ok" for x in pages.values()) else "degraded"
    return {"state": status, "pages": pages}


def probe_station() -> dict:
    nowplaying = {}
    try:
        code, data, _ = fetch_json(STATION_API, timeout=8)
        if not isinstance(data, dict):
            raise ValueError("unexpected response")
        listeners = data.get("listeners") if isinstance(data.get("listeners"), dict) else {}
        song = data.get("now_playing") if isinstance(data.get("now_playing"), dict) else {}
        track = song.get("song") if isinstance(song.get("song"), dict) else {}
        nowplaying = {
            "state": "ok" if data.get("is_online") is True else "degraded",
            "http": code,
            "station_is_online": data.get("is_online"),
            "listeners_current": listeners.get("current"),
            "title": str(track.get("title", ""))[:180],
            "artist": str(track.get("artist", ""))[:120],
            "updated_at": data.get("now_playing", {}).get("played_at") if isinstance(data.get("now_playing"), dict) else None,
        }
    except (OSError, ValueError, TypeError, urllib.error.URLError) as exc:
        nowplaying = {"state": "error", "error_type": type(exc).__name__}
    stream = {}
    try:
        # A live stream is unbounded. Read a small sample instead of using fetch(),
        # whose JSON size guard correctly rejects responses larger than its limit.
        req = urllib.request.Request(
            STREAM_URL,
            headers={"User-Agent": "RDI-Control-Center/2.1", "Accept": "audio/*, */*"},
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            code = response.status
            headers = dict(response.headers.items())
            body = response.read(16384)
        content_type = headers.get("Content-Type", "").split(";", 1)[0].lower()
        has_id3 = body.startswith(b"ID3")
        has_mpeg_frame = any(
            body[i] == 0xFF and i + 1 < len(body) and (body[i + 1] & 0xE0) == 0xE0
            for i in range(min(len(body) - 1, 8192))
        )
        audio_frame = has_id3 or has_mpeg_frame
        reachable = 200 <= code < 300 and len(body) > 0
        stream = {
            "state": "ok" if reachable else "error",
            "http": code,
            "content_type": content_type,
            "reachable": reachable,
            "audio_frame_detected": audio_frame,
            "audio_format": "mp3" if audio_frame else "not_identified",
            "bytes_sampled": len(body),
            "note": "Stream endpoint responded; audio framing is shown separately",
        }
    except (OSError, ValueError, urllib.error.URLError) as exc:
        stream = {"state": "error", "reachable": False, "error_type": type(exc).__name__}
    state = "ok" if nowplaying.get("state") == "ok" and stream.get("state") == "ok" else "degraded"
    return {"state": state, "nowplaying": nowplaying, "stream": stream}

def probe_azuracast(previous: dict | None) -> dict:
    checked = None
    if isinstance(previous, dict):
        stamp = previous.get("checked_at")
        try:
            checked = dt.datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            checked = None
    age = (utcnow() - checked).total_seconds() if checked else None
    if previous and age is not None and 0 <= age < AZURA_CACHE_SECONDS:
        cached = dict(previous)
        cached["cache_age_seconds"] = int(age)
        return cached
    script = ROOT / "deploy-geopolitica-oracle.py"
    helper = ROOT / "rdi-geopolitica-auth.php"
    if not script.is_file() or not helper.is_file():
        return {"state": "unconfigured", "detail": "Read-only AzuraCast probe files are missing"}
    try:
        result = run_command([
            "/usr/bin/python3", str(script), "inspect", "--php-helper", str(helper),
        ], timeout=60)
        output = result.stdout
        parsed = {}
        for line in output.splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                if key in ("AZURACAST_AUTHENTICATED", "AZURACAST_PLAYLIST_COUNT",
                           "RDI_GEOPOLITICA_EXISTS", "RDI_PLAYLIST_ID", "RDI_PLAYLIST_ENABLED",
                           "RDI_PLAYLIST_MINUTE", "RDI_PLAYLIST_MEDIA_COUNT", "RDI_PLAYLIST_PLAYED_AT",
                           "RDI_OWN_MEDIA_COUNT"):
                    parsed[key] = value[:160]
        enabled = parsed.get("RDI_PLAYLIST_ENABLED") == "True"
        try:
            media_count = int(parsed.get("RDI_PLAYLIST_MEDIA_COUNT", "0"))
        except (TypeError, ValueError):
            media_count = -1
        valid_configuration = (
            parsed.get("RDI_GEOPOLITICA_EXISTS") == "true"
            and parsed.get("RDI_PLAYLIST_ID") == "12"
            and parsed.get("RDI_PLAYLIST_MINUTE") == "10"
        )
        expected_suspended = not enabled and media_count == 0 and valid_configuration
        expected = (
            result.returncode == 0
            and parsed.get("AZURACAST_AUTHENTICATED") == "true"
            and valid_configuration
            and (enabled or expected_suspended)
        )
        return {
            "state": "ok" if expected else "degraded",
            "mode": "active" if enabled else ("suspended_no_media" if expected_suspended else "suspended_with_media"),
            "checked_at": utcnow().isoformat(),
            "playlist_id": parsed.get("RDI_PLAYLIST_ID"),
            "playlist_enabled": parsed.get("RDI_PLAYLIST_ENABLED"),
            "scheduled_minute": parsed.get("RDI_PLAYLIST_MINUTE"),
            "media_count": parsed.get("RDI_PLAYLIST_MEDIA_COUNT"),
            "last_played_at": parsed.get("RDI_PLAYLIST_PLAYED_AT"),
            "own_media_count": parsed.get("RDI_OWN_MEDIA_COUNT"),
            "playlist_count": parsed.get("AZURACAST_PLAYLIST_COUNT"),
            "changes_made": False,
        }
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        return {"state": "error", "checked_at": utcnow().isoformat(),
                "error_type": type(exc).__name__, "changes_made": False}


def cpu_percent() -> float | None:
    def snapshot():
        fields = pathlib.Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        values = [int(x) for x in fields]
        idle = values[3] + (values[4] if len(values) > 4 else 0)
        return sum(values), idle
    try:
        total_a, idle_a = snapshot()
        time.sleep(0.2)
        total_b, idle_b = snapshot()
        total = total_b - total_a
        return round(100 * (total - (idle_b - idle_a)) / total, 1) if total > 0 else None
    except (OSError, ValueError, IndexError):
        return None


def probe_oracle() -> dict:
    resources = {"cpu_percent": cpu_percent(), "load_average": [round(x, 2) for x in os.getloadavg()]}
    try:
        mem = {}
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            key, value = line.split(":", 1)
            if key in ("MemTotal", "MemAvailable"):
                mem[key] = int(value.strip().split()[0]) * 1024
        total = mem.get("MemTotal")
        available = mem.get("MemAvailable")
        resources["memory_percent"] = round(100 * (total - available) / total, 1) if total and available is not None else None
        resources["memory_total_bytes"] = total
        resources["memory_available_bytes"] = available
    except (OSError, ValueError):
        resources["memory_percent"] = None
    try:
        disk = shutil.disk_usage("/")
        resources["disk_percent"] = round(100 * disk.used / disk.total, 1)
        resources["disk_free_bytes"] = disk.free
        resources["disk_total_bytes"] = disk.total
    except OSError:
        resources["disk_percent"] = None
    try:
        docker = run_command(["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"], timeout=10)
        containers = []
        for line in docker.stdout.splitlines()[:40]:
            if "|" in line:
                name, status = line.split("|", 1)
                containers.append({"name": name[:80], "status": status[:120]})
        resources["docker"] = {
            "state": "ok" if docker.returncode == 0 else "error",
            "container_count": len(containers),
            "running_count": sum(1 for x in containers if x["status"].lower().startswith("up ")),
            "azuracast_container": next((x["status"] for x in containers if x["name"] == "azuracast"), "not_found"),
            "containers": containers,
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        resources["docker"] = {"state": "error", "error_type": type(exc).__name__}
    return resources


def probe_youtube() -> dict:
    base = systemd_unit(PRIMARY_YOUTUBE)
    visual = systemd_unit(VISUAL_YOUTUBE)
    watchdog = systemd_unit("rdi-youtube-browser-watchdog.timer")
    rescue = systemd_unit("rdi-youtube-browser-rescue.service")
    base_active = base["state"] == "active"
    visual_active = visual["state"] == "active"
    if base_active and visual_active:
        mode = "conflict"
    elif base_active:
        mode = "standard_relay"
    elif visual_active:
        mode = "visual_relay"
    else:
        mode = "offline"
    try:
        result = run_command(["pgrep", "-x", "ffmpeg"], timeout=5)
        ffmpeg_count = sum(1 for line in result.stdout.splitlines() if line.strip().isdigit())
    except (OSError, subprocess.TimeoutExpired):
        ffmpeg_count = None
    return {
        "state": "ok" if mode in ("standard_relay", "visual_relay") and ffmpeg_count else "degraded",
        "mode": mode,
        "encoder_process_count": ffmpeg_count,
        "rtmp_connection_confirmed": False,
        "note": "systemd e processo encoder sono osservabili; la connessione YouTube richiede conferma separata",
        "services": {"standard": base, "visual": visual, "browser_watchdog": watchdog, "browser_rescue": rescue},
    }


def probe_geopolitica_bulletin() -> dict:
    history = load_json(BROADCAST_HISTORY, {})
    editions = history.get("editions", []) if isinstance(history, dict) else []
    editions = [x for x in editions if isinstance(x, dict)]
    latest = editions[-1] if editions else {}
    edition_id = str(latest.get("edition_id", ""))
    edition_date = latest.get("edition_date")
    if not edition_date and re.fullmatch(r"20[0-9]{6}-[0-9]{4}", edition_id):
        edition_date = f"{edition_id[0:4]}-{edition_id[4:6]}-{edition_id[6:8]}"
    source_urls = latest.get("source_urls", [])
    if not isinstance(source_urls, list):
        source_urls = []
    cleanup = systemd_unit("rdi-geopolitica-cleanup.timer")
    return {
        "state": "ok" if latest else "degraded",
        "edition_id": edition_id or None,
        "edition_date": edition_date,
        "generated_at": latest.get("generated_at"),
        "story_count": latest.get("story_count", len(latest.get("signatures", []))),
        "duration_seconds": latest.get("audio_duration_seconds"),
        "source_count": len({x for x in source_urls if isinstance(x, str) and x.startswith("https://")}),
        "cleanup_timer": cleanup,
        "history_count": len(editions),
        "note": "Dati dell'ultima edizione consegnata; la playlist può essere sospesa se oggi non ci sono notizie verificate.",
    }


def probe_workflow_runs() -> dict:
    try:
        code, payload, _ = fetch_json(GITHUB_ACTIONS_RUNS, timeout=10)
        rows = payload.get("workflow_runs", []) if isinstance(payload, dict) else []
        latest = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path", "")).split("@", 1)[0].rsplit("/", 1)[-1]
            if path not in WORKFLOW_NAMES:
                continue
            stamp = str(row.get("created_at", ""))
            previous = latest.get(path)
            if previous is None or stamp > str(previous.get("created_at", "")):
                latest[path] = row
        result = {}
        failures = []
        for path, label in WORKFLOW_NAMES.items():
            run = latest.get(path)
            if not run:
                continue
            item = {
                "label": label,
                "status": str(run.get("status", "unknown")),
                "conclusion": run.get("conclusion"),
                "created_at": run.get("created_at"),
                "updated_at": run.get("updated_at"),
                "html_url": run.get("html_url"),
                "run_number": run.get("run_number"),
            }
            result[path] = item
            if item["status"] == "completed" and item["conclusion"] == "failure":
                failures.append(path)
        return {
            "state": "degraded" if failures else "ok",
            "http": code,
            "latest": result,
            "failed_workflows": failures,
            "source": "GitHub Actions API pubblica, sola lettura",
        }
    except (OSError, ValueError, TypeError, urllib.error.URLError) as exc:
        return {"state": "unavailable", "error_type": type(exc).__name__,
                "latest": {}, "source": "GitHub Actions API pubblica, sola lettura"}


def probe_redaction(site: dict) -> dict:
    pages = site.get("pages", {})
    metrics = pages.get("editorial_status", {})
    geo = pages.get("geopolitica_feed", {})
    articles = pages.get("geopolitica_articles", {})
    feed_time = metrics.get("news_updated_at")
    geo_time = geo.get("updated_at")
    def age_minutes(value):
        try:
            stamp = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                return None
            return max(0, int((utcnow() - stamp.astimezone(dt.timezone.utc)).total_seconds() / 60))
        except (TypeError, ValueError):
            return None
    feed_age = age_minutes(feed_time)
    geo_age = age_minutes(geo_time)
    workflows = probe_workflow_runs()
    state = "ok" if feed_age is not None and feed_age <= 90 else "degraded"
    if workflows.get("state") == "degraded":
        state = "degraded"
    return {
        "state": state,
        "automation": workflows,
        "feed_updated_at": feed_time,
        "feed_age_minutes": feed_age,
        "pending_total": metrics.get("pending_total"),
        "feed_total": metrics.get("feed_total"),
        "geopolitica_items": geo.get("items"),
        "geopolitica_age_minutes": geo_age,
        "geopolitica_articles": articles.get("items"),
        "geopolitica_unreviewed": articles.get("unreviewed"),
        "verified_radio_items": (pages.get("geopolitica_radio_verified") or {}).get("items"),
        "note": "Feed e schede radio sono monitorati separatamente; gli esiti dei workflow mostrano il completamento tecnico, non sostituiscono la verifica editoriale delle fonti.",
    }


def read_restart_history() -> dict:
    value = load_json(RESTARTS, {})
    return value if isinstance(value, dict) else {}


def append_audit(entry: dict) -> None:
    STATE.mkdir(mode=0o750, parents=True, exist_ok=True)
    entry = {**entry, "recorded_at": utcnow().isoformat()}
    if AUDIT.exists() and AUDIT.stat().st_size > 1_000_000:
        lines = AUDIT.read_text(encoding="utf-8", errors="replace").splitlines()[-2000:]
        AUDIT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    with AUDIT.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
    AUDIT.chmod(0o600)


def read_audit() -> list[dict]:
    if not AUDIT.is_file():
        return []
    try:
        lines = AUDIT.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]
        return [item for line in lines if line.strip()
                for item in [json.loads(line)] if isinstance(item, dict)]
    except (OSError, ValueError):
        return []


def read_check_history() -> list[dict]:
    if not CHECK_HISTORY.is_file():
        return []
    try:
        rows = []
        for line in CHECK_HISTORY.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]:
            if line.strip():
                value = json.loads(line)
                if isinstance(value, dict):
                    rows.append(value)
        return rows[-50:]
    except (OSError, ValueError):
        return []


def append_check_history(report: dict) -> list[dict]:
    STATE.mkdir(mode=0o750, parents=True, exist_ok=True)
    snapshot = {
        "checked_at": report.get("checked_at"),
        "overall": report.get("overall"),
        "issues": report.get("issues", []),
        "radio": (report.get("radio") or {}).get("state"),
        "azuracast": (report.get("azuracast") or {}).get("state"),
        "youtube": (report.get("youtube") or {}).get("state"),
        "redaction": (report.get("redaction") or {}).get("state"),
        "site": (report.get("site") or {}).get("state"),
        "cpu_percent": (report.get("oracle") or {}).get("cpu_percent"),
        "memory_percent": (report.get("oracle") or {}).get("memory_percent"),
        "disk_percent": (report.get("oracle") or {}).get("disk_percent"),
    }
    try:
        with CHECK_HISTORY.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(snapshot, ensure_ascii=False, separators=(",", ":")) + "\n")
        CHECK_HISTORY.chmod(0o600)
        rows = CHECK_HISTORY.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(rows) > 500:
            temp = CHECK_HISTORY.with_suffix(".jsonl.tmp")
            temp.write_text("\n".join(rows[-500:]) + "\n", encoding="utf-8")
            temp.replace(CHECK_HISTORY)
            CHECK_HISTORY.chmod(0o600)
    except OSError:
        pass
    return read_check_history()


def maybe_repair_youtube(report: dict) -> dict | None:
    youtube = report.get("youtube", {})
    services = youtube.get("services", {})
    base = services.get("standard", {})
    visual = services.get("visual", {})
    if base.get("load") != "loaded" or base.get("state") != "failed":
        return None
    if not base.get("enabled") or visual.get("state") == "active":
        return None
    history = read_restart_history()
    now = time.time()
    recent = [x for x in history.get(PRIMARY_YOUTUBE, [])
              if isinstance(x, (int, float)) and 0 <= now - x < 86400]
    if len(recent) >= MAX_RESTARTS_24H or (recent and now - recent[-1] < COOLDOWN):
        return {"service": PRIMARY_YOUTUBE, "action": "blocked_by_cooldown"}
    STATE.mkdir(mode=0o750, parents=True, exist_ok=True)
    history[PRIMARY_YOUTUBE] = recent + [now]
    temp = RESTARTS.with_suffix(".json.tmp")
    temp.write_text(json.dumps(history, indent=2) + "\n", encoding="utf-8")
    temp.replace(RESTARTS)
    RESTARTS.chmod(0o600)
    result = run_command(["systemctl", "restart", PRIMARY_YOUTUBE], timeout=45)
    after = systemd_unit(PRIMARY_YOUTUBE)
    verified = result.returncode == 0 and after.get("state") == "active"
    action = {
        "service": PRIMARY_YOUTUBE,
        "action": "restart_verified" if verified else ("restart_attempted" if result.returncode == 0 else "restart_failed"),
        "exit_code": result.returncode,
        "verified_active": verified,
        "cooldown_seconds": COOLDOWN,
        "attempts_last_24h": len(history[PRIMARY_YOUTUBE]),
        "reason": "systemd reported failed; primary unit enabled; visual mode inactive",
    }
    append_audit(action)
    return action


def inspect(repair: bool = False, force_azura: bool = False) -> dict:
    STATE.mkdir(mode=0o750, parents=True, exist_ok=True)
    previous = load_json(REPORT, {})
    previous_azura = previous.get("azuracast") if isinstance(previous, dict) else None
    site = probe_site()
    radio = probe_station()
    youtube = probe_youtube()
    oracle = probe_oracle()
    azura = probe_azuracast(None if force_azura else previous_azura)
    report = {
        "schema_version": 2,
        "checked_at": utcnow().isoformat(),
        "overall": "ok",
        "radio": radio,
        "azuracast": azura,
        "youtube": youtube,
        "redaction": probe_redaction(site),
        "bulletin": probe_geopolitica_bulletin(),
        "site": site,
        "oracle": oracle,
        "actions": [],
        "safety": {
            "other_playlists_modified": False,
            "youtube_live_configuration_modified": False,
            "automatic_repair_allowlist": [PRIMARY_YOUTUBE],
            "visual_relay_auto_restart": False,
        },
    }
    if repair:
        action = maybe_repair_youtube(report)
        if action:
            report["actions"].append(action)
            if action.get("action") in ("restart_attempted", "restart_failed"):
                report["youtube"] = probe_youtube()
    issues = []
    for section in ("radio", "azuracast", "youtube", "redaction", "site"):
        if report[section].get("state") not in ("ok",):
            issues.append(section)
    cpu = oracle.get("cpu_percent")
    memory = oracle.get("memory_percent")
    disk = oracle.get("disk_percent")
    if isinstance(cpu, (int, float)) and cpu >= 95:
        issues.append("oracle_cpu")
    if isinstance(memory, (int, float)) and memory >= 95:
        issues.append("oracle_memory")
    if isinstance(disk, (int, float)) and disk >= 90:
        issues.append("oracle_disk")
    if oracle.get("docker", {}).get("state") != "ok":
        issues.append("oracle_docker")
    if oracle.get("docker", {}).get("azuracast_container") == "not_found":
        issues.append("azuracast_container_missing")
    elif not str(oracle.get("docker", {}).get("azuracast_container", "")).lower().startswith("up "):
        issues.append("azuracast_container_not_running")
    report["audit_log"] = read_audit()
    if report.get("bulletin", {}).get("cleanup_timer", {}).get("state") != "active":
        issues.append("geopolitica_cleanup_timer")
    report["issues"] = sorted(set(issues))
    report["overall"] = "ok" if not report["issues"] else "degraded"
    report["check_history"] = append_check_history(report)
    temp = REPORT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(REPORT)
    REPORT.chmod(0o640)
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--repair", action="store_true", help="apply only the guarded primary YouTube recovery")
    parser.add_argument("--force-azuracast-probe", action="store_true", help="refresh the read-only AzuraCast playlist probe")
    args = parser.parse_args()
    print(json.dumps(inspect(args.repair, args.force_azuracast_probe), ensure_ascii=False, indent=2))
