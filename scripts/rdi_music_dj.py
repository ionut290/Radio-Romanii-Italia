#!/usr/bin/env python3
"""RDI Music DJ: conservative metadata + audio based radio programming suggestions.

No AzuraCast API authentication, no network and NO playlist writes.
Reuses the deployed read-only RDI scan, rhythm and LUFS analyzers.
All output remains on the local Oracle server.
"""
from __future__ import annotations
import argparse
import collections
import datetime as dt
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

HOME = Path.home() / "rdi-music"
DB = HOME / "music.db"
REPORT = HOME / "dj-report.json"
HTML = Path(__file__).resolve().parent / "rdi-music-dj.html"
ROOT = Path(__file__).resolve().parent
EXCLUDE = (
    "spot", "pubblicit", "advert", "jingle", "podcast", "notiziari",
    "notiziario", "geopolitica", "tg della sera", "tg-sera",
    "news bulletin", "riflessione", "riflessioni", "promo", "comedy",
    "bollettino", "meteo", "talk", "diretta", "intervista", "station id",
)
WORDS = re.compile(r"[\s._/\-]+")
GENRES = {
 "urban": ("urban","trap","hip hop","hiphop","rap","drill"),
 "pop": ("pop","indie pop","synthpop","synth pop","electropop"),
 "dance": ("dance","house","disco","edm","electronic","techno","afrobeat"),
 "rnb_soul": ("r&b","rnb","soul","neo soul","funk"),
 "rock": ("rock","alternative rock","indie rock","metal","punk"),
 "jazz_lounge": ("jazz","bossa","lounge","chillout","downtempo","ambient"),
 "acoustic": ("acoustic","folk","singer songwriter"),
 "classical": ("classical","orchestral","symphonic","piano solo"),
 "latin": ("latin","reggaeton","bachata","salsa"),
}
INSTRUMENTAL = re.compile(r"(?i)(?:\binstrumental\b|\binstrumentale\b|\bno vocals?\b|\bsenza voce\b|\bkaraoke\b)")
VOCAL = re.compile(r"(?i)(?:\bwith vocals?\b|\bvocal version\b|\bfeat\.?\b|\bft\.?\b|\bcantat[oa]\b)")
SLOTS = {
    "mattino_07_10": "Mattino · 07–10",
    "giorno_10_13": "Giorno · 10–13",
    "pomeriggio_13_17": "Pomeriggio · 13–17",
    "sera_18_21": "Sera · 18–21",
    "notte_21_07": "Notte · 21–07",
}


def excluded(path: str) -> bool:
    # Explicit exclusions cover folder names and known non-music titles.
    name = WORDS.sub(" ", Path(path).as_posix().casefold())
    return any(term in name for term in EXCLUDE)


def classify(genre: str, title: str, bpm, beat_score, loudness, dynamic) -> dict:
    """No made-up genre or singing detection: infer voice only from explicit metadata."""
    raw = (genre or "").strip()[:120]
    key = ""
    if raw:
        norm = raw.casefold().replace("-", " ")
        for label, synonyms in GENRES.items():
            if any(re.search(r"(?<!\w)" + re.escape(g) + r"(?!\w)", norm) for g in synonyms):
                key = label
                break
    hint = title + " " + raw
    voice = "strumentale_dichiarato" if INSTRUMENTAL.search(hint) else (
        "cantato_dichiarato" if VOCAL.search(hint) else "non_verificato")
    bpm_ok = bpm is not None and beat_score is not None and float(beat_score) >= 0.32
    bpm = round(float(bpm),1) if bpm_ok else None
    lufs_ok = loudness is not None and -50 < float(loudness) < -4
    lufs = round(float(loudness),1) if lufs_ok else None
    dyn = float(dynamic) if dynamic is not None else None
    # A relative estimate, not a music-genre recognition model.
    if not bpm_ok or not lufs_ok:
        energy = "non_verificata"
    elif bpm >= 115 and lufs >= -18 and (dyn is None or dyn <= 12):
        energy = "ritmata"
    elif bpm <= 90 and lufs <= -16:
        energy = "tranquilla"
    else:
        energy = "media"
    slots=[]
    if energy == "tranquilla":
        slots=["mattino_07_10","sera_18_21","notte_21_07"]
    elif energy == "ritmata":
        slots=["giorno_10_13","pomeriggio_13_17"]
    elif energy == "media":
        slots=["mattino_07_10","giorno_10_13","sera_18_21"]
    # Not an approved playlist assignment; a proposal to be reviewed.
    return {"genre":key or "non_identificato",
            "genre_source":"metadati_file" if key else "non_disponibile",
            "voice":voice,"bpm_candidate":bpm,
            "beat_confidence":round(float(beat_score),3) if bpm_ok else None,
            "lufs":lufs,"energy_estimate":energy,"suggested_slots":slots,
            "needs_review":True}


