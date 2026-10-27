#!/usr/bin/env python3
"""Safely deploy the current Italian RDI Geopolitica bulletin to AzuraCast.

Executed as root on the existing Oracle host via the already configured SSH
connection. It uses a short-lived admin API key that is created through the
official AzuraCast ORM and ALWAYS revoked on exit. No secrets in logs or GitHub.
Only the dedicated Geopolitica playlist or our own MP3s may be changed.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://radio-romanii-italia.duckdns.org/api"
STATION = 1
PLAYLIST_NAME = "RDI Geopolitica - ogni ora"
MEDIA_DIR = "RDI Geopolitica"
FILENAME_RE = re.compile(r"^RDI-GEOPOLITICA-IT-(20\d{6})-(\d{4})\.mp3$")
TIMEOUT_SECONDS = 45


def azura_php(source: bytes, action: str, *args: str) -> str:
    cmd = ["docker", "exec", "-i", "azuracast", "php", "/dev/stdin", action, *args]
    done = subprocess.run(cmd, input=source, capture_output=True, timeout=30, check=False)
    if done.returncode != 0:
        # Never print script stdout (may contain the temporary credential).
        err = done.stderr.decode("utf-8", "replace")
        raise RuntimeError("AzuraCast helper failed: " + err[:500])
    return done.stdout.decode("utf-8", "replace").strip()


class Client:
    def __init__(self, token: str):
        if not re.fullmatch(r"[a-f0-9]{16}:[a-f0-9]{16,64}", token):
            raise ValueError("Invalid temporary AzuraCast API credential")
        self.token = token

    def call(self, method: str, path: str, body: dict | None = None):
        if not path.startswith("/station/1/"):
            raise ValueError("Refusing API access outside the RDI station")
        data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            API + path, data=data, method=method,
            headers={"Authorization": "Bearer " + self.token,
                     "Content-Type": "application/json", "Accept": "application/json",
                     "User-Agent": "RDI-Geopolitica-Oracle/1.0"},
        )
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as response:
                payload = response.read(2_000_000 if method != "POST" else 500_000)
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as error:
            response = error.read(1500).decode("utf-8", "replace")
            raise RuntimeError(f"AzuraCast API {method} {path} HTTP {error.code}: {response[:300]}") from None


def playlist(client: Client, create: bool) -> dict | None:
    rows = client.call("GET", "/station/1/playlists")
    if not isinstance(rows, list):
        raise ValueError("Unexpected AzuraCast playlist response")
    ours = [p for p in rows if p.get("name") == PLAYLIST_NAME]
    if len(ours) > 1:
        raise ValueError("Multiple matching RDI Geopolitica playlists: refusing update")
    if ours:
        record = ours[0]
        if record.get("type") != "once_per_hour" or int(record.get("play_per_hour_minute", -1)) != 10:
            raise ValueError("A playlist with this name exists but has unexpected schedule")
        return record
    if not create:
        return None
    body = {
        "name": PLAYLIST_NAME,
        "description": "Notiziario italiano automatico con jingle. Nuove notizie, fonti e schede video su RDI.",
        "type": "once_per_hour",
        "source": "songs",
        "order": "sequential",
        "is_enabled": False,  # Activate only once upload + assignment succeed.
        "play_per_hour_minute": 10,
        "include_in_requests": False,
        "include_in_on_demand": False,
        "avoid_duplicates": False,
        "backend_options": ["single_track"],
        "weight": 5,
        "schedule_items": [],
    }
    client.call("POST", "/station/1/playlists", body)
    # Get actual server-generated ID; never predict it.
    result = playlist(client, False)
    if not result:
        raise RuntimeError("New playlist not visible after create")
    print(f"PLAYLIST_CREATED id={result['id']}")
    return result


def enable(client: Client, rec: dict, enabled: bool) -> None:
    if bool(rec.get("is_enabled")) == enabled:
        return
    client.call("PUT", f"/station/1/playlist/{int(rec['id'])}",
                {"is_enabled": enabled})
    updated = playlist(client, False)
    if not updated or bool(updated.get("is_enabled")) != enabled:
        raise RuntimeError("Playlist enabled state was not persisted")
    print("PLAYLIST_STATUS=" + ("enabled" if enabled else "disabled"))


def valid_issue(manifest_file: pathlib.Path, mp3_file: pathlib.Path) -> tuple[dict, str]:
    item = json.loads(manifest_file.read_text(encoding="utf-8"))
    title = str(item.get("track_title", ""))
    filename = item.get("audio_filename", "")
    if item.get("language") != "it" or not re.fullmatch(r"RDI-GEOPOLITICA-IT-20\d{6}-\d{4}", title):
        raise ValueError("Not an Italian RDI Geopolitica edition")
    if filename != title + ".mp3" or mp3_file.name != filename or not FILENAME_RE.fullmatch(filename):
        raise ValueError("MP3 filename does not match the editorial manifest")
    if not (1 <= int(item.get("story_count", 0)) <= 5):
        raise ValueError("Empty or unsupported editorial edition")
    generated = dt.datetime.fromisoformat(str(item.get("generated_at", "")))
    if generated.tzinfo is None:
        raise ValueError("Edition timestamp missing timezone")
    age = (dt.datetime.now(dt.timezone.utc) - generated.astimezone(dt.timezone.utc)).total_seconds()
    if not (-120 <= age <= 2 * 3600):
        raise ValueError(f"Episode is not fresh enough ({age:.0f}s old)")
    size = mp3_file.stat().st_size
    if not (100_000 < size < 20_000_000):
        raise ValueError(f"Unexpected MP3 size: {size}")
    duration = float(item.get("audio_duration_seconds", 0))
    if not 40 <= duration <= 420:
        raise ValueError("Unexpected audio duration")
    return item, MEDIA_DIR + "/" + filename


def list_own_media(client: Client):
    rows = client.call("GET", "/station/1/files")
    if not isinstance(rows, list):
        raise RuntimeError("Unexpected station media list")
    own = []
    for row in rows:
        p = str(row.get("path", ""))
        if p.startswith(MEDIA_DIR + "/") and FILENAME_RE.fullmatch(p.split("/")[-1]):
            own.append(row)
    return own


def remove_old_from_playlist(client: Client, media: list, newest: str) -> None:
    previous = [row for row in media if row["path"] != newest]
    if not previous:
        return
    # Do not delete old files here: Liquidsoap may be playing one already.
    paths = [row["path"] for row in previous]
    result = client.call("PUT", "/station/1/files/batch",
                         {"do": "playlist", "files": paths,
                          "dirs": [], "playlists": []})
    if isinstance(result, dict) and result.get("errors"):
        raise RuntimeError("Could not unlink stale RDI broadcasts from the playlist")
    print(f"OLD_RDI_TRACKS_UNLINKED={len(paths)}")


def prune_expired_own_media(client: Client, media: list[dict], newest: str) -> None:
    """Keep a two-hour safety window for recently broadcast MP3s."""
    removed = 0
    now = dt.datetime.now(dt.timezone.utc)
    for record in media:
        relative = str(record.get("path", ""))
        if relative == newest or not relative.startswith(MEDIA_DIR + "/"):
            continue
        match = FILENAME_RE.fullmatch(relative.split("/")[-1])
        if not match:
            continue
        try:
            stamp = dt.datetime.strptime("".join(match.groups()), "%Y%m%d%H%M")
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
            age = (now - stamp).total_seconds()
            if age < 2 * 3600:
                continue
            media_id = int(record.get("id", 0))
            if media_id <= 0:
                continue
            # Delete only detached RDI editions older than two hours; never the newest.
            client.call("DELETE", f"/station/1/file/{media_id}")
            removed += 1
        except (ValueError, RuntimeError) as error:
            print("OLD_TRACK_RETENTION_WARNING=" + type(error).__name__)
    print(f"OLD_RDI_MP3S_REMOVED={removed}")


def apply(client: Client, issue_file: pathlib.Path, mp3_file: pathlib.Path) -> None:
    item, relative = valid_issue(issue_file, mp3_file)
    # Confirm authorized access before creating anything.
    rec = playlist(client, False)
    if rec:
        print(f"PLAYLIST_FOUND id={rec['id']}")
    tracks = list_own_media(client)
    if any(row["path"] == relative for row in tracks):
        print("MEDIA_ALREADY_UPLOADED=true")
    else:
        # AzuraCast's official JSON UploadFile schema expects base64-encoded MP3.
        body = {"path": relative,
                "file": base64.b64encode(mp3_file.read_bytes()).decode("ascii")}
        response = client.call("POST", "/station/1/files", body)
        print("NEW_MEDIA_UPLOADED=true")
        if isinstance(response, dict) and response.get("path") not in (None, relative):
            raise RuntimeError("AzuraCast uploaded media to an unexpected path")

    # AzuraCast may index asynchronously; poll until its media API sees the MP3.
    for attempt in range(10):
        tracks = list_own_media(client)
        if any(row["path"] == relative for row in tracks):
            break
        time.sleep(3)
    else:
        raise RuntimeError("New MP3 not yet indexed; leaving existing station playlists untouched")

    if not rec:
        rec = playlist(client, True)
    playlist_id = int(rec["id"])
    # API batch action is the supported method for binding a media file to playlists.
    assigned = client.call("PUT", "/station/1/files/batch", {
        "do": "playlist", "playlists": [playlist_id], "files": [relative], "dirs": []
    })
    if isinstance(assigned, dict) and assigned.get("errors"):
        raise RuntimeError(f"New MP3 playlist association failed: {assigned['errors']!r}")
    print(f"NEW_MEDIA_ASSIGNED_TO_PLAYLIST={playlist_id}")
    # Once the new edition is safely present, detach old ones so only the
    # latest bulletin can be selected at the next top-of-hour window.
    remove_old_from_playlist(client, tracks, relative)
    enable(client, rec, True)
    verified = playlist(client, False)
    if not verified or not verified.get("is_enabled"):
        raise RuntimeError("RDI news playlist not activated")
    prune_expired_own_media(client, tracks, relative)
    print("RDI_GEOPOLITICA_HOURLY=ACTIVE")
    print("RDI_GEOPOLITICA_CURRENT_TRACK=" + item["track_title"])


def suspend(client: Client) -> None:
    rec = playlist(client, False)
    if rec is None:
        print("RDI_GEOPOLITICA_HOURLY=NOT_CONFIGURED")
        return
    enable(client, rec, False)
    print("RDI_GEOPOLITICA_HOURLY=SUSPENDED_NO_RECENT_VERIFIED_NEWS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "apply", "suspend"])
    parser.add_argument("--manifest")
    parser.add_argument("--mp3")
    parser.add_argument("--php-helper", default="/tmp/rdi-geopolitica-auth.php")
    args = parser.parse_args()
    helper = pathlib.Path(args.php_helper).read_bytes()
    if args.action == "apply":
        if not args.mp3 or not args.manifest:
            parser.error("--mp3 and --manifest are required")
        issue, relative = valid_issue(pathlib.Path(args.manifest), pathlib.Path(args.mp3))
        print("VERIFIED_ISSUE=" + issue["edition_id"])
    token = ""
    try:
        token = azura_php(helper, "create")
        client = Client(token)
        if args.action == "inspect":
            playlists = client.call("GET", "/station/1/playlists")
            print("AZURACAST_AUTHENTICATED=true")
            print(f"AZURACAST_PLAYLIST_COUNT={len(playlists)}")
            ours = [p for p in playlists if p.get("name") == PLAYLIST_NAME]
            print("RDI_GEOPOLITICA_EXISTS=" + str(bool(ours)).lower())
            if ours:
                p = ours[0]
                print("RDI_PLAYLIST_ID=" + str(p.get("id")))
                print("RDI_PLAYLIST_ENABLED=" + str(p.get("is_enabled")))
                print("RDI_PLAYLIST_MINUTE=" + str(p.get("play_per_hour_minute")))
                print("RDI_PLAYLIST_MEDIA_COUNT=" + str(p.get("num_songs")))
                media = list_own_media(client)
                print("RDI_OWN_MEDIA_COUNT=" + str(len(media)))
                for row in media[-3:]:
                    print("RDI_MEDIA=" + str(row.get("path")) + "|id=" + str(row.get("id"))
                          + "|playlists=" + str(row.get("playlists"))[:220])
        elif args.action == "apply":
            apply(client, pathlib.Path(args.manifest), pathlib.Path(args.mp3))
        else:
            suspend(client)
        return 0
    finally:
        if token:
            azura_php(helper, "revoke", token.split(":", 1)[0])


if __name__ == "__main__":
    raise SystemExit(main())
