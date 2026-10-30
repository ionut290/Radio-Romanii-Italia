#!/usr/bin/env python3
"""Publish only text items explicitly approved by the RDI editor."""
import hashlib
import json
import os
import pathlib
import tempfile

APPROVED = pathlib.Path("/var/lib/rdi-telegram-live/approved")
OUTPUT = pathlib.Path("/var/lib/docker/volumes/azuracast_station_data/_data/rdi-live-feed.json")
ALLOWED_STATUSES = {"approved_waiting_broadcast", "approved"}
MAX_ITEMS = 20
MAX_TEXT_CHARS = 700

def main():
    items = []
    if APPROVED.is_dir():
        for path in sorted(APPROVED.glob("*.json"), key=lambda p: p.name):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if record.get("status") not in ALLOWED_STATUSES:
                continue
            if record.get("media"):
                continue
            message = record.get("text")
            if not isinstance(message, str):
                continue
            message = " ".join(message.split())[:MAX_TEXT_CHARS].strip()
            if not message:
                continue
            source_id = str(record.get("update_id") or path.stem)
            public_id = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:20]
            try:
                order = int(record.get("date") or 0)
            except (TypeError, ValueError):
                order = 0
            items.append((order, {
                "id": public_id,
                "type": "text",
                "text": message,
            }))
    items.sort(key=lambda pair: (pair[0], pair[1]["id"]))
    payload = {"items": [item for _, item in items[-MAX_ITEMS:]]}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=OUTPUT.parent, prefix=".rdi-live-", delete=False
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
        temp_name = stream.name
    os.chmod(temp_name, 0o644)
    os.replace(temp_name, OUTPUT)
    print(f"RDI live feed aggiornato: {len(payload['items'])} messaggi testuali approvati")

if __name__ == "__main__":
    main()
