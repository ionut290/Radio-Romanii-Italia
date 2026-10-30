#!/usr/bin/env python3
"""Diagnostic only: never print media paths or process/playlist credentials."""
import pathlib
import subprocess
import sys
import sqlite3
sys.path.insert(0,"/opt/rdi-music-dj")
import rdi_music_ai as m

db=sqlite3.connect(pathlib.Path.home()/"rdi-music/music.db")
paths=m.sample_paths(db,10)
db.close()
for path,_,_ in paths[:4]:
    stat=subprocess.run(["sudo","-n","stat","-c","%s", "--",path],capture_output=True,timeout=12)
    print("SAMPLE_EXISTS="+str(stat.returncode==0),flush=True)
    cmd=["sudo","-n","nice","-n","15","ffmpeg","-nostdin","-v","error",
         "-threads","1","-ss","8","-t","7","-i",path,"-vn","-ac","1",
         "-ar","16000","-f","f32le","-acodec","pcm_f32le","-"]
    try:
        r=subprocess.run(cmd,capture_output=True,timeout=35)
        err=r.stderr.decode("utf-8","replace").lower()
        categories={
          "sudo_permission":"sudo:" in err,
          "media_missing":"no such file" in err,
          "media_denied":"permission denied" in err,
          "decoder":"invalid data" in err or "could not find codec" in err,
          "ffmpeg":"unrecognized option" in err or "option not found" in err,
          "format":"invalid argument" in err,
          "namespace":"not permitted" in err or "operation not permitted" in err,
        }
        print("SAMPLE_FFMPEG_EXIT="+str(r.returncode),flush=True)
        print("SAMPLE_DECODED_BYTES="+str(len(r.stdout)),flush=True)
        print("SAMPLE_ERROR_CATEGORIES="+str([k for k,v in categories.items() if v]),flush=True)
    except Exception as exc:
        print("SAMPLE_EXEC_ERROR="+type(exc).__name__,flush=True)
