#!/usr/bin/env python3
"""Start the official DPC radar timeline when its iframe enters the live weather slot.

Chrome DevTools is bound to localhost only. This helper reads the live page state
and clicks the official app's Play control in its own frame context; it does not
inspect or transmit stream keys, page content, or viewer data.
"""
from __future__ import annotations

import base64
import fcntl
import json
import os
import secrets
import socket
import struct
import time
import urllib.request
from urllib.parse import urlsplit

DEBUG_ENDPOINT = "http://127.0.0.1:9222/json/list"
MAIN_PAGE_PREFIX = "https://radioromanii.duckdns.org/youtube-news.html"
ITALY_RADAR_PREFIX = "https://radar.protezionecivile.it/"
LOCK_PATH = "/run/lock/rdi-radar-autoplay.lock"


def acquire_lock() -> int:
    os.makedirs(os.path.dirname(LOCK_PATH), exist_ok=True)
    fd = os.open(LOCK_PATH, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        os.close(fd)
        raise SystemExit("Radar autoplay helper already running.")
    return fd


class DevToolsSocket:
    def __init__(self, url: str) -> None:
        parsed = urlsplit(url)
        if parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ValueError("DevTools endpoint must stay on localhost.")
        port = parsed.port or 80
        self.sock = socket.create_connection((parsed.hostname, port), timeout=5)
        self.sock.settimeout(5)
        self.rx = bytearray()
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "Origin: http://127.0.0.1\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = bytearray()
        while b"\r\n\r\n" not in response:
            part = self.sock.recv(4096)
            if not part:
                raise ConnectionError("DevTools closed during WebSocket handshake.")
            response.extend(part)
        header, remainder = bytes(response).split(b"\r\n\r\n", 1)
        if b" 101 " not in header.split(b"\r\n", 1)[0]:
            raise ConnectionError("DevTools rejected the WebSocket connection.")
        self.rx.extend(remainder)
        self.next_id = 1
        self.contexts: dict[str, int] = {}
        self.fragments = bytearray()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _read_exact(self, size: int) -> bytes:
        while len(self.rx) < size:
            part = self.sock.recv(max(4096, size - len(self.rx)))
            if not part:
                raise ConnectionError("DevTools WebSocket closed.")
            self.rx.extend(part)
        out = bytes(self.rx[:size])
        del self.rx[:size]
        return out

    def _send_frame(self, opcode: int, payload: bytes) -> None:
        mask = secrets.token_bytes(4)
        length = len(payload)
        if length < 126:
            header = bytes((0x80 | opcode, 0x80 | length))
        elif length < 65536:
            header = bytes((0x80 | opcode, 0x80 | 126)) + struct.pack("!H", length)
        else:
            header = bytes((0x80 | opcode, 0x80 | 127)) + struct.pack("!Q", length)
        masked = bytes(value ^ mask[i % 4] for i, value in enumerate(payload))
        self.sock.sendall(header + mask + masked)

    def _receive_frame(self) -> tuple[int, bool, bytes]:
        first, second = self._read_exact(2)
        fin = bool(first & 0x80)
        opcode = first & 0x0F
        length = second & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._read_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._read_exact(8))[0]
        masked = bool(second & 0x80)
        mask = self._read_exact(4) if masked else b""
        payload = self._read_exact(length)
        if masked:
            payload = bytes(value ^ mask[i % 4] for i, value in enumerate(payload))
        return opcode, fin, payload

    def _next_message(self) -> dict:
        while True:
            opcode, fin, payload = self._receive_frame()
            if opcode == 0x9:
                self._send_frame(0xA, payload)
                continue
            if opcode == 0x8:
                raise ConnectionError("DevTools WebSocket closed.")
            if opcode == 0x1:
                self.fragments = bytearray(payload)
            elif opcode == 0x0:
                self.fragments.extend(payload)
            elif opcode != 0x2:
                continue
            if not fin:
                continue
            try:
                message = json.loads(self.fragments.decode("utf-8"))
            finally:
                self.fragments.clear()
            self._record_context_event(message)
            return message

    def _record_context_event(self, message: dict) -> None:
        method = message.get("method")
        params = message.get("params", {})
        if method == "Runtime.executionContextCreated":
            context = params.get("context", {})
            aux = context.get("auxData", {})
            if aux.get("isDefault") and aux.get("frameId"):
                self.contexts[aux["frameId"]] = context["id"]
        elif method == "Runtime.executionContextDestroyed":
            context_id = params.get("executionContextId")
            self.contexts = {frame: cid for frame, cid in self.contexts.items() if cid != context_id}
        elif method == "Runtime.executionContextsCleared":
            self.contexts.clear()

    def call(self, method: str, params: dict | None = None) -> dict:
        request_id = self.next_id
        self.next_id += 1
        body = json.dumps({"id": request_id, "method": method, "params": params or {}}).encode("utf-8")
        self._send_frame(0x1, body)
        while True:
            message = self._next_message()
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(message["error"].get("message", "DevTools command failed."))
                return message.get("result", {})

    def evaluate(self, context_id: int, expression: str):
        result = self.call("Runtime.evaluate", {
            "contextId": context_id,
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        })
        if result.get("exceptionDetails"):
            return None
        return result.get("result", {}).get("value")


