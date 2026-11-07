#!/usr/bin/env python3
"""Safely schedule a single Top3 radio episode on AzuraCast station #1.

Uses the existing temporary privileged AzuraCast API token helper.
Only this dedicated playlist / media folder may be modified.
Existing live FFmpeg, current songs and other playlists are never restarted.
"""
from __future__ import annotations
import argparse, datetime as dt, importlib.util, json, pathlib, re, sqlite3, sys, time
from zoneinfo import ZoneInfo

ROME=ZoneInfo("Europe/Rome")
ROOT=pathlib.Path("/var/lib/rdi-ai-music")
PLAYLIST_NAME="RDI AI MUSIC - TOP 3 del giorno"
MEDIA_DIR="RDI AI MUSIC TOP3"
STATION_ID=1
VALID=re.compile(r"^RDI-AI-TOP3-20\d{6}$")

def helper(path):
    spec=importlib.util.spec_from_file_location("rdi_geopolitica_api",str(path))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def find_playlist(api):
    rows=api.call("GET","/station/1/playlists")
    found=[r for r in rows if r.get("name")==PLAYLIST_NAME]
    if len(found)>1: raise RuntimeError("Duplicate Top3 playlists found; refusing modification")
    return found[0] if found else None

def safe_edition(mp3,manifest):
    data=json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("published") or not data.get("original_audio_authorized"):
        raise ValueError("Invalid or already-published input manifest")
    title=str(data.get("track_title",""))
    if not VALID.fullmatch(title) or mp3.name!=title+".mp3":
        raise ValueError("Top3 file / edition mismatch")
    if data.get("edition_id")!=title:
        raise ValueError("Edition ID mismatch")
    day=dt.datetime.now(ROME).strftime("%Y-%m-%d")
    if data.get("edition_day")!=day or title!="RDI-AI-TOP3-"+day.replace("-",""):
        raise ValueError("Refusing a non-current Top3 edition")
    seg=data.get("segments",[])
    if not isinstance(seg,list) or len(seg)!=3 or [s.get("rank") for s in seg]!=[3,2,1]:
        raise ValueError("Top3 segment ranks must be 3,2,1")
    ids=[x.get("id") for x in seg]
    if len(set(ids))!=3 or any(not re.fullmatch(r"[0-9a-f]{32}",str(x)) for x in ids):
        raise ValueError("Missing or duplicate track ID")
    length=float(data.get("duration_seconds",0))
    if not 200<length<2400:raise ValueError("Unexpected Top3 episode length")
    if not 1024*100 < mp3.stat().st_size < 38*1024*1024:
        raise ValueError("Unexpected Top3 audio size")
    with sqlite3.connect(f"file:{ROOT/'submissions.sqlite3'}?mode=ro",uri=True) as con:
        question=",".join("?" for _ in ids)
        rows=con.execute(f"SELECT id FROM submissions WHERE id IN ({question}) AND status='approved' AND spotlight_consent=1 AND youtube_consent=1 AND stored_name IS NOT NULL",ids).fetchall()
    if len(rows)!=3:raise ValueError("Explicit YouTube broadcasting authorization is required for ALL three songs")
    return data

