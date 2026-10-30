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
import rdi_music_rhythm as rhythm
import re

DB = Path.home() / "rdi-music" / "music.db"
AUDIO_EXTENSIONS = {".mp3",".wav",".flac",".m4a",".ogg",".aac"}
MAX_LIBRARY_ENTRIES = 60000
MAX_OUTPUT_BYTES = 35_000_000


def inventory() -> list[tuple[str,int,float]]:
    # Reuse EXACTLY the existing, verified Oracle sudo command:
    # sudo -n find MEDIA -type f -print0. The sudo policy may deny -printf.
    result=[]
    try:
        files=list(scan.inventory())
    except subprocess.CalledProcessError as exc:
        details=(exc.stderr or b"").decode("utf-8","replace").lower()
        flags={
          "sudo_failure": "sudo:" in details,
          "password_required": "password" in details,
          "permission_denied": "permission" in details or "not permitted" in details,
          "path_missing": "no such file" in details or "cannot access" in details,
          "systemd_restricted": "setuid" in details or "effective uid" in details,
        }
        print("RDI_INGEST_READ_ERROR_FLAGS="+json.dumps(flags),file=sys.stderr)
        raise RuntimeError("Oracle systemd cannot access read-only music directory") from None
    if not files:
        raise RuntimeError("Empty station library; no live inventory overwrite")
    if len(files)>MAX_LIBRARY_ENTRIES:
        raise RuntimeError("Too many music files for safe snapshot")
    for path in files:
        if Path(path).suffix.lower() not in AUDIO_EXTENSIONS or dj.excluded(path):
            continue
        try:
            prefix=[] if os.geteuid()==0 else ["sudo","-n"]
            stat=subprocess.run(
                prefix+["stat","-c","%s %Y","--",path],
                capture_output=True,text=True,timeout=10,check=False)
            if stat.returncode:
                continue
            fields=stat.stdout.strip().split()
            if len(fields)!=2:
                continue
            size=int(fields[0])
            modified=float(fields[1])
            if size<20000 or not math.isfinite(modified):
                continue
            result.append((path,size,modified))
        except (OSError,ValueError,subprocess.TimeoutExpired):
            continue
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
    prefix=[] if os.geteuid()==0 else ["sudo","-n"]
    proc=subprocess.run(
        prefix+["ffprobe","-v","error",
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


def measure_loudness(path):
    prefix=[] if os.geteuid()==0 else ["sudo","-n"]
    cmd=prefix+["nice","-n","15","ffmpeg","-nostdin",
         "-hide_banner","-nostats","-threads","1","-t","30",
         "-i",path,"-af","ebur128=peak=true","-f","null","-"]
    proc=subprocess.run(cmd,capture_output=True,text=True,timeout=80,check=True)
    summary=proc.stderr.rsplit("Summary:",1)[-1]
    loud=re.search(r"I:\s*(-?[0-9.]+) LUFS",summary)
    spread=re.search(r"LRA:\s*([0-9.]+) LU",summary)
    if not loud or not spread:
        raise ValueError("LUFS and dynamic measurements not available")
    return float(loud.group(1)),float(spread.group(1))

def feature_tables(db):
    db.execute("""CREATE TABLE IF NOT EXISTS track_features (
      path TEXT PRIMARY KEY,size INTEGER,modified REAL,
      integrated_lufs REAL,loudness_range REAL,rms_db REAL,
      peak_db REAL,analyzed_at TEXT)""")
    db.execute("""CREATE TABLE IF NOT EXISTS track_rhythm (
      path TEXT PRIMARY KEY,size INTEGER,modified REAL,
      bpm_candidate REAL,beat_score REAL,energy_variation REAL,
      analyzed_at TEXT)""")
    db.commit()

def complete_audio(db,path,size,modified):
    # New files are eligible only after BOTH rhythm and loudness succeeded.
    bpm,beat,variation=rhythm.estimate(path)
    lufs,spread=measure_loudness(path)
    if bpm is None or beat<0.32:
        return False
    rms,peak=db.execute("SELECT rms,peak FROM tracks WHERE path=?",(path,)).fetchone()
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    with db:
        db.execute("""INSERT INTO track_rhythm VALUES(?,?,?,?,?,?,?)
           ON CONFLICT(path) DO UPDATE SET size=excluded.size,modified=excluded.modified,
             bpm_candidate=excluded.bpm_candidate,beat_score=excluded.beat_score,
             energy_variation=excluded.energy_variation,
             analyzed_at=excluded.analyzed_at""",
           (path,size,modified,bpm,beat,variation,now))
        db.execute("""INSERT INTO track_features VALUES(?,?,?,?,?,?,?,?)
           ON CONFLICT(path) DO UPDATE SET size=excluded.size,modified=excluded.modified,
             integrated_lufs=excluded.integrated_lufs,
             loudness_range=excluded.loudness_range,rms_db=excluded.rms_db,
             peak_db=excluded.peak_db,analyzed_at=excluded.analyzed_at""",
           (path,size,modified,lufs,spread,rms,peak,now))
    return True


def analyze_new(db: sqlite3.Connection, limit:int) -> tuple[int,int,int]:
    # Fast new song first: mtime DESC prioritizes freshly uploaded media.
    candidates=db.execute("""SELECT l.path,l.size,l.modified,l.duration_seconds
        FROM track_live_index l LEFT JOIN tracks t ON l.path=t.path
        WHERE t.path IS NULL OR t.size!=l.size OR abs(t.modified-l.modified)>2
        ORDER BY l.modified DESC LIMIT ?""",(max(limit*5,20),)).fetchall()
    success=0
    failure=0
    ready=0
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
            try:
                if complete_audio(db,path,size,modified):
                    ready+=1
            except (OSError,ValueError,TypeError,subprocess.SubprocessError):
                # Music stays in inventory but never enters playable bank
                # until rhythm and loudness succeed on a subsequent cycle.
                failure+=1
        except (OSError,ValueError,TypeError,subprocess.SubprocessError):
            failure+=1
    return success,failure,ready


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
    p.add_argument("--duration-limit",type=int,default=12)
    p.add_argument("--feature-limit",type=int,default=2)
    args=p.parse_args()
    DB.parent.mkdir(parents=True,exist_ok=True)
    files=inventory()
    db=sqlite3.connect(DB,timeout=35)
    try:
        changes=reconcile(db,files)
        feature_tables(db)
        added,fail,new_ready=analyze_new(db,max(0,min(args.new_limit,12)))
        measured,duration_fail=probe_missing_durations(db,max(0,min(args.duration_limit,25)))
        # Backfill audio features for already inventoried, valid on-disk
        # tracks. This includes new uploads that failed on a prior cycle.
        pending=db.execute("""SELECT l.path,l.size,l.modified
            FROM track_live_index l JOIN tracks t ON t.path=l.path
              AND t.size=l.size AND abs(t.modified-l.modified)<2
            LEFT JOIN track_rhythm r ON r.path=l.path AND r.size=l.size
              AND abs(r.modified-l.modified)<2
            LEFT JOIN track_features f ON f.path=l.path AND f.size=l.size
              AND abs(f.modified-l.modified)<2
            WHERE l.duration_seconds BETWEEN 60 AND 720
              AND (r.path IS NULL OR f.path IS NULL)
            ORDER BY l.modified DESC LIMIT ?""",
            (max(8,args.feature_limit*4),)).fetchall()
        backfilled=0
        for path,size,modified in pending:
            if backfilled >= max(0,min(args.feature_limit,6)):
                break
            try:
                if complete_audio(db,path,size,modified):
                    backfilled+=1
            except (OSError,ValueError,TypeError,subprocess.SubprocessError):
                pass
        valid=db.execute("""SELECT COUNT(*) FROM track_live_index l JOIN tracks t
           ON t.path=l.path AND t.size=l.size AND abs(t.modified-l.modified)<2
           WHERE l.duration_seconds>=60 AND l.duration_seconds<=720""").fetchone()[0]
        # Printed summary has no paths, account IDs or artist names.
        print("RDI_NEW_MUSIC_LIVE_FILES="+str(changes["live_total"]))
        print("RDI_NEW_MUSIC_NEWLY_VISIBLE="+str(changes["newly_visible"]))
        print("RDI_NEW_MUSIC_MISSING="+str(changes["no_longer_present"]))
        print("RDI_NEW_MUSIC_ANALYZED="+str(added))
        print("RDI_NEW_MUSIC_ANALYSIS_ERRORS="+str(fail))
        print("RDI_NEW_MUSIC_FULLY_ANALYZED="+str(new_ready+backfilled))
        print("RDI_NEW_MUSIC_DURATIONS_MEASURED="+str(measured))
        print("RDI_NEW_MUSIC_DURATIONS_FAILED="+str(duration_fail))
        print("RDI_NEW_MUSIC_READY_WITH_DURATION="+str(valid))
        print("RDI_MUSIC_INGEST_RADIO_PLAYLIST_WRITES=0")
    finally:
        db.close()

if __name__=="__main__":
    main()
