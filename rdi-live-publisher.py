#!/usr/bin/env python3
"""Publish today's approved Telegram text and purge expired queue messages."""
import hashlib
import json
import os
import pathlib
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path("/var/lib/rdi-telegram-live")
PENDING = ROOT / "pending"
APPROVED = ROOT / "approved"
OUTPUT = pathlib.Path("/var/lib/docker/volumes/azuracast_station_data/_data/rdi-live-feed.json")
ALLOWED_STATUSES = {"approved_waiting_broadcast", "approved"}
MAX_TEXT_CHARS = 700
ROME = ZoneInfo("Europe/Rome")


def purge_before_today(today):
    """Remove old message records and their uploaded attachments only."""
    removed_records = 0
    removed_media = 0
    pending_root = PENDING.resolve()

    for queue in (PENDING, APPROVED):
        if not queue.is_dir():
            continue
        for path in queue.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                timestamp = int(record.get("date") or 0)
                if timestamp <= 0:
                    continue
                sent_day = datetime.fromtimestamp(timestamp, timezone.utc).astimezone(ROME).date()
            except (OSError, json.JSONDecodeError, TypeError, ValueError, OverflowError):
                continue

            if sent_day >= today:
                continue

            media_items = record.get("media")
            if isinstance(media_items, list):
                for media in media_items:
                    if not isinstance(media, dict) or not isinstance(media.get("file"), str):
                        continue
                    media_path = pathlib.Path(media["file"])
                    try:
                        resolved = media_path.resolve()
                        resolved.relative_to(pending_root)
                    except (OSError, ValueError):
                        continue
                    if resolved == pending_root:
                        continue
                    try:
                        media_path.unlink(missing_ok=True)
                        removed_media += 1
                    except OSError:
                        pass

            try:
                path.unlink()
                removed_records += 1
            except OSError:
                pass

    return removed_records, removed_media


def main():
    now = datetime.now(ROME)
    today = now.date()
    removed_records, removed_media = purge_before_today(today)
    today_text = today.isoformat()
    items = []

    if APPROVED.is_dir():
        for path in APPROVED.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if record.get("status") not in ALLOWED_STATUSES or record.get("media"):
                continue
            message = record.get("text")
            if not isinstance(message, str):
                continue
            message = " ".join(message.split())[:MAX_TEXT_CHARS].strip()
            if not message:
                continue
            try:
                order = int(record.get("date") or 0)
            except (TypeError, ValueError):
                continue
            if order <= 0:
                continue
            sent_at = datetime.fromtimestamp(order, timezone.utc).astimezone(ROME)
            if sent_at.date() != today:
                continue
            source_id = str(record.get("update_id") or path.stem)
            public_id = hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:20]
            items.append((order, {
                "id": public_id,
                "type": "text",
                "text": message,
                "date": sent_at.isoformat(timespec="seconds"),
            }))

    items.sort(key=lambda pair: (pair[0], pair[1]["id"]))
    payload = {
        "day": today_text,
        "items": [item for _, item in items],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=OUTPUT.parent, prefix=".rdi-live-", delete=False
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\\n")
        temp_name = stream.name
    os.chmod(temp_name, 0o644)
    os.replace(temp_name, OUTPUT)
    print(
        f"Feed {today_text}: {len(payload['items'])} messaggi approvati; "
        f"rimossi {removed_records} messaggi scaduti e {removed_media} allegati"
    )


if __name__ == "__main__":
    main()
