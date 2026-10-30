#!/usr/bin/env python3
"""Activate RDI's six pre-staged hourly playlists only after strict API checks.

Does not touch playlist 25, music memberships, other playlists or broadcasting.
Automatic rollback disables only playlists newly enabled during this run.
"""
import argparse, json, sys
from pathlib import Path
ROOT=Path("/opt/rdi-music-dj")
sys.path.insert(0,str(ROOT))
import rdi_music_azuracast_sync as sync

EXPECTED=[(26,"night_00_07","00:00","07:00",294),
 (27,"morning_07_10","07:00","10:00",294),
 (28,"day_10_13","10:00","13:00",729),
 (29,"afternoon_13_18","13:00","18:00",729),
 (30,"evening_18_21","18:00","21:00",294),
 (31,"late_21_24","21:00","24:00",294)]

def clock(value):
    """AzuraCast can represent schedule times as fractional hours."""
    if isinstance(value,bool):return None
    if isinstance(value,(int,float)):
        minutes=round(float(value)*60)
        if minutes<0 or minutes>1440:return None
        return f"{minutes//60:02d}:{minutes%60:02d}"
    if isinstance(value,str):
        if len(value)>=5 and value[2]==":":
            return value[:5]
        try:return clock(float(value))
        except ValueError:return None
    return None

def run(client, apply):
    rows=client.call("GET","/station/1/playlists")
    if not isinstance(rows,list):raise RuntimeError("Invalid playlist API")
    byid={int(x["id"]):x for x in rows if isinstance(x,dict) and str(x.get("id","")).isdigit()}
    main=byid.get(25)
    if not main or main.get("name")!=sync.NAME or not main.get("is_enabled"):
        raise RuntimeError("Main fallback playlist 25 not healthy")
    if len(rows)<7:raise RuntimeError("Playlist list unexpectedly short")
    for pid,suffix,start,end,minimum in EXPECTED:
        p=byid.get(pid)
        if not p or p.get("name")!="RDI fascia "+suffix:
            raise RuntimeError("Unexpected playlist ID/name "+str(pid))
        if p.get("type")!="default" or p.get("source")!="songs" or p.get("is_jingle"):
            raise RuntimeError("Unexpected playlist type "+str(pid))
        if p.get("order")!="shuffle":
            raise RuntimeError("Playlist not shuffle "+str(pid))
        sch=p.get("schedule_items")
        if not isinstance(sch,list) or len(sch)!=1:
            raise RuntimeError("Schedule missing/ambiguous "+str(pid))
        item=sch[0]
        if not isinstance(item,dict) or clock(item.get("start_time"))!=start or clock(item.get("end_time"))!=(("23:59") if end=="24:00" else end):
            raise RuntimeError("Actual schedule differs "+str(pid)+": "+repr(sch))
        # Empty days is the expected all-days scheduling created by staging.
        if item.get("days") not in ([],None):
            raise RuntimeError("Non-daily schedule "+str(pid))
        if p.get("num_songs") is not None and int(p["num_songs"])<minimum:
            raise RuntimeError("Song count below prepared size "+str(pid))
    print("RDI_HOURLY_PRECHECK=PASS 6/6",flush=True)
    if not apply:
        print("RDI_HOURLY_WRITE=0",flush=True)
        return
    changed=[]
    try:
        for pid,_,_,_,_ in EXPECTED:
            p=byid[pid]
            if not p.get("is_enabled"):
                # List before request for idempotency and rollback.
                changed.append(pid)
                client.call("PUT",f"/station/1/playlist/{pid}",{"is_enabled":True})
            latest=client.call("GET","/station/1/playlists")
            verified=next((x for x in latest if int(x.get("id",0))==pid),None)
            if not verified or not verified.get("is_enabled"):
                raise RuntimeError("Enable not persisted "+str(pid))
            print("RDI_HOURLY_ENABLED="+str(pid),flush=True)
        rows=client.call("GET","/station/1/playlists")
        if not next((x for x in rows if int(x.get("id",0))==25),{}).get("is_enabled"):
            raise RuntimeError("Fallback playlist disabled unexpectedly")
        print("RDI_HOURLY_ACTIVATED_6=true",flush=True)
    except Exception:
        for pid in reversed(changed):
            try:client.call("PUT",f"/station/1/playlist/{pid}",{"is_enabled":False})
            except Exception:pass
        print("RDI_HOURLY_ROLLBACK_ATTEMPTED=true",flush=True)
        raise

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    p.add_argument("--php-helper",required=True)
    a=p.parse_args()
    token=""
    try:
        token=sync.backend.azura_php(Path(a.php_helper).read_bytes(),"create")
        run(sync.backend.Client(token),a.apply)
    finally:
        if token:sync.backend.azura_php(Path(a.php_helper).read_bytes(),"revoke",token.split(":",1)[0])
if __name__=="__main__":main()
