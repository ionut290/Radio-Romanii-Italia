#!/usr/bin/env python3
"""Read-only on-air transition audit for RDI hourly radio programming.

Dumps a restorable snapshot of playlist configuration and reports competing
general playlists. No station or playlist modification.
"""
import datetime as dt,json,sys
from pathlib import Path
sys.path.insert(0,"/opt/rdi-music-dj")
import rdi_music_azuracast_sync as sync
SLOTS={26:(0,420),27:(420,600),28:(600,780),29:(780,1080),30:(1080,1260),31:(1260,0)}
def main():
    helper=Path("/opt/rdi-music-dj/rdi-geopolitica-auth.php").read_bytes()
    token=""
    try:
        token=sync.backend.azura_php(helper,"create")
        c=sync.backend.Client(token)
        raw=c.call("GET","/station/1/playlists")
        indexed={int(p["id"]):p for p in raw}
        main=indexed.get(25)
        if not main or main.get("name")!=sync.NAME or not main.get("is_enabled"):
            raise RuntimeError("Fallback 25 is not currently healthy")
        for pid,(start,end) in SLOTS.items():
            p=indexed.get(pid)
            if not p or p.get("is_enabled") or not p.get("name","").startswith("RDI fascia "):
                raise RuntimeError("Hourly slot state unexpected "+str(pid))
            items=p.get("schedule_items")
            if not isinstance(items,list) or len(items)!=1 or int(items[0]["start_time"])!=start or int(items[0]["end_time"])!=end:
                raise RuntimeError("Hourly slot schedule invalid "+str(pid))
        protected=[{"id":int(p["id"]),"name":p["name"],"type":p.get("type")} for p in raw
                   if p.get("is_enabled") and p.get("type")!="default"]
        competition=[{"id":int(p["id"]),"name":p["name"],"weight":p.get("weight"),"songs":p.get("num_songs")} for p in raw
                     if p.get("is_enabled") and p.get("type")=="default"]
        dest=Path("/home/ubuntu/rdi-music/azuracast-sync/hourly-transition-preflight.json")
        dest.parent.mkdir(parents=True,exist_ok=True)
        snapshot={"at":dt.datetime.now(dt.timezone.utc).isoformat(),"station":1,"playlists":raw}
        tmp=dest.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2))
        tmp.chmod(0o600)
        tmp.replace(dest)
        print("RDI_BACKUP_PATH="+str(dest))
        print("RDI_HOURLY_SCHEDULES=PASS_6")
        print("RDI_HOURLY_CURRENTLY_DISABLED=6")
        print("RDI_FALLBACK_25=ACTIVE")
        print("RDI_PROTECTED_INTERVAL_PLAYLISTS="+json.dumps(protected,ensure_ascii=False))
        print("RDI_COMPETING_DEFAULT_PLAYLISTS="+json.dumps(competition,ensure_ascii=False))
        print("RDI_WRITES_TO_AZURACAST=0")
    finally:
        if token:sync.backend.azura_php(helper,"revoke",token.split(":",1)[0])
if __name__=="__main__":main()
