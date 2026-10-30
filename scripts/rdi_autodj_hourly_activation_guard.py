#!/usr/bin/env python3
"""RDI hourly AutoDJ: safe opt-in AzuraCast staging / enabling.

Never deletes songs, playlists, queue entries, or existing schedules.
Default is read-only. Apply requires --apply and independent live preflight.
"""
import argparse, collections, datetime as dt, importlib.util, json, sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
spec=importlib.util.spec_from_file_location("rdi_backend",HERE/"deploy-geopolitica-oracle.py")
backend=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
import rdi_music_azuracast_sync as sync
import rdi_music_dj as dj

CONFIG=ROOT/"config/rdi-autodj-hourly-staging.json"
UNKNOWN={"non_identificato","sconosciuto","",None}
PREFIX="RDI Orario - "
BANDS=[("00:00","07:00"),("07:00","10:00"),("10:00","13:00"),("13:00","18:00"),("18:00","21:00"),("21:00","24:00")]

def selection(report,config):
    assert report.get("live_index_verified") is True
    tracks=report.get("tracks",[])
    eligible={x["id"]:x for x in tracks if sync._eligible(x)}
    if len(eligible)<400: raise RuntimeError("Insufficient live music")
    if [(x["from"],x["to"]) for x in config["bands"]]!=BANDS: raise RuntimeError("Schedule gap")
    genres=sum(x.get("genre_source")=="metadati_file" and x.get("genre") not in UNKNOWN for x in eligible.values())
    confident_pct=100*genres/len(eligible)
    groups=[]
    for band in config["bands"]:
        top=band["energy_priority"]
        ids=[k for k,t in eligible.items() if t.get("energy_estimate") in top]
        # Safe minimum: more than 40 real songs per category.
        if len(ids)<40: raise RuntimeError("Insufficient classified songs in "+band["id"])
        groups.append((band,ids))
    return eligible,groups,round(confident_pct,2)

def read_state(client):
    arr=client.call("GET","/station/1/playlists")
    if not isinstance(arr,list):raise RuntimeError("Invalid playlist list")
    return arr

def plan(client,eligible,groups):
    current=sync.api_files(client)
    by_id={}
    for path,record in current.items():
        token=sync.hashlib.sha256((str(sync.MEDIA_ROOT/path)).encode("utf-8","surrogateescape")).hexdigest()[:16]
        by_id[token]=(path,record)
    result=[]
    for band,trackids in groups:
        files=[by_id[t] for t in trackids if t in by_id]
        if len(files)<40: raise RuntimeError("Media paths cannot be verified for "+band["id"])
        result.append((band,files))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--apply",action="store_true")
    p.add_argument("--php-helper",default=str(HERE/"rdi-geopolitica-auth.php"))
    args=p.parse_args()
    with CONFIG.open() as fp: cfg=json.load(fp)
    dj.DB=sync.DB
    report=dj.report()
    eligible,groups,genre_percent=selection(report,cfg)
    if genre_percent<cfg["minimum_verified_genre_share_percent"]:
        print(json.dumps({"state":"BLOCKED","reason":"genre_verification_incomplete",
                          "verified_metadata_genre_percent":genre_percent,
                          "playlist_writes":0},indent=2))
        return
    if not args.apply:
        print(json.dumps({"state":"READY_FOR_REVIEW","groups":{b["id"]:len(v) for b,v in groups},
                          "playlist_writes":0},indent=2))
        return
    # Refuse broadcast changes until a separate safety-reviewed activation tool
    # is installed. This script deliberately cannot force a half-built playlist live.
    raise RuntimeError("Activation requires independent AzuraCast schedule-schema validation and rollback implementation")

if __name__=="__main__":
    main()