def frame_urls(node: dict, output: dict[str, str]) -> None:
    frame = node.get("frame", {})
    frame_id = frame.get("id")
    if frame_id:
        output[frame_id] = frame.get("url", "")
    for child in node.get("childFrames", []):
        frame_urls(child, output)


def find_live_target() -> dict | None:
    request = urllib.request.Request(DEBUG_ENDPOINT, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=2) as response:
        targets = json.load(response)
    for target in targets:
        if target.get("type") == "page" and target.get("url", "").startswith(MAIN_PAGE_PREFIX):
            return target
    return None


def main() -> None:
    lock_fd = acquire_lock()
    print("Radar autoplay helper started.", flush=True)
    connection: DevToolsSocket | None = None
    last_state = ""
    while True:
        try:
            if connection is None:
                target = find_live_target()
                if not target or not target.get("webSocketDebuggerUrl"):
                    time.sleep(2)
                    continue
                connection = DevToolsSocket(target["webSocketDebuggerUrl"])
                connection.call("Page.enable")
                connection.call("Runtime.enable")
                print("Connected to the live browser.", flush=True)

            tree = connection.call("Page.getFrameTree").get("frameTree", {})
            urls: dict[str, str] = {}
            frame_urls(tree, urls)
            main_id = next((fid for fid, url in urls.items() if url.startswith(MAIN_PAGE_PREFIX)), None)
            if not main_id or main_id not in connection.contexts:
                time.sleep(2)
                continue

            state = connection.evaluate(
                connection.contexts[main_id],
                "(() => ({active: !!window.rdiWeatherActive, src: document.getElementById('rdiWeatherRadar')?.src || ''}))()",
            )
            if not isinstance(state, dict) or not state.get("active") or not str(state.get("src", "")).startswith(ITALY_RADAR_PREFIX):
                last_state = ""
                time.sleep(2)
                continue

            for frame_id, url in urls.items():
                if url.startswith(ITALY_RADAR_PREFIX) and frame_id in connection.contexts:
                    result = connection.evaluate(
                        connection.contexts[frame_id],
                        "(() => { const b=document.querySelector('#play'); if(!b)return 'loading';"
                        " if(!b.classList.contains('pause')){b.click();return 'started';} return 'playing'; })()",
                    )
                    if result in {"started", "playing"} and result != last_state:
                        print("Italy radar animation " + result + ".", flush=True)
                        last_state = result
            time.sleep(2)
        except KeyboardInterrupt:
            break
        except Exception as error:
            print("Radar autoplay reconnect: " + str(error)[:180], flush=True)
            if connection:
                connection.close()
                connection = None
            time.sleep(3)
    if connection:
        connection.close()
    os.close(lock_fd)


if __name__ == "__main__":
    main()
