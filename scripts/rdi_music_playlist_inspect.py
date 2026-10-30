#!/usr/bin/env python3
"""Read-only RDI station playlist audit via a temporary, revoked API token.

Returns playlist structure without station credentials. No mutations of any
playlist or song. Helps choose safe AutoDJ integration instead of overriding
existing on-air music, news or announcements.
"""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("rdi_azuracast_client",ROOT/"deploy-geopolitica-oracle.py")
backend=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)

def audit(client):
    items=client.call("GET","/station/1/playlists")
    if not isinstance(items,list):
        raise ValueError("Unexpected AzuraCast station playlists response")
    report=[]
    for p in items:
        if not isinstance(p,dict):continue
        report.append({
            "id":p.get("id"),
            "name":str(p.get("name") or "")[:90],
            "enabled":p.get("is_enabled"),
            "type":p.get("type"),
            "source":p.get("source"),
            "order":p.get("order"),
            "songs":p.get("num_songs"),
            "schedule_count":len(p.get("schedule_items") or []),
            "weight":p.get("weight")
        })
    return {"playlist_count":len(items),"active_count":sum(bool(p.get("enabled")) for p in report),
            "general_playlists":[p for p in report if p.get("type")=="default"],
            "protected_playlists":[p for p in report if p.get("type")!="default"],
            "read_only":True,"playlist_writes":0}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--php-helper",required=True)
    args=p.parse_args()
    helper=Path(args.php_helper).read_bytes()
    token=""
    try:
        token=backend.azura_php(helper,"create")
        result=audit(backend.Client(token))
        print("RDI_CURRENT_AZURACAST_PLAYLISTS="+json.dumps(result,ensure_ascii=False))
    finally:
        if token:
            backend.azura_php(helper,"revoke",token.split(":",1)[0])

if __name__=="__main__":
    main()
