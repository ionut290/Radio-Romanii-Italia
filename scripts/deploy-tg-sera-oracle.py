#!/usr/bin/env python3
"""Publish RDI's Italian evening TV news only after validated audio and TV timing.

Dedicated AzuraCast one-track daily 18:00 playlist, date-scoped to the
specific episode so yesterday's bulletin cannot play again tomorrow.

Requires explicit "apply"; "inspect" is read-only. Reuses the existing
short-lived and immediately revoked AzuraCast credential helper on Oracle.
No music, geopolitics or other playlists are changed.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import importlib.util
import json
from pathlib import Path
import re
import sys
import time
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("rdi_azuracast_client", ROOT/"deploy-geopolitica-oracle.py")
backend = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

ROME = ZoneInfo("Europe/Rome")
PLAYLIST_NAME = "RDI TG della Sera - ore 18"
MEDIA_DIR = "RDI TG della Sera"
FILE_RE = re.compile(r"RDI-TG-SERA-IT-(20\d{6})\.mp3")
DATE_RE = re.compile(r"20\d{6}")
MINIMUM_STORIES = 4
SCHEDULE_TIME = (1800, 1859)
DAY_OF_WEEK = [1, 2, 3, 4, 5, 6, 7]
BACKEND_OPTIONS = ["interrupt", "single_track", "prioritize"]


def expected_day(edition: str) -> str:
    if not DATE_RE.fullmatch(edition):
        raise ValueError("Invalid TG date")
    return dt.datetime.strptime(edition, "%Y%m%d").date().isoformat()


def expected_schedule(day: str) -> dict:
    # AzuraCast's own existing station schedules use integer HHMM and weekdays
    # 1..7, as verified on Oracle. start/end dates prevent stale replays.
    return {
        "start_time": SCHEDULE_TIME[0], "end_time": SCHEDULE_TIME[1],
        "start_date": day, "end_date": day,
        "days": DAY_OF_WEEK, "loop_once": True,
    }


def verify_schedule(rows: object, day: str) -> bool:
    if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
        return False
    actual = rows[0]
    expected = expected_schedule(day)
    for field, wanted in expected.items():
        value = actual.get(field)
        if field in ("start_time", "end_time"):
            try:
                value = int(value)
            except (ValueError, TypeError):
                return False
        if field == "days":
            if not isinstance(value, list):
                return False
            value = sorted(value)
        if value != wanted:
            return False
    return True


def validate(edition_path: Path, mp3_path: Path, tv_path: Path,
             now: dt.datetime | None = None) -> tuple[dict, str]:
    now = (now or dt.datetime.now(ROME)).astimezone(ROME)
    data = json.loads(edition_path.read_text(encoding="utf-8"))
    tv = json.loads(tv_path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("language") != "it" or data.get("synthetic_voice") != "it-IT-ElsaNeural":
        raise ValueError("Unsupported TG manifest or voice")
    edition = str(data.get("edition_id", ""))
    day = expected_day(edition)
    if now.date().isoformat() != day or not (16 <= now.hour < 18):
        raise ValueError("Only the current Italian edition may be scheduled between 16:00 and 17:59")
    if now.hour == 17 and now.minute >= 50:
        raise ValueError("Late upload refused: cannot safely program a new 18:00 show")
    title = "RDI-TG-SERA-IT-" + edition
    if data.get("track_title") != title or data.get("audio_filename") != title + ".mp3" or mp3_path.name != title + ".mp3":
        raise ValueError("Episode MP3 and displayed on-air title mismatch")
    when = dt.datetime.fromisoformat(str(data.get("generated_at", "")))
    if when.tzinfo is None or when.astimezone(ROME).date().isoformat() != day:
        raise ValueError("Episode timestamp missing correct day/time zone")
    age = (now - when.astimezone(ROME)).total_seconds()
    if not (-120 <= age <= 2*3600) or when.astimezone(ROME).hour < 16:
        raise ValueError("Episode is stale, futuristic or generated before editorial cutoff")
    cutoff = dt.datetime.fromisoformat(str(data.get("cutoff_at", "")))
    if cutoff.tzinfo is None or cutoff.astimezone(ROME).hour != 16 or cutoff.minute != 0:
        raise ValueError("Newsroom cutoff is not the agreed 16:00 Italy time")
    stories = data.get("articles")
    if not isinstance(stories, list) or not (MINIMUM_STORIES <= len(stories) <= 9):
        raise ValueError("Insufficient or excessive corroborated news reports")
    if int(data.get("story_count", 0)) != len(stories):
        raise ValueError("Not all stories accounted for")
    for item in stories:
        if len(item.get("sources", [])) < 2:
            raise ValueError("Story has no corroborating independent sources")
        if not all(str(u).startswith("https://") for u in item.get("sources", [])):
            raise ValueError("Source URL is not HTTPS")
    if not (200_000 <= mp3_path.stat().st_size <= 55_000_000):
        raise ValueError("Incomplete or oversized TG audio")
    seconds = float(data.get("audio_duration_seconds", 0))
    if not 240 <= seconds <= 2100:
        raise ValueError("Unsupported bulletin duration")
    if (tv.get("type"),tv.get("schema_version"),tv.get("language"),
        tv.get("edition_id"),tv.get("track_title")) != (
        "rdi-daily-tg",1,"it",edition,title
    ):
        raise ValueError("Video chronology does not match the broadcast")
    if tv.get("audio_duration_seconds") != data.get("audio_duration_seconds"):
        raise ValueError("Voice and video duration mismatch")
    if tv.get("timeline") != data.get("timeline"):
        raise ValueError("Video chronology is different from the actual generated audio")
    timeline = data.get("timeline", [])
    if len(timeline) != len(stories)+4 or len([s for s in timeline if s.get("kind") == "story"]) != len(stories):
        raise ValueError("Incomplete on-air scenes")
    if abs(float(timeline[-1].get("end_seconds",0)) - seconds) > 3:
        raise ValueError("End of show is not aligned to voice")
    return data, MEDIA_DIR + "/" + mp3_path.name


def find_playlist(client) -> dict | None:
    rows = client.call("GET", "/station/1/playlists")
    if not isinstance(rows, list):
        raise ValueError("AzuraCast playlists API incompatible")
    matching = [x for x in rows if x.get("name") == PLAYLIST_NAME]
    if len(matching) > 1:
        raise ValueError("Duplicate dedicated evening playlists; no mutation allowed")
    record = matching[0] if matching else None
    if record and (record.get("type") != "once_per_hour" or
                   record.get("source") != "songs" or
                   str(record.get("play_per_hour_minute")) not in {"0", "00"}):
        raise ValueError("Existing name belongs to an unexpected AzuraCast playlist")
    return record


def list_own_media(client) -> list[dict]:
    tracks=client.call("GET", "/station/1/files")
    if not isinstance(tracks,list):
        raise ValueError("Unexpected AzuraCast files API")
    return [f for f in tracks if isinstance(f,dict) and
            str(f.get("path","")).startswith(MEDIA_DIR+"/") and
            FILE_RE.fullmatch(str(f.get("path","")).split("/")[-1])]


def assign(client, media_path: str, playlist_id: int) -> None:
    result=client.call("PUT", "/station/1/files/batch",
                       {"do":"playlist", "playlists":[playlist_id],
                        "files":[media_path],"dirs":[]})
    if isinstance(result,dict) and result.get("errors"):
        raise RuntimeError("Station rejected TG media/playlist association")


def plan_for(day: str) -> dict:
    return {
        "name": PLAYLIST_NAME,
        "description": "TG italiano delle 18 di Radio Românii din Italia. Solo l'edizione del giorno, con fonti verificate.",
        "type": "once_per_hour", "source": "songs", "order": "sequential",
        "play_per_hour_minute": 0,
        "is_enabled": False, "include_in_requests": False,
        "include_in_on_demand": False,
        "avoid_duplicates": False,
        "backend_options": BACKEND_OPTIONS,
        "weight": 5, "schedule_items": [expected_schedule(day)],
    }


def configure(client, playlist: dict | None, day: str) -> dict:
    if playlist is None:
        client.call("POST", "/station/1/playlists", plan_for(day))
        playlist = find_playlist(client)
        if not playlist:
            raise RuntimeError("New private evening TG playlist was not created")
    else:
        playlist_id = int(playlist["id"])
        # Always rewrite dates to today's date; this is how stale shows are
        # excluded even if tomorrow's GitHub scheduled workflow does not run.
        client.call("PUT", f"/station/1/playlist/{playlist_id}",
                    {"is_enabled":False,
                     "schedule_items":[expected_schedule(day)],
                     "backend_options":BACKEND_OPTIONS,
                     "play_per_hour_minute":0,
                     "include_in_requests": False,
                     "include_in_on_demand": False})
        playlist = find_playlist(client)
    if not playlist or not verify_schedule(playlist.get("schedule_items"),day):
        raise RuntimeError("Daily 18:00 date-scoped schedule not persisted; leave show off")
    if not all(x in (playlist.get("backend_options") or []) for x in ["interrupt","single_track"]):
        raise RuntimeError("One-track live-interruption options not persisted")
    return playlist


def activate(client, edition_path: Path, mp3_path: Path, tv_path: Path) -> None:
    data, media_path = validate(edition_path,mp3_path,tv_path)
    edition = data["edition_id"]
    day = expected_day(edition)
    existing = find_playlist(client)
    print("RDI_TG_DAILY_PRECHECK=PASSED",edition)
    old_media = list_own_media(client)
    if not any(x.get("path") == media_path for x in old_media):
        upload = {"path":media_path,
                  "file":base64.b64encode(mp3_path.read_bytes()).decode("ascii")}
        client.call("POST","/station/1/files",upload)
        print("RDI_TG_AUDIO=UPLOADED")
    for _ in range(12):
        current = list_own_media(client)
        if any(x.get("path") == media_path for x in current):
            break
        time.sleep(3)
    else:
        raise RuntimeError("TG file not indexed by AzuraCast; nothing activated")
    # Create/update only the name-protected, isolated TG playlist.
    current_playlist = configure(client,existing,day)
    pid=int(current_playlist["id"])
    assign(client,media_path,pid)
    # Check file belongs to ONLY the dedicated playlist before switching on.
    indexed = next((x for x in list_own_media(client) if x.get("path")==media_path),None)
    if not indexed:
        raise RuntimeError("New TG audio was not indexed")
    linked=indexed.get("playlists")
    if isinstance(linked,list):
        assigned_ids=set()
        for p in linked:
            try:
                assigned_ids.add(int(p["id"] if isinstance(p,dict) else p))
            except (ValueError,KeyError,TypeError):
                raise RuntimeError("Unknown TG audio playlist reference") from None
        if assigned_ids != {pid}:
            raise RuntimeError("TG audio linked to another playlist; activation prevented")
    else:
        raise RuntimeError("Cannot verify media playlist links; activation prevented")
    for f in list_own_media(client):
        p=str(f.get("path",""))
        if p==media_path:
            continue
        refs=f.get("playlists")
        if refs is not None and isinstance(refs,list):
            ids={int(x.get("id")) if isinstance(x,dict) else int(x) for x in refs}
            if not ids or ids == {pid}:
                assign_only=client.call("PUT","/station/1/files/batch",
                          {"do":"playlist","playlists":[],"files":[p],"dirs":[]})
                if isinstance(assign_only,dict) and assign_only.get("errors"):
                    raise RuntimeError("Old RDI TG media not detached")
            else:
                raise RuntimeError("Older TG audio has unexpected playlist associations")
        else:
            raise RuntimeError("Cannot verify old media association")
    # Enable only AFTER the MP3, story sources and published TV chronology are
    # present. One-time-per-day schedule expires at midnight.
    if not current_playlist.get("is_enabled"):
        client.call("PUT",f"/station/1/playlist/{pid}",{"is_enabled":True})
    verified=find_playlist(client)
    if not verified or not verified.get("is_enabled") or not verify_schedule(verified.get("schedule_items"),day):
        raise RuntimeError("Could not verify today's dedicated on-air schedule")
    print("RDI_TG_DAILY_SCHEDULE=ENABLED")
    print("RDI_TG_PLAYLIST_ID="+str(pid))
    print("RDI_TG_BROADCAST_WINDOW=18:00-18:59_Europe/Rome")
    print("RDI_TG_CURRENT_EPISODE="+data["track_title"])
    print("RDI_TG_TV_TIMING_VERIFIED=true")


def prepare_disabled(client) -> None:
    """Create an EMPTY, disabled dedicated TG playlist without touching the live."""
    now=dt.datetime.now(ROME)
    if not 0 <= now.hour < 15:
        raise ValueError("Disabled station setup is restricted to before 15:00 Italy time")
    existing=find_playlist(client)
    if existing is not None:
        if existing.get("is_enabled"):
            raise ValueError("Existing on-air TG playlist cannot be changed by setup")
        print("RDI_TG_EMPTY_PLAYLIST=ALREADY_EXISTS")
        return
    day=now.date().isoformat()
    # A new playlist is disabled: zero songs and no live broadcast.
    client.call("POST","/station/1/playlists",plan_for(day))
    record=find_playlist(client)
    if not record or bool(record.get("is_enabled")) or not verify_schedule(record.get("schedule_items"),day):
        raise RuntimeError("Empty TG playlist setup not persisted safely")
    if int(record.get("num_songs") or 0) != 0:
        raise RuntimeError("New TG playlist was unexpectedly populated")
    print("RDI_TG_EMPTY_PLAYLIST=CREATED_DISABLED")
    print("RDI_TG_EMPTY_PLAYLIST_ID="+str(record["id"]))


def main():
    p=argparse.ArgumentParser()
    p.add_argument("action",choices=["inspect","apply","prepare-disabled"])
    p.add_argument("--manifest")
    p.add_argument("--mp3")
    p.add_argument("--tv")
    p.add_argument("--php-helper",required=True)
    args=p.parse_args()
    if args.action=="apply":
        if not args.manifest or not args.mp3 or not args.tv:
            p.error("Apply needs --manifest, --mp3 and --tv")
        # Fail locally before a short-lived privileged AzuraCast credential exists.
        data,_=validate(Path(args.manifest),Path(args.mp3),Path(args.tv))
        print("EDITION_LOCAL_VALIDATED="+data["edition_id"])
    helper=Path(args.php_helper).read_bytes()
    token=""
    try:
        token=backend.azura_php(helper,"create")
        client=backend.Client(token)
        if args.action=="prepare-disabled":
            prepare_disabled(client)
        elif args.action=="inspect":
            record=find_playlist(client)
            print("RDI_TG_PLAYLIST_EXISTS="+str(bool(record)).lower())
            if record:
                print("RDI_TG_PLAYLIST_ENABLED="+str(record.get("is_enabled")).lower())
                print("RDI_TG_SCHEDULE="+json.dumps(record.get("schedule_items"),ensure_ascii=False))
                print("RDI_TG_MEDIA_COUNT="+str(len(list_own_media(client))))
        else:
            activate(client,Path(args.manifest),Path(args.mp3),Path(args.tv))
    finally:
        if token:
            backend.azura_php(helper,"revoke",token.split(":",1)[0])

if __name__=="__main__":
    main()
