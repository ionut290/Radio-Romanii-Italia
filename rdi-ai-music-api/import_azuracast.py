#!/usr/bin/env python3
"""Publish one *approved* RDI AI MUSIC upload to AzuraCast.

No implicit publishing: invoke with --publish ID after configuring the station
and media folder. Assign the AI-MUSIC folder to a playlist in AzuraCast Media
Manager before use; only mapped folders participate in AutoDJ rotation.
Reads the existing /etc/rdi-ai-music.env via systemd EnvironmentFile when run
as a secured service account. Never print or commit the API key.
"""
import argparse
import base64
import json
import os
import re
import sqlite3
import ssl
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

ROOT = Path(os.environ.get("RDI_AI_DATA_DIR", "/var/lib/rdi-ai-music"))
DB = ROOT / "submissions.sqlite3"
FILES = ROOT / "uploads"

def safe_fragment(value, limit=65):
    clean = re.sub(r"[^\w. -]+", "_", value, flags=re.UNICODE).strip(" ._")
    return clean[:limit] or "untitled"

def publish(sid, dry_run=True):
    if not re.fullmatch(r"[a-f0-9]{32}", sid):
        raise ValueError("Invalid submission ID")
    with sqlite3.connect(DB, timeout=20) as con:
        con.row_factory = sqlite3.Row
        con.execute("""CREATE TABLE IF NOT EXISTS azura_imports (
            submission_id TEXT PRIMARY KEY, media_path TEXT NOT NULL,
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
        existing = con.execute("SELECT media_path FROM azura_imports WHERE submission_id=?", (sid,)).fetchone()
        if existing:
            return {"status": "already_imported", "path": existing["media_path"]}
        record = con.execute("SELECT id,artist,title,stored_name,status FROM submissions WHERE id=?", (sid,)).fetchone()
        if record is None:
            raise ValueError("Submission not found")
        if record["status"] != "approved":
            raise ValueError("Only approved submissions can be published")
        if not record["stored_name"]:
            raise ValueError("This submission contains only a link. Download and verify audio manually.")
        filename = record["stored_name"]
        if not re.fullmatch(r"[a-f0-9]{32}\.(mp3|wav|flac|m4a|ogg)", filename):
            raise ValueError("Unsafe upload path")
        audio_path = FILES / filename
        if not audio_path.is_file() or not audio_path.stat().st_size:
            raise ValueError("Approved audio file is missing or empty")
        destination = "AI-MUSIC/" + safe_fragment(record["artist"]) + " - " + safe_fragment(record["title"]) + " - " + sid[:10] + audio_path.suffix.lower()
        if dry_run:
            return {"status": "dry_run", "path": destination, "bytes": audio_path.stat().st_size}
        api_url = os.environ.get("RDI_AI_AZURA_API_BASE", "").rstrip("/")
        station_id = os.environ.get("RDI_AI_AZURA_STATION_ID", "")
        token = os.environ.get("RDI_AI_AZURA_API_KEY", "")
        if not api_url.startswith("https://") or not station_id.isdigit() or not token:
            raise ValueError("Configure RDI_AI_AZURA_API_BASE (HTTPS), RDI_AI_AZURA_STATION_ID and RDI_AI_AZURA_API_KEY")
        if audio_path.stat().st_size > 30 * 1024 * 1024:
            raise ValueError("Audio file exceeds import limit")
        payload = json.dumps({"path": destination, "file": base64.b64encode(audio_path.read_bytes()).decode("ascii")}).encode()
        url = f"{api_url}/api/station/{station_id}/files"
        req = Request(url, data=payload, headers={"Authorization": "Bearer " + token,
            "Content-Type": "application/json", "Accept": "application/json"}, method="POST")
        try:
            with urlopen(req, timeout=100, context=ssl.create_default_context()) as resp:
                if resp.status not in (200, 201):
                    raise ValueError("AzuraCast rejected the upload")
                result = json.loads(resp.read(1024 * 1024))
        except HTTPError as exc:
            raise RuntimeError(f"AzuraCast upload HTTP {exc.code}") from None
        except URLError as exc:
            raise RuntimeError("AzuraCast connection failed") from exc
        # Require the API to acknowledge a media object before marking imported.
        if not isinstance(result, dict) or not result.get("id"):
            raise RuntimeError("AzuraCast did not confirm a media ID; inspect the media folder before retrying")
        con.execute("INSERT INTO azura_imports(submission_id,media_path) VALUES(?,?)", (sid,destination))
        con.commit()
        return {"status": "imported", "path": destination, "media_id": result["id"]}

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import only approved RDI AI MUSIC uploads into AzuraCast")
    parser.add_argument("submission_id", help="32-character submission ID")
    parser.add_argument("--publish", action="store_true", help="Actually upload the file (default is dry run)")
    args = parser.parse_args()
    try:
        print(json.dumps(publish(args.submission_id, dry_run=not args.publish), ensure_ascii=False))
    except (OSError, sqlite3.Error, ValueError, RuntimeError) as exc:
        print(f"Import refused: {exc}", file=sys.stderr)
        raise SystemExit(1)
