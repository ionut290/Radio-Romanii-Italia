#!/usr/bin/env python3
"""Read-only station info for RDI music-hour scheduling compatibility."""
import importlib.util
import json
from pathlib import Path
root=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("rdi_client",root/"deploy-geopolitica-oracle.py")
clientmod=importlib.util.module_from_spec(spec);spec.loader.exec_module(clientmod)
helper=(root/"rdi-geopolitica-auth.php").read_bytes()
token=""
try:
 token=clientmod.azura_php(helper,"create")
 client=clientmod.Client(token)
 lists=client.call("GET","/station/1/playlists")
 target=next((p for p in lists if p.get("name")=="RDI DJ Intelligente - Rotazione completa"),None)
 if not target:raise RuntimeError("RDI DJ playlist missing")
 print("SAMPLE_PLAYLIST_KEYS="+json.dumps(sorted(target.keys())))
 print("SAMPLE_DJ_LIST="+json.dumps({k:target.get(k) for k in ["id","is_enabled","type","weight","priority","order","schedule_items","avoid_duplicates"]},ensure_ascii=False))
 print("OTHER_PLAYLIST_TOTAL="+str(len(lists)-1))
 print("SCHEDULED_PLAYLISTS="+str(sum(bool(p.get("schedule_items")) for p in lists)))
 print("ACTIVE_GENERAL_ROTATION="+str(sum(bool(p.get("is_enabled")) and p.get("type")=="default" for p in lists)))
 print("OBSERVATION_ONLY=true")
finally:
 if token:clientmod.azura_php(helper,"revoke",token.split(":",1)[0])
