#!/usr/bin/env python3
"""RDI AutoDJ hourly preflight against live, PRIVATE Oracle dashboard.

This tool never touches AzuraCast playlists. It checks the six time bands,
daily play-bank capacity and how many tracks have confidently labeled genres.
A failed result deliberately blocks premature on-air changes.
"""
from __future__ import annotations
import collections
import json
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
BANDS=[("00:00","07:00"),("07:00","10:00"),("10:00","13:00"),
       ("13:00","18:00"),("18:00","21:00"),("21:00","24:00")]
UNKNOWN={"", "non_identificato", "sconosciuto", "non_disponibile"}

def assess(cfg,report,rotation):
    tracks=report.get("tracks",[])
    bands=cfg.get("bands",[])
    if [(x.get("from"),x.get("to")) for x in bands]!=BANDS:
        raise ValueError("Six time bands must cover the full day without gaps")
    genres=sum(str(t.get("genre") or "").strip() not in UNKNOWN
               and t.get("genre_source")=="metadati_file" for t in tracks)
    covers=[float(b.get("copertura_percento",0)) for b in rotation.get("blocks",[])]
    blockers=[]
    if not report.get("live_index_verified"): blockers.append("live index stale")
    if len(tracks)<cfg.get("minimum_verified_catalogue",400):blockers.append("catalogue too small")
    if len(covers)!=6 or min(covers)<cfg.get("minimum_coverage_percent",98):
        blockers.append("one or more music bands lack coverage")
    # Even high-confidence model labels are suggestions, not verified genre truth.
    pct=100*genres/len(tracks) if tracks else 0
    if pct<cfg.get("minimum_verified_genre_share_percent",75):
        blockers.append("genre review not complete")
    return {"safe_to_activate":not blockers,"music_tracks":len(tracks),
            "verified_metadata_genres":genres,"verified_genre_percent":round(pct,2),
            "energies":dict(collections.Counter(t.get("energy_estimate","non_verificata") for t in tracks)),
            "band_coverage_percent":covers,"blockers":blockers,
            "fallback_playlist_id":cfg["fallback_playlist_id"],
            "playlist_writes":0,"mode":"read_only"}

def main():
    with (ROOT/"config/rdi-autodj-hourly-staging.json").open(encoding="utf-8") as f:
        cfg=json.load(f)
    def read(endpoint):
        with urlopen("http://127.0.0.1:8788/api/"+endpoint,timeout=15) as r:
            return json.load(r)
    print(json.dumps(assess(cfg,read("report"),read("rotation")),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