def schedule(day):
    return [{"start_time":"20:30","end_time":"21:20",
       "start_date":day,"end_date":day,"days":[],
       "loop_once":True}]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["inspect","publish","suspend"])
    parser.add_argument("--mp3",type=pathlib.Path)
    parser.add_argument("--manifest",type=pathlib.Path)
    parser.add_argument("--php-helper",type=pathlib.Path,required=True)
    parser.add_argument("--api-module",type=pathlib.Path,required=True)
    args=parser.parse_args()
    prepared=None
    if args.action=="publish":
        if not args.mp3 or not args.manifest:
            parser.error("--mp3 and --manifest required")
        prepared=safe_edition(args.mp3,args.manifest)
        # Never change a playlist while it could already be on air.
        if dt.datetime.now(ROME).hour>=20:
            raise RuntimeError("Install Top3 before 20:00 Europe/Rome only; refusing disruptive late update")
    lib=helper(args.api_module)
    key=""
    try:
        key=lib.azura_php(args.php_helper.read_bytes(),"create")
        api=lib.Client(key)
        row=find_playlist(api)
        if args.action=="inspect":
            print("TOP3_PLAYLIST_EXISTS="+str(bool(row)).lower())
            if row:
                print("TOP3_PLAYLIST_ENABLED="+str(bool(row.get("is_enabled"))).lower())
                print("TOP3_PLAYLIST_ID="+str(row["id"]))
            return
        if args.action=="suspend":
            if row and row.get("is_enabled"):
                api.call("PUT","/station/1/playlist/"+str(int(row["id"])),{"is_enabled":False})
            print("TOP3_PLAYLIST_SUSPENDED=true")
            return
        relative=MEDIA_DIR+"/"+args.mp3.name
        station=api.call("GET","/station/1/profile")
        tz=station.get("timezone") if isinstance(station,dict) else None
        if tz and tz!="Europe/Rome":
            raise RuntimeError("Station timezone differs from Europe/Rome; refusing a mis-timed schedule")
        media=api.call("GET","/station/1/files")
        ours=[m for m in media if str(m.get("path","")).startswith(MEDIA_DIR+"/")]
        if not any(m.get("path")==relative for m in ours):
            import base64
            api.call("POST","/station/1/files",{
                "path":relative,"file":base64.b64encode(args.mp3.read_bytes()).decode("ascii")
            })
            for _ in range(18):
                time.sleep(3)
                media=api.call("GET","/station/1/files")
                ours=[m for m in media if str(m.get("path","")).startswith(MEDIA_DIR+"/")]
                if any(m.get("path")==relative for m in ours):break
            else:raise RuntimeError("Top3 media was not indexed by AzuraCast")
        day=prepared["edition_day"]
        fields={"name":PLAYLIST_NAME,
          "description":"Puntata con annunci 3,2,1 e file autorizzati, automatica ogni sera",
          "type":"once_per_hour","source":"songs","order":"sequential",
          "is_enabled":False,"play_per_hour_minute":30,
          "include_in_requests":False,"include_in_on_demand":False,
          "avoid_duplicates":False,"weight":8,
          "backend_options":["single_track"],
          "schedule_items":schedule(day)}
        if row:
            if row.get("type")!="once_per_hour" or int(row.get("play_per_hour_minute",-1))!=30:
                raise ValueError("Existing Top3 playlist has unexpected configuration")
            # Prevent an old program from playing while this new edition is prepared.
            api.call("PUT","/station/1/playlist/"+str(int(row["id"])),
                     {"is_enabled":False, "schedule_items":schedule(day)})
            row=find_playlist(api)
        else:
            api.call("POST","/station/1/playlists",fields)
            row=find_playlist(api)
            if not row: raise RuntimeError("Top3 playlist create not visible")
        playlist_id=int(row["id"])
        detail=api.call("GET",f"/station/1/playlist/{playlist_id}")
        items=detail.get("schedule_items") if isinstance(detail,dict) else None
        if not items:
            raise RuntimeError("Schedule did not persist; playlist left disabled")
        # AzuraCast returns the station's schedule with canonical timezone
        # representations, which can differ from the HH:MM input format.
        print("TOP3_STATION_SCHEDULE="+json.dumps(items,ensure_ascii=False,default=str)[:3000])
        if not any(
            day in str(item.get("start_date","")) and
            ("20:30" in str(item.get("start_time","")) or
             str(item.get("start_time","")) in ("73800","73800.0"))
            for item in items
        ):
            raise RuntimeError("Unexpected Top3 broadcast schedule; playlist left disabled")
        api.call("PUT","/station/1/files/batch",{
          "do":"playlist","playlists":[playlist_id],"files":[relative],"dirs":[]})
        # Never erase another station playlist, and never delete still-playing files.
        for existing in ours:
            path=str(existing.get("path",""))
            if path!=relative and path.startswith(MEDIA_DIR+"/"):
                api.call("PUT","/station/1/files/batch",{
                  "do":"playlist","playlists":[],"files":[path],"dirs":[]})
        api.call("PUT",f"/station/1/playlist/{playlist_id}",{"is_enabled":True})
        current=find_playlist(api)
        if not current or not current.get("is_enabled"):
            raise RuntimeError("Top3 playlist was not enabled")
        current_dir=ROOT/"top3";current_dir.mkdir(parents=True,exist_ok=True)
        prepared["published"]=True
        destination=current_dir/"current.json"
        pending=current_dir/".current.tmp"
        pending.write_text(json.dumps(prepared,ensure_ascii=False,indent=2),encoding="utf-8")
        pending.chmod(0o644);pending.replace(destination)
        print("RDI_TOP3_SCHEDULED=true")
        print("PLAYLIST_ID="+str(playlist_id))
        print("DATE="+day+" TIME=20:30 Europe/Rome")
        print("EPISODE_TITLE="+prepared["track_title"])
    finally:
        if key:lib.azura_php(args.php_helper.read_bytes(),"revoke",key.split(":",1)[0])

if __name__=="__main__":
    main()
