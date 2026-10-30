#!/usr/bin/env python3
"""Repair only disabled RDI hourly playlist 31 midnight rollover.

Never enables playlists, changes memberships, deletes music or restarts radio.
"""
import argparse, json, sys
from pathlib import Path
sys.path.insert(0,"/opt/rdi-music-dj")
import rdi_music_azuracast_sync as sync

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--php-helper",required=True)
    args=p.parse_args()
    helper=Path(args.php_helper).read_bytes()
    token=""
    try:
        token=sync.backend.azura_php(helper,"create")
        c=sync.backend.Client(token)
        def get():
            rows=c.call("GET","/station/1/playlists")
            return {int(x["id"]):x for x in rows if isinstance(x,dict)}
        d=get()
        if not d.get(25,{}).get("is_enabled"):
            raise RuntimeError("Fallback #25 not active")
        row=d.get(31)
        if not row or row.get("name")!="RDI fascia late_21_24" or row.get("is_enabled"):
            raise RuntimeError("Playlist 31 missing, renamed or enabled")
        sched=row.get("schedule_items")
        if not isinstance(sched,list) or len(sched)!=1:
            raise RuntimeError("Unexpected playlist 31 schedule")
        item=sched[0]
        if item.get("start_time")!=21 or item.get("end_time") not in (23,0):
            raise RuntimeError("Unexpected starting schedule, refusing write")
        if item.get("end_time")==0:
            print("RDI_MIDNIGHT_ALREADY_CORRECT=true")
            return
        # API accepts HH:MM input. 00:00 the next day is a supported
        # overnight interval, unlike 23:59 which this version truncated.
        new=[{"start_time":"21:00","end_time":"00:00","days":[],"loop_once":False}]
        try:
            c.call("PUT","/station/1/playlist/31",
                   {"schedule_items":new,"is_enabled":False})
            latest=get()[31]
            sch=latest.get("schedule_items") or []
            if len(sch)!=1 or sch[0].get("start_time")!=21 or sch[0].get("end_time")!=0 or latest.get("is_enabled"):
                raise RuntimeError("Midnight schedule not persisted as 21->0")
        except Exception:
            # Restore exact original full schedule when repair not persisted.
            try:
                c.call("PUT","/station/1/playlist/31",
                       {"schedule_items":[{"start_time":"21:00","end_time":"23:00","days":[],"loop_once":False}],
                        "is_enabled":False})
            except Exception:
                pass
            raise
        print("RDI_PLAYLIST_31_MIDNIGHT_FIXED=true")
        print("RDI_PLAYLIST_31_ENABLED=false")
    finally:
        if token:sync.backend.azura_php(helper,"revoke",token.split(":",1)[0])
if __name__=="__main__":main()