def query_tables(db: sqlite3.Connection) -> set[str]:
    return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def read_rows(db: sqlite3.Connection) -> list[sqlite3.Row]:
    if "tracks" not in query_tables(db):
        return []
    tables = query_tables(db)
    feature = "track_features" in tables
    rhythm = "track_rhythm" in tables
    tags = "track_tags" in tables
    q = """SELECT t.path,t.size,t.modified,t.rms,t.peak,
        {feat} AS integrated_lufs,{dyn} AS loudness_range,
        {bpm} AS bpm_candidate,{beat} AS beat_score,
        {genre} AS genre_tag,{title} AS title_tag,{artist} AS artist_tag
        FROM tracks t
        {join_f} {join_r} {join_g}
        ORDER BY t.analyzed_at DESC"""
    q = q.format(
      feat="f.integrated_lufs" if feature else "NULL",
      dyn="f.loudness_range" if feature else "NULL",
      bpm="r.bpm_candidate" if rhythm else "NULL",
      beat="r.beat_score" if rhythm else "NULL",
      genre="g.genre" if tags else "NULL",
      title="g.title" if tags else "NULL",
      artist="g.artist" if tags else "NULL",
      join_f="LEFT JOIN track_features f ON f.path=t.path AND f.size=t.size AND f.modified=t.modified" if feature else "",
      join_r="LEFT JOIN track_rhythm r ON r.path=t.path AND r.size=t.size AND r.modified=t.modified" if rhythm else "",
      join_g="LEFT JOIN track_tags g ON g.path=t.path AND g.size=t.size AND g.modified=t.modified" if tags else "",
    )
    return db.execute(q).fetchall()


def metadata_scan(db: sqlite3.Connection, limit: int) -> int:
    db.execute("""CREATE TABLE IF NOT EXISTS track_tags
        (path TEXT PRIMARY KEY, size INTEGER, modified REAL,
         genre TEXT, title TEXT, artist TEXT, analyzed_at TEXT)""")
    db.commit()
    tracked=0
    for path,size,modified in db.execute(
        "SELECT path,size,modified FROM tracks ORDER BY analyzed_at DESC").fetchall():
        if tracked >= limit:
            break
        if excluded(path):
            continue
        old=db.execute("SELECT size,modified FROM track_tags WHERE path=?",(path,)).fetchone()
        if old==(size,modified):
            continue
        try:
            proc=subprocess.run(
                ["sudo","-n","nice","-n","15","ffprobe","-v","error",
                "-show_entries","format_tags=genre,title,artist:stream_tags=genre,title,artist",
                "-of","json","-i",path],
                capture_output=True,text=True,timeout=18,check=True)
            payload=json.loads(proc.stdout[:200_000])
            tags=dict(payload.get("format",{}).get("tags") or {})
            for stream in payload.get("streams",[]):
                for k,v in (stream.get("tags") or {}).items():
                    tags.setdefault(k,v)
            tags={str(k).lower():str(v)[:300] for k,v in tags.items()}
            genre=tags.get("genre","")[:120]
            title=tags.get("title","")[:200]
            artist=tags.get("artist","")[:200]
            db.execute("""INSERT INTO track_tags VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(path) DO UPDATE SET size=excluded.size,modified=excluded.modified,
                genre=excluded.genre,title=excluded.title,artist=excluded.artist,
                analyzed_at=excluded.analyzed_at""",
                (path,size,modified,genre,title,artist,dt.datetime.now(dt.timezone.utc).isoformat()))
            db.commit()
            tracked+=1
        except (OSError,subprocess.SubprocessError,ValueError,TypeError) as exc:
            print("METADATA_SKIPPED="+type(exc).__name__,file=sys.stderr)
    return tracked


