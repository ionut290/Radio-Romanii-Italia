#!/usr/bin/env python3
"""RDI audio inventory: read-only media inspection, cached in SQLite."""
import argparse
import os
import datetime as dt
import pathlib
import re
import sqlite3
import subprocess
import sys

MEDIA = "/var/lib/docker/volumes/azuracast_station_data/_data/radio-romanii-italia/media"
DB = pathlib.Path.home() / "rdi-music" / "music.db"
EXTENSIONS = (".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac")
EXCLUDED = {"spot", "riflessioni sul diaspora", "riflessione sulla diaspora", ".albumart"}

def run(args, timeout):
    return subprocess.run(args, capture_output=True, check=True, timeout=timeout)

def inventory():
    prefix=[] if os.geteuid()==0 else ["sudo","-n"]
    data = run(prefix+["find", MEDIA, "-type", "f", "-print0"], 45).stdout
    for raw in data.split(b"\0"):
        if not raw:
            continue
        path = pathlib.Path(raw.decode("utf-8", "surrogateescape"))
        if path.suffix.lower() not in EXTENSIONS:
            continue
        rel = path.relative_to(MEDIA)
        if any(part.casefold() in EXCLUDED or part.startswith(".") for part in rel.parts[:-1]):
            continue
        yield str(path)

def analyze(path):
    prefix=[] if os.geteuid()==0 else ["sudo","-n"]
    p = run(prefix+["nice", "-n", "15", "ffmpeg", "-nostdin",
             "-hide_banner", "-nostats", "-threads", "1", "-t", "25",
             "-i", path, "-vn", "-af", "volumedetect", "-f", "null", "-"], 100)
    output = p.stderr.decode("utf-8", "replace")
    mean = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", output)
    peak = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", output)
    if not mean or not peak:
        raise RuntimeError("Volume non rilevato")
    return float(mean[1]), float(peak[1])

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args()
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS tracks (path TEXT PRIMARY KEY, size INTEGER, modified REAL, rms REAL, peak REAL, category TEXT, analyzed_at TEXT)")
    paths = list(inventory())
    print(f"File musicali trovati (esclusi spot/podcast): {len(paths)}")
    inspected = 0
    for path in paths:
        if inspected >= max(1, min(args.limit, 10)):
            break
        try:
            # Ask root to read metadata; the volume is private to Docker.
            prefix=[] if os.geteuid()==0 else ["sudo","-n"]
            result = run(prefix+["stat", "-c", "%s %Y", "--", path], 10)
            size, modified = (int(x) for x in result.stdout.split())
            previous = conn.execute("SELECT size,modified FROM tracks WHERE path=?", (path,)).fetchone()
            if previous and previous == (size, float(modified)):
                continue
            mean, peak = analyze(path)
            conn.execute("INSERT INTO tracks (path,size,modified,rms,peak,category,analyzed_at) VALUES (?,?,?,?,?,?,?) "
                         "ON CONFLICT(path) DO UPDATE SET size=excluded.size,modified=excluded.modified,rms=excluded.rms,peak=excluded.peak,category=excluded.category,analyzed_at=excluded.analyzed_at",
                         (path, size, float(modified), mean, peak, "da_verificare", dt.datetime.now(dt.timezone.utc).isoformat()))
            conn.commit()
            inspected += 1
            print(f"Analizzato: {pathlib.Path(path).name[:55]} | medio {mean} dB | picco {peak} dB")
        except Exception as exc:
            print(f"Saltato {pathlib.Path(path).name[:55]}: {exc}", file=sys.stderr)
    total = conn.execute("SELECT COUNT(*) FROM tracks").fetchone()[0]
    print(f"Nuovi analizzati: {inspected}; registrati nel database: {total}. Nessuna playlist modificata.")

if __name__ == "__main__":
    main()
