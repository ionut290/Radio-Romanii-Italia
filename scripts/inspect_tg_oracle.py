#!/usr/bin/env python3
"""Read-only AzuraCast schedule audit for the RDI evening television news.

Never prints API tokens or changes station playlists.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("rdi_geopolitica_api",ROOT/"deploy-geopolitica-oracle.py")
api=importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)

def inspect(helper: Path):
    source=helper.read_bytes()
    token=""
    try:
        token=api.azura_php(source,"create")
        client=api.Client(token)
        playlists=client.call("GET","/station/1/playlists")
        print("READ_ONLY_STATION_AUDIT=true")
        for p in playlists:
            # Only public configuration; omit uploaded tracks and any user details.
            if p.get("type")=="once_per_hour" or p.get("schedule_items") or "RDI" in str(p.get("name","")):
                clean={k:p.get(k) for k in
                  ["id","name","type","source","play_per_hour_minute","backend_options",
                   "is_enabled","schedule_items","weight","priority","num_songs","played_at"]
                  if k in p}
                print("PLAYLIST="+json.dumps(clean,ensure_ascii=False))
    finally:
        if token:
            api.azura_php(source,"revoke",token.split(":",1)[0])

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--php-helper",required=True)
    args=p.parse_args()
    inspect(Path(args.php_helper))
