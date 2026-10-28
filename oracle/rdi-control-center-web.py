#!/usr/bin/env python3
"""Loopback-only read-only HTTP view for the RDI Control Center."""
import json
import pathlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = pathlib.Path("/opt/rdi-control-center")
STATUS = pathlib.Path("/var/lib/rdi-control-center/status.json")
HTML = ROOT / "control-center.html"

class Handler(BaseHTTPRequestHandler):
    server_version = "RDIControlCenter/1"

    def send_bytes(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/":
            try:
                body = HTML.read_bytes()
                self.send_bytes(200, body, "text/html; charset=utf-8")
            except OSError:
                self.send_bytes(503, b"Dashboard unavailable", "text/plain; charset=utf-8")
            return
        if self.path.split("?", 1)[0] == "/api/status":
            try:
                data = json.loads(STATUS.read_text(encoding="utf-8"))
                body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                self.send_bytes(200, body, "application/json; charset=utf-8")
            except (OSError, ValueError):
                self.send_bytes(503, b'{"state":"not_ready"}', "application/json; charset=utf-8")
            return
        self.send_bytes(404, b"Not found", "text/plain; charset=utf-8")

    def do_POST(self):
        self.send_bytes(405, b"Read-only dashboard", "text/plain; charset=utf-8")

    def log_message(self, fmt, *args):
        # No request data or credentials are logged.
        return

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8787), Handler).serve_forever()
