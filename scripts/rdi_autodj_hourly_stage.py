#!/usr/bin/env python3
"""RDI: populate six DISABLED hourly playlists, leaving current on-air rotation untouched.

This script never enables a playlist. It preserves all existing song playlist
memberships and checks each batch, with rollback on verification errors.
"""
import argparse, collections, datetime as dt, importlib.util, json, sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import rdi_music_azuracast_sync as base
import rdi_music_dj as dj
CONFIG=HERE/"rdi-autodj-hourly-staging.json"
PREFIX="RDI fascia "
def schedule_items(b):
    # Use the documented schedule shape; never assume this will be accepted:
    # actual server response must be verified before any playlist is enabled.
    end=b["to"]
    if end=="24:00":end="23:59"
    return [{"start_time":b["from"],"end_time":end,
             "days":[],"loop_once":False}]
def candidates():
    dj.DB=base.DB
    rep=dj.report()
    if not rep.get("live_index_verified"):raise RuntimeError("Stale inventory")
    catalog={t["id"]:t for t in rep["tracks"] if base._eligible(t)}
    actual=base.local_music()
    result={p:(t,catalog.get(t["id"])) for p,t in actual.items() if t["id"] in catalog}
    if len(result)<400:raise RuntimeError("Insufficient current media")
    return result
def names(cfg):
    return [(PREFIX+b["id"],b) for b in cfg["bands"]]
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("mode",choices=["audit","prepare"],default="audit")
    ap.add_argument("--php-helper",required=True)
    args=ap.parse_args()
    cfg=json.loads(CONFIG.read_text())
    if cfg["status"]!="staging_not_on_air" or cfg["fallback_playlist_id"]!=25:
        raise RuntimeError("Unsafe configuration")
    if [(b["from"],b["to"]) for b in cfg["bands"]] != [
        ("00:00","07:00"),("07:00","10:00"),("10:00","13:00"),
        ("13:00","18:00"),("18:00","21:00"),("21:00","24:00")]:
        raise RuntimeError("Schedule not contiguous")
    pool=candidates()
    helper=Path(args.php_helper).read_bytes()
    token=""
    try:
        token=base.backend.azura_php(helper,"create")
        client=base.backend.Client(token)
        playlists=client.call("GET","/station/1/playlists")
        general=[p for p in playlists if p.get("id")==25]
        if len(general)!=1 or general[0].get("name")!=base.NAME or not general[0].get("is_enabled"):
            raise RuntimeError("Live fallback playlist 25 changed; abort")
        existing={p.get("name"):p for p in playlists}
        for name,b in names(cfg):
            if name in existing and existing[name].get("is_enabled"):
                raise RuntimeError("Existing hourly playlist is live: refuse changes")
        media=base.api_files(client)
        plans=[]
        for name,b in names(cfg):
            chosen=[p for p,(t,info) in pool.items()
                    if info.get("energy_estimate") in b["energy_priority"] and p in media]
            if len(chosen)<40:raise RuntimeError("Insufficient verified tracks: "+name)
            plans.append((name,b,sorted(chosen)))
        print("RDI_HOURLY_PLANNED="+json.dumps({n:len(paths) for n,_,paths in plans}))
        if args.mode=="audit":
            print("RDI_HOURLY_WRITES=0");return
        for name,b,paths in plans:
            rec=existing.get(name)
            if not rec:
                client.call("POST","/station/1/playlists",{
                    "name":name,"description":"RDI energy-based slot; not yet approved for air",
                    "type":"default","source":"songs","order":"shuffle",
                    "is_enabled":False,"is_jingle":False,"weight":3,
                    "include_in_requests":False,"include_in_on_demand":False,
                    "avoid_duplicates":True,"schedule_items":schedule_items(b)})
                rec=next((x for x in client.call("GET","/station/1/playlists")
                          if x.get("name")==name),None)
            if not rec or rec.get("is_enabled") or rec.get("type")!="default":
                raise RuntimeError("Invalid or enabled staging playlist: "+name)
            pid=int(rec["id"])
            # Validate scheduling before populating; never enable even if valid.
            if rec.get("schedule_items") is None:
                raise RuntimeError("Schedule not acknowledged by AzuraCast: "+name)
            before=base.api_files(client)
            original={p:base.ids(before[p].get("playlists")) for p in paths}
            groups=collections.defaultdict(list)
            for path in paths:
                if pid not in original[path]:
                    groups[frozenset(original[path]|{pid})].append(path)
            for union,group in groups.items():
                for i in range(0,len(group),25):
                    batch=group[i:i+25]
                    base.snapshot({"playlist_id":pid,
                                   "files":{p:sorted(original[p]) for p in batch}},
                                  "hourly-"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d%H%M%S%f")+".json")
                    try:
                        base.set_memberships(client,batch,union)
                        base.verify_subset(client,original,pid,batch)
                    except Exception:
                        for p in batch:
                            try:base.set_memberships(client,[p],original[p])
                            except Exception:pass
                        raise
            current=next(x for x in client.call("GET","/station/1/playlists")
                         if int(x["id"])==pid)
            if current.get("is_enabled"):raise RuntimeError("Staging playlist unexpectedly enabled")
            print("RDI_HOURLY_STAGED="+name+" ID="+str(pid)+" TRACKS="+str(len(paths)),flush=True)
        print("RDI_HOURLY_ALL_DISABLED=true")
    finally:
        if token:base.backend.azura_php(helper,"revoke",token.split(":",1)[0])
if __name__=="__main__":
    main()
