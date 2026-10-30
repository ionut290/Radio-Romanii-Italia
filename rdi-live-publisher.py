#!/usr/bin/env python3
"""Publish today's editor-approved text and media to the RDI live feed."""
import hashlib
import json
import os
import pathlib
import re
import shutil
import tempfile
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = pathlib.Path("/var/lib/rdi-telegram-live")
PENDING = ROOT / "pending"
APPROVED = ROOT / "approved"
OUTPUT = pathlib.Path("/var/lib/docker/volumes/azuracast_station_data/_data/rdi-live-feed.json")
MEDIA_ROOT = OUTPUT.parent / "rdi-live-media"
PUBLIC_BASE = "https://radio-romanii-italia.duckdns.org/rdi-live-media"
ALLOWED_STATUSES = {"approved_waiting_broadcast", "approved"}
MAX_TEXT_CHARS = 700
MAX_MEDIA_BYTES = 20 * 1024 * 1024
ROME = ZoneInfo("Europe/Rome")
MEDIA_EXTENSIONS = {
    "photo": {".jpg", ".jpeg", ".png", ".webp"},
}


def purge_before_today(today):
    """Remove old queue records, uploaded attachments, and public media copies."""
    removed_records = 0
    removed_uploads = 0
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
                    source = pathlib.Path(media["file"])
                    try:
                        resolved = source.resolve()
                        resolved.relative_to(pending_root)
                    except (OSError, ValueError):
                        continue
                    if resolved == pending_root:
                        continue
                    try:
                        source.unlink(missing_ok=True)
                        removed_uploads += 1
                    except OSError:
                        pass

            try:
                path.unlink()
                removed_records += 1
            except OSError:
                pass

    removed_public = 0
    if MEDIA_ROOT.is_dir():
        for day_dir in MEDIA_ROOT.iterdir():
            if not day_dir.is_dir() or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day_dir.name):
                continue
            if day_dir.name < today.isoformat():
                try:
                    removed_public += sum(1 for p in day_dir.rglob("*") if p.is_file())
                    shutil.rmtree(day_dir)
                except OSError:
                    pass

    return removed_records, removed_uploads, removed_public


def publish_media(record, source_id, day_text, index):
    media = record
    kind = media.get("type")
    if kind not in MEDIA_EXTENSIONS:
        return None
    raw_path = media.get("file")
    if not isinstance(raw_path, str):
        return None

    source = pathlib.Path(raw_path)
    try:
        resolved = source.resolve(strict=True)
        resolved.relative_to(PENDING.resolve())
        size = resolved.stat().st_size
    except (OSError, ValueError):
        return None

    suffix = resolved.suffix.lower()
    if suffix not in MEDIA_EXTENSIONS[kind] or size <= 0 or size > MAX_MEDIA_BYTES:
        return None

    day_dir = MEDIA_ROOT / day_text
    day_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(f"{source_id}:{index}".encode("utf-8")).hexdigest()[:20]
    filename = f"{digest}{suffix}"
    target = day_dir / filename
    if not target.exists() or target.stat().st_size != size:
        with tempfile.NamedTemporaryFile(dir=day_dir, prefix=".rdi-media-", delete=False) as stream:
            temp_name = stream.name
        try:
            shutil.copyfile(resolved, temp_name)
            os.chmod(temp_name, 0o644)
            os.replace(temp_name, target)
        finally:
            try:
                os.unlink(temp_name)
            except FileNotFoundError:
                pass

    public_type = "audio" if kind == "voice" else kind
    return {
        "type": public_type,
        "url": f"{PUBLIC_BASE}/{day_text}/{filename}",
        "size": size,
    }


def main():
    now = datetime.now(ROME)
    today = now.date()
    today_text = today.isoformat()
    removed_records, removed_uploads, removed_public = purge_before_today(today)
    items = []
    text_count = 0
    media_count = 0

    if APPROVED.is_dir():
        for path in APPROVED.glob("*.json"):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if record.get("status") not in ALLOWED_STATUSES:
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
            message = record.get("text")
            message = " ".join(message.split())[:MAX_TEXT_CHARS].strip() if isinstance(message, str) else ""
            raw_media = record.get("media")
            media_items = raw_media if isinstance(raw_media, list) else []
            published_media = []

            for media_index, media_record in enumerate(media_items):
                if not isinstance(media_record, dict):
                    continue
                published = publish_media(media_record, source_id, today_text, media_index)
                if not published:
                    continue
                published["id"] = f"{public_id}-m{media_index}"
                published["text"] = message
                published["date"] = sent_at.isoformat(timespec="seconds")
                items.append((order, media_index + 1, published))
                published_media.append(published)
                media_count += 1

            if message and not published_media:
                items.append((order, 0, {
                    "id": public_id,
                    "type": "text",
                    "text": message,
                    "date": sent_at.isoformat(timespec="seconds"),
                }))
                text_count += 1

    items.sort(key=lambda pair: (pair[0], pair[1], pair[2]["id"]))
    payload = {
        "day": today_text,
        "items": [item for _, _, item in items],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=OUTPUT.parent, prefix=".rdi-live-", delete=False
    ) as stream:
        json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
        stream.write("\n")
        temp_name = stream.name
    os.chmod(temp_name, 0o644)
    os.replace(temp_name, OUTPUT)
    print(
        f"Feed {today_text}: {text_count} testi e {media_count} media approvati; "
        f"rimossi {removed_records} messaggi, {removed_uploads} allegati e "
        f"{removed_public} copie pubbliche scadute"
    )


if __name__ == "__main__":
    main()
