#!/usr/bin/env python3
"""Loopback-only, read-only dashboard for the separate Varga platform bot."""
import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path("/opt/varga-platform-bot")
STATE = pathlib.Path("/var/lib/varga-platform-bot/status.json")
AUDIT = pathlib.Path("/var/lib/varga-platform-bot/actions.jsonl")
HTML = ROOT / "varga-platform-dashboard.html"


class Handler(BaseHTTPRequestHandler):
    def respond(self, status, content_type, body):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/":
            self.respond(200, "text/html; charset=utf-8", HTML.read_bytes())
        elif self.path == "/api/status":
            try:
                data = json.loads(STATE.read_text(encoding="utf-8"))
                actions = []
                if AUDIT.exists():
                    actions = [json.loads(line) for line in AUDIT.read_text(encoding="utf-8").splitlines()[-30:]]
                data["actions"] = actions[-10:]
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.respond(200, "application/json; charset=utf-8", body)
            except (OSError, json.JSONDecodeError):
                self.respond(503, "application/json; charset=utf-8", b'{"state":"unavailable"}')
        else:
            self.respond(404, "text/plain; charset=utf-8", b"Not found")

    def log_message(self, fmt, *args):
        return


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8790), Handler).serve_forever()
