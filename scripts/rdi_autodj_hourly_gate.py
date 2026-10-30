#!/usr/bin/env python3
"""Read-only safety gate for RDI's proposed six-band AutoDJ.

Never communicates with AzuraCast's write API. Does not enable playlists.
"""
import argparse
import collections
import json
from pathlib import Path
from urllib.request import urlopen

EXPECTED = [("00:00","07:00"),("07:00","10:00"),("10:00","13:00"),
            ("13:00","18:00"),("18:00","21:00"),("21:00","24:00")]
UNKNOWN = {"", "non_identificato", "sconosciuto", "non_disponibile"}

def validate(config, report, rotation):
    bands=config["bands"]
    assert len(bands)==6 and [(x["from"],x["to"]) for x in bands]==EXPECTED
    assert config["fallback_playlist_id"]==25
    assert config["status"]=="staging_not_on_air"
    tracks=report.get("tracks",[])
    count=len(tracks)
    energies=collections.Counter(x.get("energy_estimate","non_verificata") for x in tracks)
    verified_genres=sum(str(x.get("genre") or "").strip() not in UNKNOWN for x in tracks)
    genre_pct=round(100*verified_genres/count,2) if count else 0
    cover=[float(x.get("copertura_percento",0)) for x in rotation.get("blocks",[])]
    reasons=[]
    if not report.get("live_index_verified"): reasons.append("stale_live_inventory")
    if count < config["minimum_verified_catalogue"]: reasons.append("insufficient_music")
    if len(cover)!=6 or min(cover)<config["minimum_coverage_percent"]: reasons.append("insufficient_band_coverage")
    if genre_pct < config["minimum_verified_genre_share_percent"]: reasons.append("genre_verification_incomplete")
    return {"mode":"READ_ONLY","ready_to_activate":not reasons,
            "catalogue_tracks":count,"verified_genre_tracks":verified_genres,
            "verified_genre_percent":genre_pct,"energy_counts":dict(energies),
            "simulated_band_coverage_percent":cover,"blockers":reasons,
            "fallback_playlist_id":25,"playlist_writes":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--config",default=str(Path(__file__).resolve().parents[1]/"config/rdi-autodj-hourly-staging.json"))
    p.add_argument("--base-url",default="http://127.0.0.1:8788")
    args=p.parse_args()
    with open(args.config,encoding="utf-8") as f: cfg=json.load(f)
    def read(endpoint):
        with urlopen(args.base_url.rstrip("/")+"/api/"+endpoint,timeout=18) as resp:
            return json.load(resp)
    out=validate(cfg,read("report"),read("rotation"))
    print(json.dumps(out,ensure_ascii=False,indent=2))
    # A nonzero exit means the station is NOT ready for scheduling.
    raise SystemExit(0 if out["ready_to_activate"] else 2)

if __name__=="__main__":
    main()
