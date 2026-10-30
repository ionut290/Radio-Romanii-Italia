#!/usr/bin/env python3
"""RDI: lightweight, tentative pulse analysis of audio already inventoried.
Read-only on media and AzuraCast. Never changes playlists.
BPM candidate comes from autocorrelation of short-term energy changes;
it is NOT a reliable genre/emotion detector, and half/double tempo is possible.
"""
import argparse
import array
import datetime as dt
import math
import os
import pathlib
import sqlite3
import subprocess
import sys

DB = pathlib.Path.home() / "rdi-music" / "music.db"
RATE = 8000
HOP = 800  # 100ms; 10 envelope points/second

def estimate(path):
    prefix=[] if os.geteuid()==0 else ["sudo","-n"]
    command = prefix+["nice", "-n", "15", "ffmpeg",
               "-nostdin", "-v", "error", "-threads", "1",
               "-t", "45", "-i", path, "-vn", "-ac", "1", "-ar", str(RATE),
               "-f", "s16le", "-acodec", "pcm_s16le", "-"]
    r = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       timeout=100, check=True)
    pcm = array.array("h")
    pcm.frombytes(r.stdout[:len(r.stdout)//2*2])
    if sys.byteorder != "little":
        pcm.byteswap()
    energies = []
    for start in range(0, len(pcm)-HOP+1, HOP):
        chunk = pcm[start:start+HOP]
        energies.append(math.sqrt(sum(x*x for x in chunk)/HOP))
    if len(energies) < 200:
        raise ValueError("Audio troppo corto per stimare il ritmo")
    # Relative positive energy changes are more useful than absolute loudness.
    onset = [max(0.0, energies[i] - energies[i-1]) for i in range(1,len(energies))]
    avg = sum(onset)/len(onset)
    centered = [x-avg for x in onset]
    power = sum(x*x for x in centered)
    if power < 1e-9:
        return None, 0.0, 0.0
    # Lag 4..9 at 10Hz covers 67..150 BPM; search 60..180 BPM.
    results=[]
    for lag in range(3,11):
        numerator = sum(centered[i]*centered[i-lag] for i in range(lag,len(centered)))
        a = sum(x*x for x in centered[lag:])
        b = sum(x*x for x in centered[:-lag])
        corr = numerator/math.sqrt(a*b) if a*b else 0.0
        results.append((corr, lag))
    score, lag = max(results)
    bpm = round(600/lag, 1) if score >= 0.10 else None
    # variation in slow energy envelope; not an emotion label
    avg_energy = sum(energies)/len(energies)
    variation = (math.sqrt(sum((x-avg_energy)**2 for x in energies)/len(energies))
                 / avg_energy) if avg_energy else 0.0
    return bpm, round(max(0.0,score), 3), round(variation,3)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--limit",type=int,default=3)
    a=p.parse_args()
    db=sqlite3.connect(DB)
    db.execute("""CREATE TABLE IF NOT EXISTS track_rhythm (
        path TEXT PRIMARY KEY, size INTEGER, modified REAL,
        bpm_candidate REAL, beat_score REAL, energy_variation REAL,
        analyzed_at TEXT)""")
    count=0
    for path,size,modified in db.execute(
        "SELECT path,size,modified FROM tracks ORDER BY analyzed_at ASC").fetchall():
        if count>=max(1,min(10,a.limit)): break
        exists=db.execute("SELECT size,modified FROM track_rhythm WHERE path=?",(path,)).fetchone()
        if exists==(size,modified): continue
        try:
            bpm,score,variation=estimate(path)
            db.execute("""INSERT INTO track_rhythm VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(path) DO UPDATE SET
               size=excluded.size, modified=excluded.modified,
               bpm_candidate=excluded.bpm_candidate,beat_score=excluded.beat_score,
               energy_variation=excluded.energy_variation,
               analyzed_at=excluded.analyzed_at""",
               (path,size,modified,bpm,score,variation,dt.datetime.now(dt.timezone.utc).isoformat()))
            db.commit()
            count+=1
            candidate=f"{bpm} BPM (ipotesi)" if bpm is not None else "ritmo incerto"
            print(f"{pathlib.Path(path).name[:48]} | {candidate} | indice {score:.3f} | variazione {variation:.3f}")
        except Exception as e:
            print(f"Saltato {pathlib.Path(path).name[:48]}: {e}",file=sys.stderr)
    print("Nuove analisi ritmiche:",count)
    print("Brani con analisi ritmica:",db.execute("SELECT COUNT(*) FROM track_rhythm").fetchone()[0])
    print("Nessuna playlist modificata.")
if __name__=="__main__":
    main()
