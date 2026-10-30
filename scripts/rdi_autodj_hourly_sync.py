#!/usr/bin/env python3
"""Synchronize new verified tracks into existing RDI hourly AzuraCast playlists.

Default audit mode is read-only. --apply adds only missing memberships, never
removes any membership, disables a playlist, changes schedule, or restarts radio.
Uses existing guarded snapshot/rollback methods and station-wide lock externally.
"""
import argparse, collections, json, sys
from pathlib import Path
ROOT=Path("/opt/rdi-music-dj")
sys.path.insert(0,str(ROOT))
import rdi_music_azuracast_sync as sync
import rdi_music_dj as dj

BANDS={
 26:("night_00_07",{"tranquilla","media"}),
 27:("morning_07_10",{"media","tranquilla"}),
 28:("day_10_13",{"media","ritmata"}),
 29:("afternoon_13_18",{"ritmata","media"}),
 30:("evening_18_21",{"media","tranquilla"}),
 31:("late_21_24",{"tranquilla","media"})
}

def run(client,apply=False,limit=60):
    rows=client.call("GET","/station/1/playlists")
    byid={int(x["id"]):x for x in rows if isinstance(x,dict) and str(x.get("id","")).isdigit()}
    main=byid.get(25)
    if not main or main.get("name")!=sync.NAME or not main.get("is_enabled"):
        raise RuntimeError("Fallback music playlist 25 unavailable")
    for pid,(name,_) in BANDS.items():
        r=byid.get(pid)
        if not r or r.get("name")!="RDI fascia "+name or not r.get("is_enabled") or r.get("type")!="default":
            raise RuntimeError("Hourly playlist changed or disabled: "+str(pid))
        if not isinstance(r.get("schedule_items"),list) or len(r["schedule_items"])!=1:
            raise RuntimeError("Hourly schedule invalid: "+str(pid))
    dj.DB=sync.DB
    catalogue=dj.report()
    if not catalogue.get("live_index_verified"):
        raise RuntimeError("Music index is stale")
    tracks={t["id"]:t for t in catalogue["tracks"] if sync._eligible(t)}
    local=sync.local_music()
    files=sync.api_files(client)
    choices=collections.defaultdict(set)
    for path,t in local.items():
        if path not in files or t["id"] not in tracks:continue
        energy=tracks[t["id"]].get("energy_estimate")
        if energy not in ("ritmata","media","tranquilla"):continue
        existing=sync.ids(files[path].get("playlists"))
        if 25 not in existing: continue
        for pid,(_,allowed) in BANDS.items():
            if energy in allowed and pid not in existing:
                choices[path].add(pid)
    print("RDI_HOURLY_NEW_MEMBERSHIPS="+str(sum(map(len,choices.values()))),flush=True)
    print("RDI_HOURLY_NEW_FILES="+str(len(choices)),flush=True)
    if not apply:
        print("RDI_HOURLY_WRITES=0",flush=True);return
    changed=0
    for path in sorted(choices)[:max(1,min(limit,150))]:
        old=sync.ids(files[path].get("playlists"))
        updated=old|choices[path]
        sync.snapshot({"files":{path:sorted(old)},"reason":"hourly-new-song-sync"},
                      "hourly-new-"+str(changed)+"-"+__import__("datetime").datetime.now(__import__("datetime").timezone.utc).strftime("%Y%m%d%H%M%S%f")+".json")
        try:
            sync.set_memberships(client,[path],updated)
            latest=sync.api_files(client).get(path)
            if not latest or sync.ids(latest.get("playlists"))!=updated:
                raise RuntimeError("Membership verification failed")
        except Exception:
            try:sync.set_memberships(client,[path],old)
            except Exception:pass
            raise
        changed+=1
    print("RDI_HOURLY_ADDED_FILES="+str(changed),flush=True)
    print("RDI_HOURLY_EXISTING_PLAYLISTS_UNTOUCHED=true",flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    p.add_argument("--limit",type=int,default=60)
    p.add_argument("--php-helper",required=True)
    a=p.parse_args()
    helper=Path(a.php_helper).read_bytes()
    token=""
    try:
        token=sync.backend.azura_php(helper,"create")
        run(sync.backend.Client(token),a.apply,a.limit)
    finally:
        if token:sync.backend.azura_php(helper,"revoke",token.split(":",1)[0])
if __name__=="__main__":main()
