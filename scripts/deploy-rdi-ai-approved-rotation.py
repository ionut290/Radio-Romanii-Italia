#!/usr/bin/env python3
"""Synchronize approved RDI AI MUSIC source files into a dedicated AzuraCast rotation.

Only uploads original audio belonging to submissions that are currently approved.
It never edits news, jingles, existing playlists, station settings, or any file
outside the managed media prefix. Membership updates preserve other playlists.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import time

ROOT = Path("/var/lib/rdi-ai-music")
DB = ROOT / "submissions.sqlite3"
UPLOADS = ROOT / "uploads"
MEDIA_PREFIX = "RDI AI MUSIC Approvati"
PLAYLIST_NAME = "RDI AI MUSIC - Brani approvati"
MAX_SOURCE_BYTES = 30 * 1024 * 1024
ID = re.compile(r"^[a-f0-9]{32}$")
AUDIO_EXT = {".mp3", ".wav", ".flac", ".m4a", ".ogg"}

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rdi_azura_client", str(HERE / "deploy-geopolitica-oracle.py"))
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)


def playlist_ids(refs):
    if not isinstance(refs, list):
        raise ValueError("AzuraCast media playlist references are invalid")
    result = set()
    for ref in refs:
        value = ref.get("id") if isinstance(ref, dict) else ref
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise ValueError("AzuraCast playlist identifier is invalid") from None
        if value <= 0:
            raise ValueError("AzuraCast playlist identifier is invalid")
        result.add(value)
    return result


def approved_sources():
    if not DB.is_file():
        raise RuntimeError("RDI AI MUSIC submissions database is unavailable")
    rows = []
    with sqlite3.connect(f"file:{DB}?mode=ro", uri=True) as con:
        con.row_factory = sqlite3.Row
        records = con.execute("""
            SELECT id, stored_name, file_name, title, artist
            FROM submissions
            WHERE status='approved' AND stored_name IS NOT NULL
            ORDER BY created_at ASC
        """).fetchall()
    for row in records:
        sid = str(row["id"])
        stored = str(row["stored_name"])
        if not ID.fullmatch(sid) or Path(stored).name != stored:
            raise ValueError("Invalid approved RDI AI MUSIC file reference")
        source = UPLOADS / stored
        suffix = source.suffix.lower()
        if suffix not in AUDIO_EXT or not source.is_file():
            raise RuntimeError("Approved original audio file missing: " + sid)
        size = source.stat().st_size
        if not 1000 <= size <= MAX_SOURCE_BYTES:
            raise ValueError("Approved audio file size is invalid: " + sid)
        path = f"{MEDIA_PREFIX}/{sid}{suffix}"
        if PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts:
            raise ValueError("Unsafe managed media path")
        rows.append({
            "id": sid, "source": source, "path": path,
            "title": str(row["title"])[:160], "artist": str(row["artist"])[:100],
        })
    return rows


def find_playlist(client, create=False):
    playlists = client.call("GET", "/station/1/playlists")
    if not isinstance(playlists, list):
        raise RuntimeError("Unexpected AzuraCast playlist response")
    found = [p for p in playlists if isinstance(p, dict) and p.get("name") == PLAYLIST_NAME]
    if len(found) > 1:
        raise RuntimeError("Duplicate approved RDI AI MUSIC playlists found")
    if not found and create:
        client.call("POST", "/station/1/playlists", {
            "name": PLAYLIST_NAME,
            "description": "Rotazione automatica: solo brani RDI AI MUSIC approvati con file originale.",
            "type": "default", "source": "songs", "order": "shuffle",
            "is_enabled": False, "is_jingle": False, "weight": 3,
            "include_in_requests": False, "include_in_on_demand": False,
            "avoid_duplicates": True, "schedule_items": [],
        })
        return find_playlist(client, False)
    return found[0] if found else None


def validate_playlist(item):
    if not item:
        raise RuntimeError("Approved RDI AI MUSIC playlist is missing")
    expected = {
        "name": PLAYLIST_NAME, "type": "default", "source": "songs",
        "order": "shuffle",
    }
    if any(item.get(k) != v for k, v in expected.items()) or item.get("is_jingle") is True:
        raise RuntimeError("Managed approved-song playlist has unexpected configuration")
    if item.get("schedule_items") not in (None, []):
        raise RuntimeError("Managed approved-song playlist has an unsafe schedule")
    try:
        value = int(item["id"])
    except (KeyError, TypeError, ValueError):
        raise RuntimeError("Invalid approved-song playlist ID") from None
    if value <= 0:
        raise RuntimeError("Invalid approved-song playlist ID")
    return value


def media_index(client):
    items = client.call("GET", "/station/1/files")
    if not isinstance(items, list):
        raise RuntimeError("Unexpected AzuraCast media response")
    result = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str) or not path or path in result:
            raise RuntimeError("Duplicate or invalid AzuraCast media path")
        result[path] = item
    return result


def upload_one(client, item):
    raw = item["source"].read_bytes()
    if not 1000 <= len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError("Refusing unexpected source size")
    response = client.call("POST", "/station/1/files", {
        "path": item["path"],
        "file": base64.b64encode(raw).decode("ascii"),
    })
    if isinstance(response, dict) and response.get("errors"):
        raise RuntimeError("AzuraCast rejected approved audio upload")


def wait_for_paths(client, expected):
    for _ in range(20):
        index = media_index(client)
        if expected.issubset(index):
            return index
        time.sleep(3)
    raise RuntimeError("AzuraCast did not index all approved uploaded audio")


def save_snapshot(pid, memberships):
    folder = ROOT / "approved-rotation"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = folder / f"azura-memberships-{stamp}.json"
    target.write_text(json.dumps({
        "playlist_id": pid, "memberships": {k: sorted(v) for k, v in memberships.items()},
    }, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    target.chmod(0o600)


def set_memberships(client, groups):
    for members, paths in groups.items():
        values = sorted(members)
        for start in range(0, len(paths), 20):
            batch = paths[start:start + 20]
            result = client.call("PUT", "/station/1/files/batch", {
                "do": "playlist", "playlists": values, "files": batch, "dirs": [],
            })
            if isinstance(result, dict) and result.get("errors"):
                raise RuntimeError("AzuraCast rejected playlist membership update")


def sync(client):
    approved = approved_sources()
    playlist = find_playlist(client, create=True)
    pid = validate_playlist(playlist)
    current = media_index(client)

    missing_paths = {item["path"] for item in approved if item["path"] not in current}
    for item in approved:
        if item["path"] in missing_paths:
            upload_one(client, item)
    approved_paths = {item["path"] for item in approved}
    current = wait_for_paths(client, approved_paths) if approved_paths else media_index(client)

    managed = {
        path: row for path, row in current.items()
        if path.startswith(MEDIA_PREFIX + "/")
    }
    original = {path: playlist_ids(row.get("playlists")) for path, row in managed.items()}
    desired = {}
    for path, memberships in original.items():
        desired[path] = (memberships | {pid}) if path in approved_paths else (memberships - {pid})

    changed = {path for path in desired if desired[path] != original[path]}
    save_snapshot(pid, {path: original[path] for path in changed})
    groups = {}
    for path in sorted(changed):
        groups.setdefault(frozenset(desired[path]), []).append(path)

    touched = list(changed)
    try:
        set_memberships(client, groups)
        refreshed = media_index(client)
        for path in touched:
            if playlist_ids(refreshed[path].get("playlists")) != desired[path]:
                raise RuntimeError("AzuraCast membership verification failed")
    except Exception:
        rollback = {}
        for path in touched:
            rollback.setdefault(frozenset(original[path]), []).append(path)
        try:
            set_memberships(client, rollback)
        except Exception:
            pass
        raise

    enabled = bool(approved_paths)
    client.call("PUT", f"/station/1/playlist/{pid}", {"is_enabled": enabled})
    final = find_playlist(client)
    if bool(final.get("is_enabled")) != enabled:
        raise RuntimeError("Approved-song playlist activation did not persist")
    print("RDI_AI_APPROVED_ROTATION_PLAYLIST_ID=" + str(pid))
    print("RDI_AI_APPROVED_ROTATION_TRACKS=" + str(len(approved_paths)))
    print("RDI_AI_APPROVED_ROTATION_UPLOADED=" + str(len(missing_paths)))
    print("RDI_AI_APPROVED_ROTATION_MEMBERSHIPS_CHANGED=" + str(len(changed)))
    print("RDI_AI_APPROVED_ROTATION_ENABLED=" + str(enabled).lower())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("sync",))
    parser.add_argument("--php-helper", required=True)
    args = parser.parse_args()
    helper = Path(args.php_helper).read_bytes()
    token = ""
    try:
        token = backend.azura_php(helper, "create")
        sync(backend.Client(token))
    finally:
        if token:
            backend.azura_php(helper, "revoke", token.split(":", 1)[0])


if __name__ == "__main__":
    main()
