#!/usr/bin/env python3
"""RDI Piper: inspect or create ONLY an empty disabled announcement playlist.

No audio uploads, queue edits, streaming restarts, or existing playlist updates.
Credentials are temporary and revoked in finally.
"""
import argparse
import importlib.util
import json
from pathlib import Path

NAME = "RDI Conduttore Italiano - Serena"
ROOT = Path("/home/ubuntu/rdi-geopolitica/scripts")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("action", choices=["inspect","prepare-disabled"])
    p.add_argument("--scripts-dir",type=Path,default=ROOT)
    args=p.parse_args()
    folder=args.scripts_dir.resolve()
    backend_file=folder/"deploy-geopolitica-oracle.py"
    helper_file=folder/"rdi-geopolitica-auth.php"
    if not backend_file.is_file() or not helper_file.is_file():
        raise SystemExit("Helper AzuraCast mancanti.")
    spec=importlib.util.spec_from_file_location("rdi_auth_backend",backend_file)
    backend=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    token=""
    helper=helper_file.read_bytes()
    try:
        token=backend.azura_php(helper,"create")
        client=backend.Client(token)
        def get():
            rows=client.call("GET","/station/1/playlists")
            if not isinstance(rows,list): raise ValueError("Elenco playlist non valido")
            found=[r for r in rows if isinstance(r,dict) and r.get("name")==NAME]
            if len(found)>1: raise RuntimeError("Playlist duplicata: nessuna modifica")
            return found[0] if found else None
        existing=get()
        if args.action=="inspect":
            print(json.dumps({"playlist":NAME,"exists":existing is not None,
              "enabled":existing.get("is_enabled") if existing else None,
              "songs":existing.get("num_songs") if existing else None,
              "read_only":True},ensure_ascii=False))
            return
        if existing:
            if existing.get("is_enabled"):
                raise RuntimeError("Playlist omonima attiva: non la modifico.")
            print("Playlist dedicata già esistente e disabilitata: nessuna modifica.")
            return
        playlist={
            "name":NAME,
            "description":"Annunci vocali offline italiani generati da Piper. ATTIVAZIONE MANUALE DOPO CONTROLLO AUDIO E ORARI.",
            "type":"once_per_hour",
            "source":"songs",
            "order":"sequential",
            "is_enabled":False,
            "include_in_requests":False,
            "include_in_on_demand":False,
            "weight":1,
            "schedule_items":[]
        }
        client.call("POST","/station/1/playlists",playlist)
        new=get()
        if not new or new.get("is_enabled") or (new.get("schedule_items") or []):
            raise RuntimeError("Playlist non verificata come disabilitata e senza orari.")
        if new.get("num_songs") not in (None,0,"0"):
            raise RuntimeError("Playlist non vuota: verificare prima di proseguire.")
        print(json.dumps({"playlist":NAME,"created":True,"enabled":False,"scheduled":False,
            "on_air":False,"playlist_id":new.get("id")},ensure_ascii=False))
    finally:
        if token:
            backend.azura_php(helper,"revoke",token.split(":",1)[0])

if __name__=="__main__":
    main()
