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


CLEANUP_ROOT = pathlib.Path("/usr/local/lib/rdi-geopolitica")
CLEANUP_UNIT = "rdi-geopolitica-cleanup"


def public_nowplaying() -> dict:
    request = urllib.request.Request(
        API + "/nowplaying/1",
        headers={"Accept": "application/json", "User-Agent": "RDI-Geopolitica-cleanup/1.0"},
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        data = json.loads(response.read(2_000_000))
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected AzuraCast now-playing response")
    return data


def episode_title(song: dict) -> str:
    for value in (song.get("title"), song.get("text")):
        match = re.search(r"(RDI-GEOPOLITICA-IT-20\d{6}-\d{4})", str(value or ""))
        if match:
            return match.group(1)
    return ""


def completed_episode_names(data: dict, now: float | None = None) -> set[str]:
    now = time.time() if now is None else now
    current = episode_title((data.get("now_playing") or {}).get("song") or {})
    completed = set()
    history = data.get("song_history", [])
    if not isinstance(history, list):
        return completed
    for row in history:
        if not isinstance(row, dict):
            continue
        title = episode_title(row.get("song") or {})
        if not title or title == current:
            continue
        try:
            played_at = float(row.get("played_at", 0))
            duration = float(row.get("duration", 0))
        except (TypeError, ValueError):
            continue
        # Let Liquidsoap finish the MP3 before removing it from AzuraCast.
        if duration > 0 and now >= played_at + duration + 30:
            completed.add(title + ".mp3")
    return completed


def playlist_ids(record: dict) -> set[int] | None:
    linked = record.get("playlists")
    if not isinstance(linked, list):
        return None
    result = set()
    for item in linked:
        if isinstance(item, dict):
            item = item.get("id")
        try:
            result.add(int(item))
        except (TypeError, ValueError):
            return None
    return result


def epoch_seconds(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    raw = str(value or "").strip()
    try:
        return float(raw)
    except ValueError:
        parsed = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.timestamp()


def cleanup_played(client: Client, data: dict) -> None:
    rec = playlist(client, False)
    if rec is None or int(rec.get("id", -1)) != 12:
        print("RDI_DELETE=SKIPPED_PLAYLIST_NOT_ID_12")
        return
    now = time.time()
    current = episode_title((data.get("now_playing") or {}).get("song") or {})
    completed = completed_episode_names(data, now)
    # The playlist API retains its last-played timestamp after the public song history
    # rolls over. With one RDI track assigned at a time, this safely catches a
    # completed episode when the cleaner is first installed.
    try:
        playlist_played_at = epoch_seconds(rec.get("played_at", 0))
    except (TypeError, ValueError, OverflowError):
        playlist_played_at = 0
    media = list_own_media(client)
    episode_stamps = {}
    for record in media:
        name = str(record.get("path", "")).split("/")[-1]
        match = FILENAME_RE.fullmatch(name)
        if not match:
            continue
        try:
            from zoneinfo import ZoneInfo
            generated = dt.datetime.strptime("".join(match.groups()), "%Y%m%d%H%M")
            episode_stamps[name] = generated.replace(tzinfo=ZoneInfo("Europe/Rome")).timestamp()
        except (ValueError, OverflowError):
            continue
    # Only the newest edition that existed at the recorded playlist play time
    # can be the detached file selected by this single-track playlist.
    latest_before_play = max(
        (name for name, stamp in episode_stamps.items() if stamp <= playlist_played_at),
        key=lambda name: episode_stamps[name], default="",
    )
    for record in media:
        relative = str(record.get("path", ""))
        filename = relative.split("/")[-1]
        match = FILENAME_RE.fullmatch(filename)
        if not match:
            continue
        ids = playlist_ids(record)
        if ids is None or not ids.issubset({12}):
            print("RDI_DELETE=SKIPPED_OTHER_PLAYLIST_OR_UNKNOWN_LINKS|" + filename)
            continue
        generated = episode_stamps.get(filename, 0)
        finished = playlist_played_at > generated and now >= playlist_played_at + 450
        currently_playing = episode_title((data.get("now_playing") or {}).get("song") or {}) == match.group(0)
        history_confirms = filename in completed and not currently_playing
        playlist_confirms = finished and not currently_playing and filename == latest_before_play
        if not (history_confirms or playlist_confirms):
            continue
        media_id = int(record.get("id", 0))
        if media_id <= 0:
            print("RDI_DELETE=SKIPPED_INVALID_MEDIA_ID|" + filename)
            continue
        client.call("DELETE", f"/station/1/file/{media_id}")
        print("RDI_PLAYED_MP3_DELETED=" + filename)


def install_cleanup_timer(helper_file: pathlib.Path) -> None:
    CLEANUP_ROOT.mkdir(parents=True, exist_ok=True)
    installed_script = CLEANUP_ROOT / "deploy-geopolitica-oracle.py"
    installed_helper = CLEANUP_ROOT / "rdi-geopolitica-auth.php"
    installed_script.write_bytes(pathlib.Path(__file__).read_bytes())
    installed_helper.write_bytes(helper_file.read_bytes())
    installed_script.chmod(0o644)
    installed_helper.chmod(0o644)
    service = pathlib.Path("/etc/systemd/system/rdi-geopolitica-cleanup.service")
    timer = pathlib.Path("/etc/systemd/system/rdi-geopolitica-cleanup.timer")
    service.write_text(
        "[Unit]\nDescription=Remove RDI Geopolitica MP3 after completed AzuraCast playback\n"
        "After=docker.service\n\n[Service]\nType=oneshot\n"
        "ExecStart=/usr/bin/python3 /usr/local/lib/rdi-geopolitica/deploy-geopolitica-oracle.py "
        "cleanup-played --php-helper /usr/local/lib/rdi-geopolitica/rdi-geopolitica-auth.php\n"
        "TimeoutStartSec=180\n",
        encoding="utf-8",
    )
    timer.write_text(
        "[Unit]\nDescription=Check completed RDI Geopolitica broadcasts every five minutes\n\n"
        "[Timer]\nOnBootSec=2min\nOnActiveSec=1min\nOnUnitActiveSec=5min\nAccuracySec=30s\nUnit=rdi-geopolitica-cleanup.service\n\n"
        "[Install]\nWantedBy=timers.target\n",
        encoding="utf-8",
    )
    for command in (
        ["systemctl", "daemon-reload"],
        ["systemctl", "enable", "--now", "rdi-geopolitica-cleanup.timer"],
        ["systemctl", "is-active", "--quiet", "rdi-geopolitica-cleanup.timer"],
    ):
        subprocess.run(command, check=True, capture_output=True, timeout=30)
    # Reconcile immediately as well: this prevents a completed old edition from
    # being selected again while waiting for the first timer tick.
    subprocess.run(
        [sys.executable, str(installed_script), "cleanup-played", "--php-helper", str(installed_helper)],
        check=True, timeout=180,
    )
    print("RDI_POSTPLAY_CLEANUP_TIMER=active_interval_5m")


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
    # Persist history only after AzuraCast confirms publication. The generator
    # uses this durable Oracle-local file to avoid repeating recent editions.
    history_path = pathlib.Path("/var/lib/rdi-geopolitica/broadcast-history.json")
    history_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        previous = json.loads(history_path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            previous = {}
    except (OSError, ValueError):
        previous = {}
    editions = previous.get("editions", [])
    if not isinstance(editions, list):
        editions = []
    entry = {
        "edition_id": item["edition_id"],
        "generated_at": item["generated_at"],
        "signatures": item.get("story_signatures", []),
        "source_urls": [src["url"] for src in item.get("sources", []) if isinstance(src, dict) and src.get("url")],
    }
    editions = [e for e in editions if isinstance(e, dict) and e.get("edition_id") != entry["edition_id"]]
    editions.append(entry)
    destination = history_path.with_suffix(".json.tmp")
    try:
        destination.write_text(json.dumps({"editions": editions[-72:]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        destination.replace(history_path)
    except OSError as error:
        print("RDI_HISTORY_WARNING=" + type(error).__name__)
    else:
        print("RDI_HISTORY_RECORDED=" + str(len(editions[-72:])))



def recover(client: Client) -> None:
    """Re-enable only an existing correctly scheduled playlist with indexed RDI audio."""
    rec = playlist(client, False)
    if rec is None:
        print("RDI_RECOVERY=NO_PLAYLIST")
        return
    if rec.get("is_enabled"):
        print("RDI_RECOVERY=ALREADY_ENABLED")
        return
    media = list_own_media(client)
    if not media:
        print("RDI_RECOVERY=NO_INDEXED_RDI_MP3")
        return
    # The file list alone does not prove a track is assigned to this playlist.
    playlist_id = int(rec["id"])
    eligible = []
    for row in media:
        linked = row.get("playlists") or []
        if isinstance(linked, list) and any(
            (isinstance(p, dict) and int(p.get("id", -1)) == playlist_id)
            or (isinstance(p, (int, str)) and str(p) == str(playlist_id))
            for p in linked
        ):
            eligible.append(row)
    if not eligible:
        print("RDI_RECOVERY=NO_ASSIGNED_RDI_MP3")
        return
    # Never broadcast an arbitrarily old bulletin as a current update.
    now = dt.datetime.now(dt.timezone.utc)
    fresh = []
    for row in eligible:
        name = str(row.get("path", "")).split("/")[-1]
        match = FILENAME_RE.fullmatch(name)
        if match:
            stamp = dt.datetime.strptime("".join(match.groups()), "%Y%m%d%H%M")
            stamp = stamp.replace(tzinfo=dt.timezone.utc)
            if dt.timedelta(0) <= now - stamp <= dt.timedelta(hours=2):
                fresh.append(row)
    if not fresh:
        print("RDI_RECOVERY=NO_RECENT_ASSIGNED_MP3")
        return
    enable(client, rec, True)
    print("RDI_RECOVERY=ENABLED_WITH_RECENT_ASSIGNED_MP3")

def suspend(client: Client) -> None:
    rec = playlist(client, False)
    if rec is None:
        print("RDI_GEOPOLITICA_HOURLY=NOT_CONFIGURED")
        return
    enable(client, rec, False)
    print("RDI_GEOPOLITICA_HOURLY=SUSPENDED_NO_RECENT_VERIFIED_NEWS")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "apply", "suspend", "recover", "install-cleanup", "cleanup-played"])
    parser.add_argument("--manifest")
    parser.add_argument("--mp3")
    parser.add_argument("--php-helper", default="/tmp/rdi-geopolitica-auth.php")
    args = parser.parse_args()
    helper_path = pathlib.Path(args.php_helper)
    helper = helper_path.read_bytes()
    if args.action == "install-cleanup":
        install_cleanup_timer(helper_path)
        return 0
    play_data = None
    if args.action == "cleanup-played":
        play_data = public_nowplaying()
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
                print("RDI_PLAYLIST_PLAYED_AT=" + str(p.get("played_at")))
                media = list_own_media(client)
                print("RDI_OWN_MEDIA_COUNT=" + str(len(media)))
                for row in media:
                    print("RDI_MEDIA=" + str(row.get("path")) + "|id=" + str(row.get("id"))
                          + "|playlists=" + str(row.get("playlists"))[:220])
        elif args.action == "apply":
            apply(client, pathlib.Path(args.manifest), pathlib.Path(args.mp3))
            install_cleanup_timer(helper_path)
        elif args.action == "recover":
            recover(client)
        elif args.action == "cleanup-played":
            cleanup_played(client, play_data or {})
        else:
            suspend(client)
        return 0
    finally:
        if token:
            azura_php(helper, "revoke", token.split(":", 1)[0])


if __name__ == "__main__":
    raise SystemExit(main())
