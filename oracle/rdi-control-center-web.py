#!/usr/bin/env python3
"""Loopback-only dashboard and tightly allow-listed RDI interventions."""
import datetime as dt
import json
import pathlib
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path("/opt/rdi-control-center")
STATUS = pathlib.Path("/var/lib/rdi-control-center/status.json")
HTML = ROOT / "control-center.html"
AUDIT = pathlib.Path("/var/lib/rdi-control-center/actions.jsonl")
ACTION_LOCK = threading.Lock()
TRUSTED_HOSTS = {"127.0.0.1:8787", "localhost:8787"}
TRUSTED_ORIGINS = {"http://127.0.0.1:8787", "http://localhost:8787"}


def run_status_check():
    result = subprocess.run(
        ["/usr/bin/python3", str(ROOT / "rdi-control-center.py"), "--force-azuracast-probe"],
        capture_output=True, text=True, timeout=150, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("status probe failed")
    data = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise RuntimeError("invalid status report")
    return data


def run_recovery():
    result = subprocess.run(
        ["/usr/bin/python3", str(ROOT / "deploy-geopolitica-oracle.py"), "recover",
         "--php-helper", str(ROOT / "rdi-geopolitica-auth.php")],
        capture_output=True, text=True, timeout=100, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("playlist recovery failed")
    outcomes = [line.partition("=")[2] for line in result.stdout.splitlines()
                if line.startswith("RDI_RECOVERY=")]
    return outcomes[-1] if outcomes else "UNKNOWN"


def run_suspension():
    result = subprocess.run(
        ["/usr/bin/python3", str(ROOT / "deploy-geopolitica-oracle.py"), "suspend",
         "--php-helper", str(ROOT / "rdi-geopolitica-auth.php")],
        capture_output=True, text=True, timeout=100, check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("playlist suspension failed")
    outcomes = [line.partition("=")[2] for line in result.stdout.splitlines()
                if line.startswith("RDI_GEOPOLITICA_HOURLY=")]
    return outcomes[-1] if outcomes else "UNKNOWN"


def append_audit(action, service, result, verified=False):
    AUDIT.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    entry = {
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "action": action, "service": service, "result": result,
        "verified_active": verified, "source": "local_dashboard",
    }
    with AUDIT.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) + "\n")
    AUDIT.chmod(0o600)


def refresh_report_audit(data):
    try:
        lines = AUDIT.read_text(encoding="utf-8", errors="replace").splitlines()[-100:]
        data["audit_log"] = [obj for line in lines if line.strip()
                             for obj in [json.loads(line)] if isinstance(obj, dict)]
    except (OSError, ValueError):
        data["audit_log"] = []
    temp = STATUS.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(STATUS)
    STATUS.chmod(0o640)


class Handler(BaseHTTPRequestHandler):
    server_version = "RDIControlCenter/2"

    def send_bytes(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, code, payload):
        self.send_bytes(code, json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                        "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/":
            try:
                self.send_bytes(200, HTML.read_bytes(), "text/html; charset=utf-8")
            except OSError:
                self.send_bytes(503, b"Dashboard unavailable", "text/plain; charset=utf-8")
            return
        if path == "/api/status":
            try:
                self.send_json(200, json.loads(STATUS.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                self.send_bytes(503, b'{"state":"not_ready"}', "application/json; charset=utf-8")
            return
        self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        if self.client_address[0] not in ("127.0.0.1", "::1"):
            self.send_json(403, {"ok": False, "message": "Accesso consentito solo in locale"})
            return
        if self.headers.get("Host", "") not in TRUSTED_HOSTS:
            self.send_json(403, {"ok": False, "message": "Host non autorizzato"})
            return
        if self.headers.get("Origin", "") not in TRUSTED_ORIGINS:
            self.send_json(403, {"ok": False, "message": "Origine non autorizzata"})
            return
        if self.headers.get("Sec-Fetch-Site", "same-origin") != "same-origin":
            self.send_json(403, {"ok": False, "message": "Richiesta cross-origin rifiutata"})
            return
        if self.headers.get("Content-Type", "").split(";", 1)[0].lower() != "application/json":
            self.send_json(415, {"ok": False, "message": "Richiesta JSON obbligatoria"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 1024:
                raise ValueError("invalid body size")
            body = json.loads(self.rfile.read(length) or b"{}")
            if not isinstance(body, dict):
                raise ValueError("invalid body")
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"ok": False, "message": "Richiesta non valida"})
            return
        path = self.path.split("?", 1)[0]
        if path not in ("/api/actions/refresh", "/api/actions/recover-geopolitica", "/api/actions/suspend-geopolitica"):
            self.send_json(404, {"ok": False, "message": "Azione non disponibile"})
            return
        confirmations = {
            "/api/actions/recover-geopolitica": "RIATTIVA NOTIZIARIO ID 12",
            "/api/actions/suspend-geopolitica": "SOSPENDI NOTIZIARIO ID 12",
        }
        if path in confirmations and body.get("confirmation") != confirmations[path]:
            self.send_json(400, {"ok": False, "message": "Conferma non valida"})
            return
        if not ACTION_LOCK.acquire(blocking=False):
            self.send_json(409, {"ok": False, "message": "Un controllo o intervento è già in corso"})
            return
        try:
            if path == "/api/actions/refresh":
                data = run_status_check()
                append_audit("manual_refresh", "control_center", "completed")
                refresh_report_audit(data)
                self.send_json(200, {"ok": True, "changed": False,
                                     "message": "Controlli aggiornati. Nessuna impostazione modificata.",
                                     "status": data})
                return
            if path == "/api/actions/suspend-geopolitica":
                outcome = run_suspension()
                data = run_status_check()
                enabled = str((data.get("azuracast") or {}).get("playlist_enabled", "")).lower() == "true"
                changed = outcome == "SUSPENDED_NO_CURRENT_EDITION" and not enabled
                messages = {
                    "SUSPENDED_NO_CURRENT_EDITION": "Playlist 12 sospesa e verifica aggiornata.",
                    "ALREADY_SUSPENDED": "Playlist 12 era già sospesa.",
                    "NOT_CONFIGURED": "Playlist 12 non trovata; nessuna modifica eseguita.",
                    "UNEXPECTED_PLAYLIST_ID": "Identità playlist inattesa; intervento bloccato.",
                }
                message = messages.get(outcome, "Sospensione non verificata; controlla lo stato.")
                append_audit("geopolitica_suspend", "azuracast_playlist_12", outcome,
                             verified=not enabled)
                refresh_report_audit(data)
                self.send_json(200, {"ok": True, "changed": changed, "message": message,
                                     "suspension": outcome, "status": data})
                return
            outcome = run_recovery()
            data = run_status_check()
            enabled = str((data.get("azuracast") or {}).get("playlist_enabled", "")).lower() == "true"
            changed = outcome == "ENABLED_WITH_RECENT_UNPLAYED_ASSIGNED_MP3" and enabled
            messages = {
                "ENABLED_WITH_RECENT_UNPLAYED_ASSIGNED_MP3": "Playlist 12 riattivata e verificata.",
                "ALREADY_ENABLED": "Playlist 12 già attiva.",
                "NO_RECENT_UNPLAYED_ASSIGNED_MP3": "Non riattivata: manca un MP3 recente, assegnato e successivo all’ultima trasmissione.",
                "NO_PLAYLIST": "Playlist 12 non trovata; nessuna modifica eseguita.",
                "UNEXPECTED_PLAYLIST_ID": "Identità playlist inattesa; intervento bloccato.",
                "NO_ASSIGNED_RDI_MP3": "Nessun MP3 RDI assegnato; intervento bloccato.",
                "PLAYBACK_TIME_UNVERIFIED": "Ultima riproduzione non verificabile; intervento bloccato.",
            }
            message = messages.get(outcome, "Intervento non eseguito: verifica manuale necessaria.")
            append_audit("geopolitica_recovery", "azuracast_playlist_12",
                         outcome, verified=enabled)
            refresh_report_audit(data)
            self.send_json(200, {"ok": True, "changed": changed, "message": message,
                                 "recovery": outcome, "status": data})
        except subprocess.TimeoutExpired:
            self.send_json(504, {"ok": False, "message": "Controllo scaduto; verifica lo stato aggiornato"})
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError):
            self.send_json(502, {"ok": False, "message": "Azione non completata; controlla lo stato e il registro"})
        finally:
            ACTION_LOCK.release()

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
