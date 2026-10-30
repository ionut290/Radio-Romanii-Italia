#!/usr/bin/env python3
"""RDI AutoDJ: opt-in guarded sync of all verified music into ONE new playlist.

Real AzuraCast connection occurs only when run on Oracle with short-lived,
revoked credentials. Nothing writes to existing playlist configurations.
New music playlist is created DISABLED, then filled with exact union of each
song's current playlist memberships and our dedicated rotation playlist.

Supported actions: audit (read-only), prepare (create disabled), sync (update
membership while disabled), enable (after 99% coverage verification), status,
disable, reshuffle. No station restart/queue/immediate, no media delete/upload.
Snapshot before each batch and rollback on verification failure.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path, PurePosixPath
import re
import sqlite3
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("rdi_azuracast_client",ROOT/"deploy-geopolitica-oracle.py")
backend=importlib.util.module_from_spec(spec)
spec.loader.exec_module(backend)
import rdi_music_dj as dj
from rdi_music_rotation import _eligible, _bank

NAME="RDI DJ Intelligente - Rotazione completa"
ROME=ZoneInfo("Europe/Rome")
MEDIA_ROOT=Path("/var/lib/docker/volumes/azuracast_station_data/_data/radio-romanii-italia/media")
DB=Path("/home/ubuntu/rdi-music/music.db")
STATE=Path("/home/ubuntu/rdi-music/azuracast-sync")
MIN_VERIFIED=400
MIN_COVERAGE=.99
MAX_BATCH=25
BATCHES_PER_RUN=6

def ids(refs):
    if not isinstance(refs,list):
        raise ValueError("Playlist references missing; media is not safe to modify")
    out=set()
    for ref in refs:
        if isinstance(ref,dict): ref=ref.get("id")
        try: pid=int(ref)
        except (ValueError,TypeError):
            raise ValueError("Unexpected playlist reference") from None
        if pid<=0:raise ValueError("Invalid playlist reference")
        out.add(pid)
    return out

def find_playlist(client,create=False):
    rows=client.call("GET","/station/1/playlists")
    if not isinstance(rows,list):
        raise RuntimeError("Unexpected AzuraCast playlists response")
    matching=[p for p in rows if isinstance(p,dict) and p.get("name")==NAME]
    if len(matching)>1:
        raise RuntimeError("Ambiguous duplicate RDI DJ playlists")
    if not matching and create:
        body={
            "name":NAME,
            "description":"Rotazione completa RDI con brani validati. Gestita da sistema RDI, non contiene notiziari, spot o jingle.",
            "type":"default","source":"songs","order":"shuffle",
            "is_enabled":False,"is_jingle":False,"weight":4,
            "include_in_requests":False,"include_in_on_demand":False,
            "avoid_duplicates":True,"schedule_items":[]
        }
        client.call("POST","/station/1/playlists",body)
        return find_playlist(client,False)
    return matching[0] if matching else None

def validate_ours(rec):
    if not rec:raise RuntimeError("Dedicated RDI DJ playlist missing")
    if (rec.get("name")!=NAME or rec.get("type")!="default"
       or rec.get("source")!="songs" or rec.get("order")!="shuffle"
       or rec.get("is_jingle") is True or rec.get("schedule_items") not in (None,[])):
        raise RuntimeError("RDI DJ playlist configuration changed outside managed settings")
    try: pid=int(rec["id"])
    except (ValueError,KeyError,TypeError):
        raise RuntimeError("Invalid RDI DJ playlist ID") from None
    if pid<=0:raise RuntimeError("Invalid RDI DJ playlist ID")
    return pid

def api_files(client):
    files=client.call("GET","/station/1/files")
    if not isinstance(files,list):
        raise RuntimeError("Unexpected station files response")
    by_path={}
    for f in files:
        if not isinstance(f,dict):continue
        name=f.get("path")
        if not isinstance(name,str) or not name or name in by_path:
            raise RuntimeError("Duplicate or invalid AzuraCast media file paths")
        by_path[name]=f
    return by_path

def local_music():
    if not DB.is_file():raise RuntimeError("Local music inventory missing")
    # Only current, duration-verified music, no remembered/deleted files.
    dj.DB=DB
    report=dj.report()
    if not report.get("live_index_verified"):
        raise RuntimeError("Live station music scan older than 4 hours")
    pool=_bank(report.get("tracks",[]))
    if len(pool)<MIN_VERIFIED:
        raise RuntimeError("Insufficient validated music for live transition")
    db=sqlite3.connect(f"file:{DB}?mode=ro",uri=True)
    try:
        rows=db.execute("""SELECT l.path,l.size,l.modified FROM track_live_index l
           JOIN tracks t ON t.path=l.path AND t.size=l.size AND abs(t.modified-l.modified)<2
           WHERE l.duration_seconds BETWEEN 60 AND 720""").fetchall()
    finally: db.close()
    identity={
        hashlib.sha256(p.encode("utf-8","surrogateescape")).hexdigest()[:16]:p
        for p,_,_ in rows
    }
    selected={}
    for item in pool:
        source=identity.get(item["id"])
        if source is None:continue
        path=Path(source)
        try: relative=path.relative_to(MEDIA_ROOT).as_posix()
        except ValueError:continue
        if relative.startswith("/") or ".." in PurePosixPath(relative).parts or not relative:
            continue
        if relative in selected:
            raise RuntimeError("Duplicate relative AzuraCast music path")
        selected[relative]=item
    if len(selected)<MIN_VERIFIED:
        raise RuntimeError("Mapped station media has insufficient verified songs")
    return selected

def plan(client,ours):
    pool=local_music()
    media=api_files(client)
    pid=validate_ours(ours) if ours else None
    found={p:f for p,f in media.items() if p in pool}
    absent=sorted(set(pool)-set(found))
    if len(found)<MIN_VERIFIED:
        raise RuntimeError("AzuraCast API names do not match actual music inventory")
    if len(found)/len(pool)<.98:
        raise RuntimeError("Too many local songs are missing from AzuraCast media index")
    current={}
    protected=[]
    missing=[]
    for path,f in found.items():
        assigned=ids(f.get("playlists"))
        current[path]=assigned
        if pid is not None and pid in assigned:
            protected.append(path)
        else:missing.append(path)
    # Stable order prioritizes files not already assigned to the DJ, so new
    # uploads are picked up in the next run; path sort is deterministic.
    missing.sort()
    return {
        "verified_total":len(pool),"api_matching":len(found),
        "api_unmatched":len(absent),"already_linked":len(protected),
        "to_link":len(missing),"playlist_id":pid,
        "_target_paths":missing,"_media":found,"_memberships":current,
    }

def snapshot(data,name):
    STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    statefile=STATE/name
    content=json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2).encode()
    with statefile.open("xb") as out:
        out.write(content)
    statefile.chmod(0o600)
    return statefile

def set_memberships(client,paths,target):
    # A full SET, not just a new playlist ID. Avoids erasing already-assigned
    # genre playlists or special scheduling memberships on these songs.
    resp=client.call("PUT","/station/1/files/batch",{
        "do":"playlist","playlists":sorted(target),"files":list(paths),"dirs":[]
    })
    if isinstance(resp,dict) and resp.get("errors"):
        raise RuntimeError("AzuraCast batch playlist assignment rejected")

def verify_subset(client,original,pid,paths):
    all_files=api_files(client)
    for path in paths:
        record=all_files.get(path)
        if record is None:raise RuntimeError("Song vanished during assignment")
        expected=original[path]|{pid}
        if ids(record.get("playlists"))!=expected:
            raise RuntimeError("AzuraCast did not preserve all existing playlists")
    return True

def apply_batch(client,plan_data,limit):
    pid=plan_data["playlist_id"]
    if pid is None:raise RuntimeError("Prepare the disabled playlist first")
    candidate=plan_data["_target_paths"][:limit]
    if not candidate:return 0
    membership=plan_data["_memberships"]
    groups={}
    for path in candidate:
        union=frozenset(membership[path]|{pid})
        groups.setdefault(union,[]).append(path)
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name=f"rdi-dj-pre-{stamp}-{hashlib.sha256(str(candidate).encode()).hexdigest()[:9]}.json"
    snapshot({"playlist_id":pid,"files":{path:sorted(membership[path]) for path in candidate}},name)
    touched=[]
    try:
        for union,paths in groups.items():
            for start in range(0,len(paths),MAX_BATCH):
                batch=paths[start:start+MAX_BATCH]
                # Even after an HTTP timeout the write MAY have happened; add
                # to touched before the API call so rollback covers it.
                touched.extend(batch)
                set_memberships(client,batch,union)
                verify_subset(client,membership,pid,batch)
    except Exception:
        # Best effort rollback of ONLY touched files to their previous
        # memberships. Never enable the new playlist on an error.
        for path in touched:
            try:
                set_memberships(client,[path],membership[path])
            except Exception:
                pass
        raise
    return len(candidate)

def public_summary(info):
    return {key:info[key] for key in ("verified_total","api_matching",
        "api_unmatched","already_linked","to_link","playlist_id")}

def run(client,command,limit=None):
    if command=="prepare":
        ours=find_playlist(client,create=True)
        validate_ours(ours)
        if ours.get("is_enabled"):
            raise RuntimeError("Cannot prepare an already enabled playlist")
        print("DJ_PLAYLIST_PREPARED_DISABLED="+str(ours["id"]))
        return
    ours=find_playlist(client)
    if command=="status" and ours is None:
        info=plan(client,None)
        print("DJ_SYNC_STATUS="+json.dumps(public_summary(info),sort_keys=True))
        print("DJ_PLAYLIST_EXISTS=false")
        return
    pid=validate_ours(ours)
    if command=="disable":
        STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
        paused=STATE/"paused"
        paused.write_text("manual rollback - do not auto-enable\n")
        paused.chmod(0o600)
        if ours.get("is_enabled"):
            client.call("PUT",f"/station/1/playlist/{pid}",{"is_enabled":False})
        if find_playlist(client).get("is_enabled"):
            raise RuntimeError("Could not disable RDI DJ playlist")
        print("DJ_PLAYLIST_DISABLED=true")
        return
    info=plan(client,ours)
    summary=public_summary(info)
    summary["enabled"]=bool(ours.get("is_enabled"))
    print("DJ_SYNC_STATUS="+json.dumps(summary,sort_keys=True))
    if command=="status":return
    if command=="sync":
        # Add new uploads without toggling or rewriting the on-air playlist.
        # This updates only the song-to-playlist membership, preserving the
        # full original set. On any failed verification the batch rolls back.
        linked=apply_batch(client,info,min(max(1,int(limit or 50)),300))
        print("DJ_ADDED_PRESERVING_ORIGINALS="+str(linked))
        print("DJ_EXISTING_PLAYLISTS_CONFIGURED=0")
        return
    if command=="enable":
        if (STATE/"paused").exists():
            raise RuntimeError("AutoDJ disabled by rollback; resume explicitly")
        if ours.get("is_enabled"):
            print("DJ_ALREADY_ENABLED=true")
            return
        if info["to_link"]>0 or info["already_linked"]<MIN_VERIFIED:
            raise RuntimeError("Playlist must contain ALL current verified music before enabling")
        if info["already_linked"]/info["verified_total"]<MIN_COVERAGE:
            raise RuntimeError("Playlist population below safety threshold")
        client.call("PUT",f"/station/1/playlist/{pid}",{"is_enabled":True})
        updated=find_playlist(client)
        if not updated or not updated.get("is_enabled"):
            raise RuntimeError("RDI DJ playlist activation did not persist")
        print("DJ_INTELLIGENT_ROTATION_LIVE=true")
        return
    if command=="reshuffle":
        if not ours.get("is_enabled"):
            raise RuntimeError("Cannot reshuffle disabled playlist")
        # Optional AzuraCast API: 404/405 means unsupported in this version,
        # not permission to change Liquidsoap or the station configuration.
        client.call("POST",f"/station/1/playlist/{pid}/reshuffle")
        print("DJ_AZURACAST_RESHUFFLED=true")
        return
    raise ValueError("Unexpected command")

def auto_cycle(client,batch_limit=150):
    """Resumable first activation and continuing new-song synchronization."""
    if (STATE/"paused").exists():
        print("DJ_AUTO_STATUS=PAUSED_BY_OPERATOR",flush=True)
        return
    playlist=find_playlist(client)
    if playlist is None:
        run(client,"prepare")
    playlist=find_playlist(client)
    pid=validate_ours(playlist)
    completed=0
    for attempt in range(12):
        info=plan(client,playlist)
        if info["to_link"]==0:break
        batch=min(max(1,batch_limit),250)
        added=apply_batch(client,info,batch)
        if not added:
            raise RuntimeError("DJ music sync made no progress")
        completed+=added
        # No media/playlist config is ever deleted or unlinked.
        print("DJ_AUTO_PROGRESS="+str(completed),flush=True)
    check=plan(client,find_playlist(client))
    print("DJ_AUTO_LEFT_TO_SYNC="+str(check["to_link"]),flush=True)
    if check["to_link"]:
        print("DJ_AUTO_STATUS=CONTINUE_ON_NEXT_RUN",flush=True)
        return
    run(client,"enable")
    # At most one daily reshuffle after the playlist is enabled. If the
    # installed AzuraCast version lacks this endpoint, shuffle mode still
    # works and the playlist remains on air without any station reset.
    today=dt.datetime.now(ROME).date().isoformat()
    datefile=STATE/"last-daily-shuffle.txt"
    previous=datefile.read_text().strip() if datefile.exists() else ""
    if today!=previous:
        try:
            run(client,"reshuffle")
        except RuntimeError:
            print("DJ_DAILY_RESHUFFLE=NOT_AVAILABLE_IN_CURRENT_AZURACAST",flush=True)
        else:
            STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
            temp=STATE/"last-daily-shuffle.tmp"
            temp.write_text(today)
            temp.chmod(0o600)
            temp.replace(datefile)
            print("DJ_DAILY_SHUFFLE_DATE="+today,flush=True)
    print("DJ_AUTO_STATUS=LIVE_WITH_EXISTING_GENRE_PLAYLISTS_PRESERVED",flush=True)

def publish_public_status(client):
    """Sanitized operational snapshot for the private DJ dashboard only."""
    import os
    import pwd
    ours=find_playlist(client)
    if not ours:
        data={"playlist_exists":False,"enabled":False,"songs":0}
    else:
        pid=validate_ours(ours)
        info=plan(client,ours)
        data={
            "playlist_exists":True,"playlist_id":pid,
            "enabled":bool(ours.get("is_enabled")),
            "songs":info["already_linked"],
            "verified_total":info["verified_total"],
            "still_to_link":info["to_link"],
            "paused":(STATE/"paused").exists(),
            "on_air_order":"azuracast_shuffle",
            "simulated_daily_order_is_not_on_air":True,
        }
    data.update({"schema_version":1,"updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                 "source":"azuracast_api_verified","music_playlist_only":True})
    out=Path("/home/ubuntu/rdi-music/autodj-public-status.json")
    out.parent.mkdir(parents=True,exist_ok=True)
    temp=out.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True))
    temp.chmod(0o644)
    nobody=pwd.getpwnam("ubuntu")
    os.chown(temp,nobody.pw_uid,nobody.pw_gid)
    temp.replace(out)
    print("DJ_DASHBOARD_STATUS="+("ENABLED" if data["enabled"] else "DISABLED"),
          "TRACKS="+str(data.get("songs",0)),flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("command",choices=("status","prepare","sync","enable","disable","reshuffle","auto","resume"))
    p.add_argument("--limit",type=int,default=150)
    p.add_argument("--php-helper",required=True)
    args=p.parse_args()
    helper=Path(args.php_helper).read_bytes()
    token=""
    try:
        token=backend.azura_php(helper,"create")
        client=backend.Client(token)
        if args.command=="resume":
            (STATE/"paused").unlink(missing_ok=True)
            auto_cycle(client,args.limit)
        elif args.command=="auto":
            auto_cycle(client,args.limit)
        else:
            run(client,args.command,args.limit)
        # Never display a guessed on-air state; refresh from AzuraCast itself.
        publish_public_status(client)
    finally:
        if token:backend.azura_php(helper,"revoke",token.split(":",1)[0])

if __name__=="__main__":
    main()
