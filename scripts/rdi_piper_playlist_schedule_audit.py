#!/usr/bin/env python3
"""RDI: read-only, lightweight AzuraCast playlist/schedules audit.

No station file catalogue reads; no playlist/media writes; revokes short-lived key.
Run with sudo on the existing Oracle radio server.
"""
from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path

DEFAULT_ROOT = Path("/home/ubuntu/rdi-geopolitica/scripts")
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--scripts-dir",type=Path,default=DEFAULT_ROOT)
    args = p.parse_args()
    directory=args.scripts_dir.resolve()
    backend_path=directory/"deploy-geopolitica-oracle.py"
    php_path=directory/"rdi-geopolitica-auth.php"
    if not backend_path.is_file() or not php_path.is_file():
        raise SystemExit("File di autenticazione AzuraCast non trovati.")
    spec=importlib.util.spec_from_file_location("rdi_azura_backend",backend_path)
    backend=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backend)
    token=""
    try:
        token=backend.azura_php(php_path.read_bytes(),"create")
        client=backend.Client(token)
        rows=client.call("GET","/station/1/playlists")
        if not isinstance(rows,list):
            raise RuntimeError("Formato della risposta playlist non valido")
        report=[]
        for row in rows:
            if not isinstance(row,dict):
                continue
            report.append({
                "name":str(row.get("name") or "")[:100],
                "enabled":bool(row.get("is_enabled")),
                "type":row.get("type"),
                "source":row.get("source"),
                "order":row.get("order"),
                "weight":row.get("weight"),
                "schedule_items":row.get("schedule_items") or [],
            })
        print(json.dumps({"read_only":True,"playlist_count":len(report),"playlists":report},ensure_ascii=False,default=str,indent=2))
    finally:
        if token:
            backend.azura_php(php_path.read_bytes(),"revoke",token.split(":",1)[0])

if __name__=="__main__":
    main()
