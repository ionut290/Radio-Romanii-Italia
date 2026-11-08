#!/usr/bin/env python3
"""Convert previously generated Italian Piper WAV previews to broadcast-ready MP3.
Offline only: no AzuraCast uploads, no scheduling, no stream changes.
"""
import json
import os
from pathlib import Path
import subprocess
import tempfile

folder=Path.home()/"rdi-piper-test"/"annunci"
manifest=folder/"manifest.json"
if not manifest.is_file():
    raise SystemExit("Manifest mancante: generare prima gli annunci con Piper.")
data=json.loads(manifest.read_text(encoding="utf-8"))
if data.get("state")!="PREVIEW_ONLY_NOT_ON_AIR" or data.get("language")!="it":
    raise SystemExit("Manifest non valido per anteprima italiana.")
count=0
for item in data["announcements"]:
    source=folder/Path(item["audio_filename"]).name
    dest=source.with_suffix(".mp3")
    if not source.is_file() or source.stat().st_size<2048:
        raise SystemExit(f"WAV non valido: {source.name}")
    if dest.is_file() and dest.stat().st_size>2048:
        print(f"Già pronto: {dest.name}")
        count+=1
        continue
    fd,tmpname=tempfile.mkstemp(dir=folder,prefix=".rdi-",suffix=".mp3")
    os.close(fd)
    tmp=Path(tmpname)
    try:
        args=["nice","-n","15","ffmpeg","-hide_banner","-loglevel","error","-nostdin","-threads","1","-y","-i",str(source),"-af","loudnorm=I=-18:TP=-1.5:LRA=11","-ar","44100","-ac","2","-c:a","libmp3lame","-b:a","160k",str(tmp)]
        subprocess.run(args,check=True,timeout=60)
        if tmp.stat().st_size<2048: raise RuntimeError(f"MP3 vuoto: {dest.name}")
        tmp.replace(dest)
    finally:
        tmp.unlink(missing_ok=True)
    count+=1
    print(f"Creato: {dest.name} ({dest.stat().st_size//1024} KB)")
print(json.dumps({"mp3_ready":count,"on_air":False,"directory":str(folder)}))
