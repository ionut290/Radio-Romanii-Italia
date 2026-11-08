#!/usr/bin/env python3
"""Prepare six individually timed, DISABLED RDI Serena announcement playlists.

This command only CREATES new playlists; all remain disabled. Existing playlist
#33 and all existing tracks/playlists are never modified. No on-air effects.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

BASE=Path("/home/ubuntu/rdi-geopolitica/scripts")
SLOTS=(
 ("apertura","07:05",705,710),
 ("musica","10:45",1045,1050),
 ("notizie","12:15",1215,1220),
 ("storia","15:15",1515,1520),
 ("sera","19:15",1915,1920),
 ("notte","22:30",2230,2235),
)
PREFIX="RDI Serena - "
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action", choices=["plan","prepare-disabled"])
    args=parser.parse_args()
    if args.action=="plan":
        print(json.dumps({"on_air":False,"schedule":SLOTS},ensure_ascii=False))
        return
    backend_path=BASE/"deploy-geopolitica-oracle.py"
    helper_path=BASE/"rdi-geopolitica-auth.php"
    spec=importlib.util.spec_from_file_location("rdi_serena_api",backend_path)
    backend=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    helper=helper_path.read_bytes()
    token=""
    try:
        token=backend.azura_php(helper,"create")
        client=backend.Client(token)
        def read():
            rows=client.call("GET","/station/1/playlists")
            if not isinstance(rows,list): raise RuntimeError("Invalid playlist listing")
            return rows
        playlists=read()
        base=[r for r in playlists if r.get("name")=="RDI Conduttore Italiano - Serena"]
        if len(base)!=1 or int(base[0].get("id",-1))!=33 or base[0].get("is_enabled"):
            raise RuntimeError("Playlist 33 missing or enabled; no changes allowed")
        prepared=[]
        for key,label,start,end in SLOTS:
            name=PREFIX+key
            found=[r for r in playlists if r.get("name")==name]
            if len(found)>1: raise RuntimeError("Duplicate playlist "+name)
            if found:
                p=found[0]
                if p.get("is_enabled") or p.get("type")!="once_per_hour" or p.get("source")!="songs":
                    raise RuntimeError("Unexpected existing playlist "+name)
                prepared.append({"slot":key,"playlist_id":p.get("id"),"already_exists":True,"enabled":False})
                continue
            body={
                "name":name,
                "description":"Solo annuncio italiano Piper Serena "+key+" alle "+label+"; NON ATTIVARE prima del controllo qualità e collisioni.",
                "type":"once_per_hour",
                "source":"songs",
                "order":"sequential",
                "play_per_hour_minute":start%100,
                "is_enabled":False,
                "include_in_requests":False,
                "include_in_on_demand":False,
                "avoid_duplicates":False,
                "weight":1,
                "schedule_items":[{
                    "start_time":start,
                    "end_time":end,
                    "start_date":None,
                    "end_date":None,
                    "days":[1,2,3,4,5,6,7],
                    "loop_once":True
                }],
            }
            client.call("POST","/station/1/playlists",body)
            playlists=read()
            new=[r for r in playlists if r.get("name")==name]
            if len(new)!=1 or new[0].get("is_enabled"):
                raise RuntimeError("Creation verification failed "+name)
            prepared.append({"slot":key,"playlist_id":new[0].get("id"),"enabled":False,"at":label})
        print(json.dumps({"created_or_verified":len(prepared),"playlists":prepared,
                          "original_33_untouched":True,"on_air":False},ensure_ascii=False))
    finally:
        if token: backend.azura_php(helper,"revoke",token.split(":",1)[0])

if __name__=="__main__":
    main()
