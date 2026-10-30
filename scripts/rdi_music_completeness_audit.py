#!/usr/bin/env python3
"""Private RDI catalog completeness audit. Prints aggregate stats only.

No station actions, no paths or titles are printed.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
import sqlite3
import sys
from zoneinfo import ZoneInfo
sys.path.insert(0,"/opt/rdi-music-dj")
import rdi_music_dj as dj
from rdi_music_rotation import simulate

dbpath=Path.home()/"rdi-music"/"music.db"
db=sqlite3.connect("file:"+str(dbpath)+"?mode=ro",uri=True)
exists={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
data={}
if "track_live_index" in exists:
    data["live_index"]=db.execute("SELECT COUNT(*) FROM track_live_index").fetchone()[0]
    data["duration_verified"]=db.execute("SELECT COUNT(*) FROM track_live_index WHERE duration_seconds BETWEEN 60 AND 720").fetchone()[0]
    data["unmeasured"]=db.execute("SELECT COUNT(*) FROM track_live_index WHERE duration_seconds IS NULL").fetchone()[0]
    data["matching_tracks"]=db.execute("""SELECT COUNT(*) FROM track_live_index l
        JOIN tracks t ON l.path=t.path AND l.size=t.size AND abs(l.modified-t.modified)<2
        WHERE l.duration_seconds BETWEEN 60 AND 720""").fetchone()[0]
    if "track_metadata_failures" in exists:
        data["metadata_error_files"]=db.execute("SELECT COUNT(*) FROM track_metadata_failures").fetchone()[0]
    else:data["metadata_error_files"]=0
    data["last_scan"]=db.execute("SELECT MAX(last_seen) FROM track_live_index").fetchone()[0]
else:
    data.update({"live_index":0,"duration_verified":0,"unmeasured":0,"matching_tracks":0,"metadata_error_files":0,"last_scan":None})
db.close()
dj.DB=dbpath
rep=dj.report()
today=dt.datetime.now(ZoneInfo("Europe/Rome")).date()
a=simulate(rep,today.isoformat())
b=simulate(rep,(today+dt.timedelta(days=1)).isoformat())
first=lambda p:[s["id"] for block in p["blocks"] for s in block["brani"]]
ids_today=first(a)
ids_tomorrow=first(b)
data.update({
  "report_tracks":rep["total_music"],
  "catalogue_bank":a["pool_tracks_total"],
  "rotation_ready":a["pool_ready_for_rotation"],
  "waiting_audio_features":a["pool_waiting_for_analysis"],
  "planned_today":len(ids_today),
  "planned_tomorrow":len(ids_tomorrow),
  "new_in_tomorrow":len(set(ids_tomorrow)-set(ids_today)),
  "day_order_changes":ids_today!=ids_tomorrow,
  "duplicate_audio_file_ids_today":len(ids_today)-len(set(ids_today)),
  "live_index_verified":rep["live_index_verified"],
  "playlist_writes":0,
  "automatic_broadcast_enabled":False,
  "ready_for_live":False,
})
print("RDI_MUSIC_COMPLETENESS="+json.dumps(data,ensure_ascii=False,sort_keys=True))
