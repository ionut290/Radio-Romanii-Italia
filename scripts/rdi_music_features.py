#!/usr/bin/env python3
"""RDI: lightweight supplementary audio measurements. Does not alter playlists."""
import argparse
import datetime as dt
import pathlib
import re
import sqlite3
import subprocess

DB = pathlib.Path.home() / "rdi-music" / "music.db"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    db = sqlite3.connect(DB)
    db.execute("""CREATE TABLE IF NOT EXISTS track_features (
       path TEXT PRIMARY KEY, size INTEGER, modified REAL,
       integrated_lufs REAL, loudness_range REAL, rms_db REAL, peak_db REAL,
       analyzed_at TEXT
    )""")
    rows = db.execute("SELECT path,size,modified FROM tracks ORDER BY analyzed_at ASC").fetchall()
    done = 0
    for path,size,modified in rows:
        if done >= max(1,min(args.limit,10)):
            break
        old = db.execute("SELECT size,modified FROM track_features WHERE path=?", (path,)).fetchone()
        if old == (size,modified):
            continue
        cmd = ["sudo","-n","nice","-n","15","ffmpeg","-nostdin","-hide_banner","-nostats",
               "-threads","1","-t","30","-i",path,
               "-af","ebur128=peak=true","-f","null","-"]
        try:
            proc=subprocess.run(cmd,capture_output=True,text=True,timeout=90,check=True)
            out=proc.stderr
            summary=out.rsplit("Summary:",1)[-1]
            loud=re.search(r"I:\s*(-?[0-9.]+) LUFS",summary)
            span=re.search(r"LRA:\s*([0-9.]+) LU",summary)
            if not loud or not span: raise ValueError("Misure LUFS/LRA non disponibili")
            rms,peak=db.execute("SELECT rms,peak FROM tracks WHERE path=?",(path,)).fetchone()
            db.execute("""INSERT INTO track_features VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(path) DO UPDATE SET
                       size=excluded.size,modified=excluded.modified,
                       integrated_lufs=excluded.integrated_lufs,
                       loudness_range=excluded.loudness_range,
                       rms_db=excluded.rms_db,peak_db=excluded.peak_db,
                       analyzed_at=excluded.analyzed_at""",
                       (path,size,modified,float(loud.group(1)),float(span.group(1)),rms,peak,dt.datetime.now(dt.timezone.utc).isoformat()))
            db.commit()
            done+=1
            print(f"{pathlib.Path(path).name[:48]} | {loud.group(1)} LUFS | dinamica {span.group(1)} LU")
        except Exception as e:
            print(f"ERRORE {pathlib.Path(path).name[:48]}: {e}")
    print("Misure supplementari salvate:",done)
    print("Brani con misure complete:",db.execute("SELECT count(*) FROM track_features").fetchone()[0])
    print("Nessuna playlist modificata")

if __name__=="__main__": main()