def report() -> dict:
    now=dt.datetime.now(dt.timezone.utc).isoformat()
    empty={"schema_version":1,"updated_at":now,"mode":"osservazione_senza_modifiche",
      "read_only":True,"playlist_writes":0,"total_inventoried":0,"total_music":0,
      "complete_audio_features":0,"with_genre_metadata":0,"voice_marked":0,
      "status":"attesa_scansione","slots":{k:[] for k in SLOTS},"tracks":[]}
    if not DB.is_file():
        return empty
    db=sqlite3.connect("file:"+str(DB)+"?mode=ro",uri=True)
    db.row_factory=sqlite3.Row
    rows=read_rows(db)
    db.close()
    tracks=[]
    slots=collections.defaultdict(list)
    stats=collections.Counter()
    for row in rows:
        if excluded(row["path"]):
            continue
        title=str(row["title_tag"] or Path(row["path"]).stem)[:100]
        item=classify(row["genre_tag"] or "",title,
            row["bpm_candidate"],row["beat_score"],
            row["integrated_lufs"],row["loudness_range"])
        item["id"]=hashlib.sha256(row["path"].encode("utf-8","surrogateescape")).hexdigest()[:16]
        item["title"]=title
        item["artist"]=str(row["artist_tag"] or "")[:90]
        item["ready_for_autodj"]=False
        item["reason"]="Revisione musicale necessaria prima di spostare il brano."
        if item["energy_estimate"]!="non_verificata":
            stats["complete"]+=1
        if row["genre_tag"]:
            stats["genre"]+=1
        if item["voice"]!="non_verificato":
            stats["voice"]+=1
        tracks.append(item)
        if item["suggested_slots"]:
            for key in item["suggested_slots"]:
                if len(slots[key]) < 25:
                    slots[key].append(item["id"])
    empty.update({"total_inventoried":len(rows),"total_music":len(tracks),
        "complete_audio_features":stats["complete"],
        "with_genre_metadata":stats["genre"],"voice_marked":stats["voice"],
        "status":"proposte_disponibili" if stats["complete"] else "analisi_in_corso",
        "slots":{k:slots[k] for k in SLOTS},
        # Full track details are private to Oracle loopback.
        "tracks":tracks[:500]})
    return empty


def save_report() -> dict:
    data=report()
    HOME.mkdir(mode=0o700,parents=True,exist_ok=True)
    dest=REPORT.with_suffix(".json.tmp")
    dest.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    dest.chmod(0o600)
    dest.replace(REPORT)
    return data


def pipeline(limit: int):
    # These pre-existing tools never modify AzuraCast playlists or audio.
    for name in ("rdi_music_scan.py","rdi_music_rhythm.py","rdi_music_features.py"):
        file=ROOT/name
        if not file.is_file():
            print("MISSING_ANALYZER="+name,file=sys.stderr)
            continue
        try:
            r=subprocess.run([sys.executable,str(file),"--limit",str(limit)],
                timeout=300,check=False)
            print("ANALYZER="+name+" STATUS="+str(r.returncode))
        except (OSError,subprocess.TimeoutExpired) as exc:
            print("ANALYZER_ERROR="+name+" "+type(exc).__name__,file=sys.stderr)
    if DB.is_file():
        db=sqlite3.connect(DB)
        done=metadata_scan(db,limit)
        db.close()
        print("META_ANALYZED="+str(done))
    data=save_report()
    print("MUSIC_INVENTORIED="+str(data["total_inventoried"]))
    print("MUSIC_TRACKS="+str(data["total_music"]))
    print("AUDIO_FEATURES_READY="+str(data["complete_audio_features"]))
    print("METADATA_GENRE="+str(data["with_genre_metadata"]))
    print("MUSIC_DJ_MODE=READ_ONLY_NO_PLAYLIST_WRITES")


class Handler(BaseHTTPRequestHandler):
    server_version="RDIMusicDJ/1"
    def do_GET(self):
        path=self.path.partition("?")[0]
        if path=="/":
            target=HTML
            typ="text/html; charset=utf-8"
        elif path=="/api/report":
            target=REPORT
            typ="application/json; charset=utf-8"
        else:
            self.send_error(404)
            return
        try:
            data=target.read_bytes()
        except OSError:
            self.send_error(503)
            return
        self.send_response(200)
        self.send_header("Content-Type",typ)
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Content-Security-Policy","default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'self'")
        self.send_header("Content-Length",str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self,*args):
        pass
    def do_POST(self):
        self.send_error(405)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=["run","report","serve"],nargs="?",default="report")
    parser.add_argument("--limit",type=int,default=3)
    args=parser.parse_args()
    if args.action=="run":
        pipeline(max(1,min(args.limit,10)))
    elif args.action=="report":
        data=save_report()
        print(json.dumps({k:v for k,v in data.items() if k not in ("tracks","slots")},ensure_ascii=False))
    else:
        ThreadingHTTPServer(("127.0.0.1",8788),Handler).serve_forever()

if __name__=="__main__":
    main()
