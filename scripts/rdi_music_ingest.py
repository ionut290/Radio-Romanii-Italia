#!/usr/bin/env python3
"""RDI live AzuraCast media index + bounded ingestion of NEW music.

Reads only the station's real music volume, writes only the PRIVATE SQLite DJ
cache. It does NOT contact AzuraCast HTTP, does not create or edit playlists,
and cannot change broadcast. The live index is authoritative for availability.

A run atomically reconciles existing files and then analyzes a few newly
uploaded files. It can be repeated frequently and is resumable.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from zoneinfo import ZoneInfo

sys.path.insert(0,str(Path(__file__).resolve().parent))
import rdi_music_dj as dj
import rdi_music_scan as scan

DB = Path.home() / "rdi-music" / "music.db"
AUDIO_EXTENSIONS = {".mp3",".wav",".flac",".m4a",".ogg",".aac"}
MAX_LIBRARY_ENTRIES = 60000
MAX_OUTPUT_BYTES = 35_000_000


def inventory() -> list[tuple[str,int,float]]:
    # Root-owned Docker volume, but the only command is read-only find.
    cmd=["sudo","-n","find",scan.MEDIA,"-type","f",
         "-printf","%p\\0%s\\0%T@\\0"]
    proc=subprocess.run(cmd,capture_output=True,timeout=120,check=True)
    data=proc.stdout
    if len(data)>MAX_OUTPUT_BYTES:
        raise RuntimeError("Station music inventory unexpectedly large")
    fields=data.split(b"\0")
    if fields[-1]!=b"":
        raise RuntimeError("Invalid NUL-terminated inventory")
    fields.pop()
    if len(fields)%3:
        raise RuntimeError("Incomplete station inventory")
    result=[]
    prefix=str(Path(scan.MEDIA))+"/"
    for i in range(0,len(fields),3):
        path=fields[i].decode("utf-8","surrogateescape")
        if not path.startswith(prefix):
            continue
        if Path(path).suffix.lower() not in AUDIO_EXTENSIONS or dj.excluded(path):
            continue
        try:
            size=int(fields[i+1])
            stamp=float(fields[i+2])
        except ValueError:
            continue
        if size<20000 or not math.isfinite(stamp):
            continue
        result.append((path,size,stamp))
    if len(result)>MAX_LIBRARY_ENTRIES:
        raise RuntimeError("Too many station files for safe snapshot")
    return result


def ensure(db: sqlite3.Connection):
    db.execute("""CREATE TABLE IF NOT EXISTS track_live_index(
        path TEXT PRIMARY KEY, size INTEGER NOT NULL, modified REAL NOT NULL,
        duration_seconds REAL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_live_seen ON track_live_index(last_seen)")
    db.execute("""CREATE TABLE IF NOT EXISTS tracks(
        path TEXT PRIMARY KEY,size INTEGER,modified REAL,rms REAL,peak REAL,
        category TEXT,analyzed_at TEXT
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS track_tags(
        path TEXT PRIMARY KEY,size INTEGER,modified REAL,
        genre TEXT,title TEXT,artist TEXT,analyzed_at TEXT
    )""")
    db.commit()


def reconcile(db: sqlite3.Connection, files:list[tuple[str,int,float]]) -> dict:
    if not files:
        # Never erase the last known state if find unexpectedly returns empty.
        raise RuntimeError("Empty live AzuraCast volume: refusing to update inventory")
    ensure(db)
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    with db:
        old_count=db.execute("SELECT COUNT(*) FROM track_live_index").fetchone()[0]
        first_seen=now if old_count else "1970-01-01T00:00:00+00:00"
        db.executemany("""INSERT INTO track_live_index(
            path,size,modified,duration_seconds,first_seen,last_seen
        ) VALUES(?,?,?,NULL,?,?)
        ON CONFLICT(path) DO UPDATE SET
            duration_seconds=CASE WHEN size=excluded.size
                 AND abs(modified-excluded.modified)<2
                 THEN duration_seconds ELSE NULL END,
            size=excluded.size,modified=excluded.modified,last_seen=excluded.last_seen""",
            ((path,size,modified,first_seen,now) for path,size,modified in files))
        # Remove ONLY entries from the *live availability* view. Preserve every
        # historic audio/AI analysis in its own separate table for auditing.
        gone=db.execute("DELETE FROM track_live_index WHERE last_seen!=?",(now,)).rowcount
        new=max(0,len(files)-(old_count-gone))
    return {"live_total":len(files),"no_longer_present":gone,"newly_visible":new}


def media_details(path:str) -> tuple[float,str,str,str]:
    proc=subprocess.run(
        ["sudo","-n","ffprobe","-v","error",
         "-show_entries","format=duration:format_tags=title,artist,genre",
         "-of","json",path],
        capture_output=True,text=True,timeout=20,check=True)
    data=json.loads(proc.stdout[:250_000])
    duration=float(data.get("format",{}).get("duration",0))
    if not math.isfinite(duration) or not 60<=duration<=720:
        raise ValueError("Music duration missing or outside expected range")
    tags={str(k).lower():str(v) for k,v in
          (data.get("format",{}).get("tags") or {}).items()}
    return duration,tags.get("genre","")[:120],tags.get("title","")[:200],tags.get("artist","")[:200]


def analyze_new(db: sqlite3.Connection, limit:int) -> tuple[int,int]:
    # Fast new song first: mtime DESC prioritizes freshly uploaded media.
    candidates=db.execute("""SELECT l.path,l.size,l.modified,l.duration_seconds
        FROM track_live_index l LEFT JOIN tracks t ON l.path=t.path
        WHERE t.path IS NULL OR t.size!=l.size OR abs(t.modified-l.modified)>2
        ORDER BY l.modified DESC LIMIT ?""",(max(limit*5,20),)).fetchall()
    success=0
    failure=0
    for path,size,modified,_ in candidates:
        if success>=limit or failure>=max(12,limit*3):
            break
        try:
            duration,genre,title,artist=media_details(path)
            rms,peak=scan.analyze(path)
            timestamp=dt.datetime.now(dt.timezone.utc).isoformat()
            with db:
                db.execute("""INSERT INTO tracks VALUES(?,?,?,?,?,?,?)
                    ON CONFLICT(path) DO UPDATE SET
                     size=excluded.size,modified=excluded.modified,rms=excluded.rms,
                     peak=excluded.peak,category=excluded.category,
                     analyzed_at=excluded.analyzed_at""",
                     (path,size,modified,rms,peak,"da_verificare",timestamp))
                db.execute("""INSERT INTO track_tags VALUES(?,?,?,?,?,?,?)
                     ON CONFLICT(path) DO UPDATE SET
                      size=excluded.size,modified=excluded.modified,
                      genre=excluded.genre,title=excluded.title,artist=excluded.artist,
                      analyzed_at=excluded.analyzed_at""",
                     (path,size,modified,genre,title,artist,timestamp))
                db.execute("""UPDATE track_live_index
                    SET duration_seconds=?
                    WHERE path=? AND size=? AND abs(modified-?)<2""",
                    (duration,path,size,modified))
            success+=1
        except (OSError,ValueError,TypeError,subprocess.SubprocessError):
            failure+=1
    return success,failure


def probe_missing_durations(db: sqlite3.Connection, limit: int) -> tuple[int,int]:
    # Existing music indexed before this module was created.
    rows=db.execute("""SELECT l.path,l.size,l.modified
        FROM track_live_index l
        INNER JOIN tracks t ON t.path=l.path AND t.size=l.size
        AND abs(t.modified-l.modified)<2
        WHERE l.duration_seconds IS NULL
        ORDER BY l.modified DESC LIMIT ?""",(max(limit*3,15),)).fetchall()
    done=0
    failed=0
    for path,size,modified in rows:
        if done>=limit or failed>=limit*3:
            break
        try:
            duration,genre,title,artist=media_details(path)
            now=dt.datetime.now(dt.timezone.utc).isoformat()
            with db:
                db.execute("""UPDATE track_live_index
                    SET duration_seconds=? WHERE path=? AND size=?
                        AND abs(modified-?)<2""",(duration,path,size,modified))
                db.execute("""INSERT INTO track_tags VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(path) DO UPDATE SET
                     size=excluded.size,modified=excluded.modified,
                     genre=excluded.genre,title=excluded.title,
                     artist=excluded.artist,analyzed_at=excluded.analyzed_at""",
                   (path,size,modified,genre,title,artist,now))
            done+=1
        except (OSError,ValueError,subprocess.SubprocessError):
            failed+=1
    return done,failed


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--new-limit",type=int,default=4)
    p.add_argument("--duration-limit",type=int,default=10)
    args=p.parse_args()
    DB.parent.mkdir(parents=True,exist_ok=True)
    files=inventory()
    db=sqlite3.connect(DB,timeout=35)
    try:
        changes=reconcile(db,files)
        added,fail=analyze_new(db,max(0,min(args.new_limit,12)))
        measured,duration_fail=probe_missing_durations(db,max(0,min(args.duration_limit,25)))
        valid=db.execute("""SELECT COUNT(*) FROM track_live_index l JOIN tracks t
           ON t.path=l.path AND t.size=l.size AND abs(t.modified-l.modified)<2
           WHERE l.duration_seconds>=60 AND l.duration_seconds<=720""").fetchone()[0]
        # Printed summary has no paths, account IDs or artist names.
        print("RDI_NEW_MUSIC_LIVE_FILES="+str(changes["live_total"]))
        print("RDI_NEW_MUSIC_NEWLY_VISIBLE="+str(changes["newly_visible"]))
        print("RDI_NEW_MUSIC_MISSING="+str(changes["no_longer_present"]))
        print("RDI_NEW_MUSIC_ANALYZED="+str(added))
        print("RDI_NEW_MUSIC_ANALYSIS_ERRORS="+str(fail))
        print("RDI_NEW_MUSIC_DURATIONS_MEASURED="+str(measured))
        print("RDI_NEW_MUSIC_DURATIONS_FAILED="+str(duration_fail))
        print("RDI_NEW_MUSIC_READY_WITH_DURATION="+str(valid))
        print("RDI_MUSIC_INGEST_RADIO_PLAYLIST_WRITES=0")
    finally:
        db.close()

if __name__=="__main__":
    main()
