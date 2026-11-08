#!/usr/bin/env python3
"""Stage RDI Italian Piper MP3 files into a dedicated DISABLED AzuraCast playlist.

Never activates/schedules the playlist, touches other playlists or restarts streams.
No full media inventory GET (the RDI station inventory can time out).
"""
from __future__ import annotations

import argparse
import base64
import importlib.util
import json
from pathlib import Path

NAME = "RDI Conduttore Italiano - Serena"
PLAYLIST_ID = 33
MEDIA_DIR = "RDI Conduttore Italiano Serena"
SCRIPTS_DIR = Path("/home/ubuntu/rdi-geopolitica/scripts")
ANNOUNCEMENTS = Path("/home/ubuntu/rdi-piper-test/annunci")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["check", "stage"])
    args = parser.parse_args()
    manifest = json.loads((ANNOUNCEMENTS/"manifest.json").read_text(encoding="utf-8"))
    if (manifest.get("language") != "it"
        or manifest.get("state") != "PREVIEW_ONLY_NOT_ON_AIR"
        or manifest.get("voice") != "it_IT-serena-medium"):
        raise RuntimeError("Unexpected manifest / voice state. No changes made.")
    entries = manifest.get("announcements")
    if not isinstance(entries,list) or len(entries) != 7:
        raise RuntimeError("Expected exactly seven Piper announcements")
    expected = {"apertura", "notizie", "top3", "storia", "musica", "sera", "notte"}
    if {x.get("slot") for x in entries} != expected:
        raise RuntimeError("Announcement slots do not match")
    media=[]
    for item in entries:
        wav_name = str(item.get("audio_filename") or "")
        if not wav_name.endswith(".wav") or Path(wav_name).name != wav_name:
            raise RuntimeError("Invalid filename")
        mp3=ANNOUNCEMENTS / (wav_name[:-4]+".mp3")
        if not item.get("ready") or not mp3.is_file() or not 4096 < mp3.stat().st_size < 2_000_000:
            raise RuntimeError(f"Missing / wrong MP3: {mp3.name}")
        media.append((mp3,MEDIA_DIR+"/"+mp3.name))
    backend_path = SCRIPTS_DIR/"deploy-geopolitica-oracle.py"
    helper_path = SCRIPTS_DIR/"rdi-geopolitica-auth.php"
    if not backend_path.is_file() or not helper_path.is_file():
        raise RuntimeError("AzuraCast backend unavailable")
    spec=importlib.util.spec_from_file_location("rdi_stage_azura",backend_path)
    backend=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    helper=helper_path.read_bytes()
    token=""
    try:
        token=backend.azura_php(helper,"create")
        client=backend.Client(token)
        def verify():
            rows=client.call("GET","/station/1/playlists")
            matching=[p for p in rows if isinstance(p,dict) and p.get("name")==NAME]
            if len(matching)!=1:
                raise RuntimeError("Dedicated playlist not unique")
            p=matching[0]
            if (int(p.get("id",-1)) != PLAYLIST_ID
                or p.get("is_enabled") is not False
                or p.get("type") != "once_per_hour"
                or p.get("source") != "songs"
                or (p.get("schedule_items") or [])):
                raise RuntimeError("Playlist is not the expected disabled, unscheduled staging playlist")
            return p
        p=verify()
        print(json.dumps({"phase":"preflight","playlist_id":PLAYLIST_ID,
                          "enabled":False,"scheduled":False,
                          "audio_count":len(media),"existing_playlist_songs":p.get("num_songs"),
                          "dry_run":args.action=="check"},ensure_ascii=False))
        if args.action=="check":
            return
        # Strictly disallow pre-existing tracks to avoid changing unknown media.
        if p.get("num_songs") not in (None,0,"0"):
            raise RuntimeError("Playlist already populated; staging refused")
        for mp3,relative in media:
            verify()
            uploaded=client.call("POST","/station/1/files",{
                "path":relative,
                "file":base64.b64encode(mp3.read_bytes()).decode("ascii")
            })
            if isinstance(uploaded,dict):
                actual=uploaded.get("path")
                if actual not in (None,relative):
                    raise RuntimeError(f"Unexpected upload path for {mp3.name}")
            linked=client.call("PUT","/station/1/files/batch",{
                "do":"playlist","playlists":[PLAYLIST_ID],
                "files":[relative],"dirs":[]
            })
            if isinstance(linked,dict) and linked.get("errors"):
                raise RuntimeError(f"AzuraCast rejected playlist assignment for {mp3.name}")
            print("STAGED="+mp3.name)
        verify()
        print(json.dumps({"staged_count":len(media),"playlist_id":PLAYLIST_ID,
                          "enabled":False,"scheduled":False,"on_air":False},ensure_ascii=False))
    finally:
        if token:
            backend.azura_php(helper,"revoke",token.split(":",1)[0])

if __name__=="__main__":
    main()
