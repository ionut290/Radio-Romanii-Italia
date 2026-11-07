#!/usr/bin/env python3
"""Read-only audit: verify a future RDI Top3 episode exists on the station."""
import argparse,importlib.util,json,pathlib
ROOT=pathlib.Path("/var/lib/rdi-ai-music")
NAME="RDI AI MUSIC - TOP 3 del giorno"
def module(path):
    spec=importlib.util.spec_from_file_location("rdi_azura_api",path)
    obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
def main():
    p=argparse.ArgumentParser();p.add_argument("--api-module",required=True);p.add_argument("--php-helper",required=True)
    args=p.parse_args()
    manifest=json.loads((ROOT/"top3"/"current.json").read_text(encoding="utf-8"))
    assert manifest.get("published") and len(manifest.get("segments",[]))==3
    lib=module(args.api_module);source=pathlib.Path(args.php_helper).read_bytes();token=lib.azura_php(source,"create")
    try:
        api=lib.Client(token)
        playlists=api.call("GET","/station/1/playlists")
        matches=[x for x in playlists if x.get("name")==NAME]
        assert len(matches)==1,"Expected exactly one Top3 playlist"
        playlist=matches[0]
        assert playlist.get("is_enabled"),"Top3 playlist disabled"
        assert playlist.get("type")=="once_per_hour" and int(playlist.get("play_per_hour_minute",-1))==30
        pid=int(playlist["id"])
        detail=api.call("GET",f"/station/1/playlist/{pid}")
        sched=detail.get("schedule_items",[])
        assert any(x.get("start_time")==2030 and x.get("end_time")==2120 and
                   x.get("start_date")==manifest["edition_day"] and x.get("end_date")==manifest["edition_day"]
                   and x.get("loop_once") for x in sched)
        files=api.call("GET","/station/1/files")
        wanted="RDI AI MUSIC TOP3/"+manifest["track_title"]+".mp3"
        found=[f for f in files if f.get("path")==wanted]
        assert len(found)==1, "Scheduled episode audio missing in AzuraCast"
        track=found[0]
        links=track.get("playlists")
        associated=False
        if isinstance(links,list):
            for value in links:
                try:
                    associated=associated or int(value.get("id") if isinstance(value,dict) else value)==pid
                except (TypeError,ValueError):pass
        assert associated, "Episode file not assigned to Top3 playlist"
        print("RDI_TOP3_STATUS=READY")
        print("PLAYLIST_ENABLED=true")
        print("PLAYLIST_ID="+str(pid))
        print("EPISODE="+manifest["track_title"])
        print("DURATION_SECONDS="+str(manifest["duration_seconds"]))
        print("TOP3_AUDIO_FILE_ASSIGNED=true")
        print("TOP3_SCHEDULE="+json.dumps(sched,ensure_ascii=False)[:900])
        print("TOP3_MEDIA_TITLE="+str((track.get("song") or {}).get("title") or track.get("title") or "not_available"))
    finally:
        lib.azura_php(source,"revoke",token.split(":",1)[0])
if __name__=="__main__":main()
