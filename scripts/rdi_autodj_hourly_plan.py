#!/usr/bin/env python3
"""Build six RDI AutoDJ hourly playlist proposals from the verified local catalog.

READ ONLY: no AzuraCast credentials, HTTP writes, station restarts, queue writes.
Never asserts that an AI-estimated genre is a verified genre.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

BASE=Path(__file__).resolve().parents[1]
BANDS=(("00:00","07:00"),("07:00","10:00"),("10:00","13:00"),
       ("13:00","18:00"),("18:00","21:00"),("21:00","24:00"))
VALID={"ritmata","media","tranquilla"}
def build(config,report,day):
    if not report.get("live_index_verified") or report.get("read_only") is not True:
        raise RuntimeError("Fresh, read-only live catalog required")
    if [(b["from"],b["to"]) for b in config["bands"]]!=list(BANDS):
        raise ValueError("Unexpected or overlapping time bands")
    tracks=report.get("tracks",[])
    tracks=[t for t in tracks if isinstance(t.get("id"),str)
            and isinstance(t.get("duration_seconds"),(int,float))
            and 60<=t["duration_seconds"]<=720]
    if len(tracks)<config["minimum_verified_catalogue"]:
        raise RuntimeError("Insufficient verified music")
    order=sorted(tracks,key=lambda t:hashlib.sha256(
        (day+"|"+t["id"]).encode()).hexdigest())
    output=[]
    for band in config["bands"]:
        rank={v:i for i,v in enumerate(band["energy_priority"])}
        # Broad-energy selection only; no invented genre labels. Ensure
        # enough candidates by allowing the complete general bank as fallback.
        preferred=[t for t in order if t.get("energy_estimate") in rank]
        preferred.sort(key=lambda t:rank[t["energy_estimate"]])
        fallback=[t for t in order if t["id"] not in {p["id"] for p in preferred}]
        names=list(dict.fromkeys(t["id"] for t in preferred+fallback))
        output.append({"id":band["id"],"from":band["from"],"to":band["to"],
          "theme":band["theme"],"preferred_count":len(preferred),
          "fallback_count":len(fallback),"song_ids_in_order":names,
          "genre_verified":False,"on_air":False})
    return {"date":day,"timezone":"Europe/Rome","state":"STAGING_NOT_ON_AIR",
      "playlist_writes":0,"existing_playlist_25_unchanged":True,
      "catalogue_size":len(tracks),"bands":output}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default=str(BASE/"config/rdi-autodj-hourly-staging.json"))
    p.add_argument("--date",default=dt.date.today().isoformat())
    p.add_argument("--report",help="Local read-only DJ report JSON, else Oracle loopback API")
    args=p.parse_args()
    with open(args.config,encoding="utf8") as f: cfg=json.load(f)
    if args.report:
        with open(args.report,encoding="utf8") as f: report=json.load(f)
    else:
        with urlopen("http://127.0.0.1:8788/api/report",timeout=15) as r: report=json.load(r)
    print(json.dumps(build(cfg,report,args.date),ensure_ascii=False))
if __name__=="__main__":
    main()
