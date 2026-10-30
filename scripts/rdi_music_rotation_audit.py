#!/usr/bin/env python3
"""Read-only reality check of RDI DJ shadow rotation against actual station media.

No AzuraCast API and never edits any media, stations, playlists or scheduling.
Compares the simulator's 24h proposed track IDs to real on-disk file stats
and ffprobe duration. Prints AGGREGATE counts only; no filenames/metadata/keys.
"""
from __future__ import annotations
import collections
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
import rdi_music_dj as dj
from rdi_music_rotation import simulate

DB=Path("/home/ubuntu/rdi-music/music.db")
SAMPLE_LIMIT=450

def path_id(path: str) -> str:
    return hashlib.sha256(path.encode("utf-8","surrogateescape")).hexdigest()[:16]

def probe_duration(path: str):
    try:
        proc=subprocess.run(["nice","-n","15","ffprobe","-nostdin","-v","error",
                  "-show_entries","format=duration","-of","default=noprint_wrappers=1:nokey=1",
                  path],capture_output=True,text=True,timeout=13,check=False)
        if proc.returncode:
            return None
        seconds=float(proc.stdout.strip())
        if not math.isfinite(seconds) or not 60 <= seconds <= 720:
            return None
        return seconds
    except (OSError,ValueError,subprocess.TimeoutExpired):
        return None

def inspect(day="2026-10-30"):
    dj.DB=DB
    catalog=dj.report()
    plan=simulate(catalog,day)
    requested=[(block["id"],song["id"]) for block in plan["blocks"]
               for song in block["brani"]]
    if len(requested)>SAMPLE_LIMIT:
        raise RuntimeError("Audit over per-day limit")
    con=sqlite3.connect(f"file:{DB}?mode=ro",uri=True)
    try:
        entries=con.execute("SELECT path,size,modified FROM tracks").fetchall()
    finally:
        con.close()
    indexed={path_id(p):(p,sz,mtime) for p,sz,mtime in entries}
    counts=collections.Counter()
    durations=collections.defaultdict(float)
    tested=[]
    for block,ident in requested:
        data=indexed.get(ident)
        if data is None:
            counts["not_in_inventory"]+=1
            continue
        path,stored_size,stored_mtime=data
        try:
            st=os.stat(path)
        except OSError:
            counts["missing_or_unreadable"]+=1
            continue
        counts["readable"]+=1
        if st.st_size!=stored_size or abs(st.st_mtime-stored_mtime)>2:
            counts["inventory_needs_refresh"]+=1
        duration=probe_duration(path)
        if duration is None:
            counts["invalid_or_unavailable_duration"]+=1
            continue
        counts["duration_ok"]+=1
        durations[block]+=duration
        tested.append(duration)
    block_summary={}
    for block in plan["blocks"]:
        actual=durations[block["id"]]/60
        target=block["minuti"]
        block_summary[block["id"]]={
            "target_minutes":target,
            "known_duration_minutes":round(actual,1),
            "estimated_shortfall_minutes":round(max(0,target-actual),1),
            "playlist_coverage_estimate_percent":round(min(100,actual/target*100),1)
        }
    enough=(counts["duration_ok"]==len(requested) and
        all(x["estimated_shortfall_minutes"]<=3.5 for x in block_summary.values()))
    result={
        "schema_version":1,"kind":"rdi-dj-rotation-reality-audit",
        "read_only":True,"playlist_writes":0,"ready_for_live":False,
        "date":day,"planned_tracks":len(requested),
        "readable_on_disk":counts["readable"],
        "missing_or_unreadable":counts["missing_or_unreadable"],
        "inventory_mismatches":counts["inventory_needs_refresh"],
        "valid_real_durations":counts["duration_ok"],
        "invalid_durations":counts["invalid_or_unavailable_duration"],
        "actual_total_audio_minutes":round(sum(tested)/60,1),
        "block_durations":block_summary,
        "real_files_support_draft":enough,
        "warnings":[
            "Il piano non e' stato pubblicato o programmato in AzuraCast.",
            "Gli orari restano orientativi finche' durata reale e appuntamenti editoriali non sono integrati.",
            "I generi musicali IA non sono ancora convalidati da ascolto umano.",
        ]
    }
    return result

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--date",required=True)
    a=p.parse_args()
    result=inspect(a.date)
    # Safe aggregation: no song titles or local file paths disclosed.
    print("RDI_ROTATION_REALITY="+json.dumps(result,ensure_ascii=False,sort_keys=True))
