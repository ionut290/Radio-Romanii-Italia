#!/usr/bin/env python3
"""RDI AI DJ: offline YAMNet ONNX tagging of a deterministic 100-song sample.

Apache-2.0 YAMNet / AudioSet CC BY 4.0 label map, provided by audiomagic.
Inference is NOT a reliable genre oracle or a singing source separator.
Reads decoded audio from station media, never writes any music or playlists.
CPU only, short staggered windows, bounded samples, independent SQLite table.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
DB=Path.home()/"rdi-music"/"music.db"
MODEL=ROOT/"models"/"yamnet.onnx"
LABELS=ROOT/"models"/"yamnet_class_map.csv"
MODEL_ID="yamnet-google-v1-audiomagic-f25b741"
MODEL_SHA256="d3835ffbbd4a1bb3e777f0ca217b5007907f5171dd5d17c4236b95b2af8f908e"
# Official AudioSet categories, broad categories only. Never advertise "trap"
# or other styles not covered by the model's own taxonomy.
GENRE_LABELS={
 "pop":("Pop music",),
 "urban":("Hip hop music",),
 "dance":("Disco","Electronic music","House music","Techno","Dubstep",
          "Drum and bass","Electronica","Electronic dance music","Trance music","Afrobeat"),
 "rnb_soul":("Rhythm and blues","Soul music","Funk"),
 "rock":("Rock music","Heavy metal","Punk rock","Grunge","Progressive rock",
          "Rock and roll","Psychedelic rock"),
 "jazz_lounge":("Jazz","Swing music","Ambient music","New-age music"),
 "acoustic":("Folk music","Country","Bluegrass"),
 "classical":("Classical music","Opera"),
 "latin":("Music of Latin America","Salsa music","Flamenco"),
 "reggae":("Reggae","Ska"),
 "blues":("Blues",)
}
VOCAL_CATEGORIES=("Singing","Vocal music","A capella","Rapping")
SPEECH_CATEGORIES=("Speech","Narration, monologue")
MUSIC_CATEGORIES=("Music","Song","Musical instrument","Background music")
# 3 non-adjacent segments, no complete audio is retained or transmitted.
OFFSETS=(8,49,97)
SECONDS=7.0
RATE=16000

def model_integrity(model=MODEL):
    if not model.exists() or not 10_000_000<=model.stat().st_size<=26_000_000:
        raise RuntimeError("Missing or unexpected YAMNet ONNX model")
    hasher=hashlib.sha256()
    with model.open("rb") as fp:
        for block in iter(lambda:fp.read(1024*1024),b""):
            hasher.update(block)
    digest=hasher.hexdigest()
    if digest!=MODEL_SHA256:
        raise RuntimeError("YAMNet model SHA256 mismatch")
    return digest

def class_names(path=LABELS):
    with path.open(newline="",encoding="utf-8") as fp:
        records=list(csv.DictReader(fp))
    if len(records)!=521:
        raise ValueError("Expected precisely 521 AudioSet labels")
    labels={int(r["index"]):str(r["display_name"]).strip() for r in records}
    if (labels.get(0),labels.get(24),labels.get(211),labels.get(212))!=(
        "Speech","Singing","Pop music","Hip hop music"):
        raise ValueError("YAMNet class labels are not the expected ontology")
    if len(labels)!=521 or set(labels)!=set(range(521)):
        raise ValueError("Invalid AudioSet class index coverage")
    return labels

def decisions(event_scores:dict[str,float]) -> dict:
    """Calibrated-as-hints only: AudioSet scores aren't genre probabilities."""
    genres=[]
    for group,labels in GENRE_LABELS.items():
        highest=max((event_scores.get(label,0.) for label in labels),default=0.)
        if highest>0:
            genres.append((group,float(highest)))
    genres.sort(key=lambda v:v[1],reverse=True)
    score=genres[0][1] if genres else 0.
    runner_up=genres[1][1] if len(genres)>1 else 0.
    # The threshold + small margin makes low scores explicitly inconclusive.
    genre=genres[0][0] if score>=0.16 and score>=runner_up+0.025 else "non_identificato"
    genre_score=round(score,3)
    singing=max((event_scores.get(x,0.) for x in VOCAL_CATEGORIES),default=0.)
    speech=max((event_scores.get(x,0.) for x in SPEECH_CATEGORIES),default=0.)
    music=max((event_scores.get(x,0.) for x in MUSIC_CATEGORIES),default=0.)
    if singing>=0.21:
        voice="cantato_probabile"
    elif speech>=0.28 and music<0.20:
        voice="parlato_da_verificare"
    elif singing<0.025 and speech<0.06 and music>=0.45:
        voice="strumentale_probabile"
    else:
        voice="non_verificato"
    top=sorted(event_scores.items(),key=lambda x:x[1],reverse=True)[:5]
    return {"genre_ai":genre,"genre_score":genre_score,
            "voice_ai":voice,"voice_score":round(float(singing),3),
            "music_score":round(float(music),3),
            "top_events":[{"label":k,"score":round(float(v),3)} for k,v in top],
            "model":MODEL_ID}

def extract(path:str, offset:int, ffmpeg="ffmpeg"):
    # Paths come ONLY from local SQLite inventory, not from web or user URLs.
    # sudo permits reading station Docker media, not modifying it.
    cmd=["sudo","-n","nice","-n","15",ffmpeg,"-nostdin","-v","error",
         "-threads","1","-ss",str(offset),"-t",str(SECONDS),
         "-i",path,"-vn","-ac","1","-ar",str(RATE),
         "-f","f32le","-acodec","pcm_f32le","-"]
    proc=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                        timeout=32,check=False)
    if proc.returncode:
        raise RuntimeError("Audio decode error ("+str(proc.returncode)+")")
    import numpy as np
    arr=np.frombuffer(proc.stdout,dtype="<f4")
    if arr.size<16000*3 or arr.size>16000*9:
        raise RuntimeError("Empty, too short or malformed audio sample")
    return arr

def analyze_one(session,path,names) -> dict:
    import numpy as np
    scores_accum=[]
    for offset in OFFSETS:
        try:
            waveform=extract(path,offset)
        except RuntimeError:
            continue
        scores=session.run(["output_0"],{"waveform":waveform})[0]
        if scores.ndim!=2 or scores.shape[1]!=521 or not np.all(np.isfinite(scores)):
            raise ValueError("Unexpected YAMNet classification matrix")
        # Keep the mean over each window so longer windows aren't overweighted.
        scores_accum.append(np.mean(scores,axis=0))
    if not scores_accum:
        raise RuntimeError("No segment available for model evaluation")
    overall=np.mean(np.stack(scores_accum),axis=0)
    return decisions({names[i]:float(overall[i]) for i in range(521)})

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS track_ai (
        path TEXT PRIMARY KEY,size INTEGER,modified REAL,model_id TEXT,
        genre_ai TEXT,genre_score REAL,voice_ai TEXT,voice_score REAL,
        music_score REAL,top_events TEXT,analyzed_at TEXT)""")
    db.commit()

def sample_paths(db, sample_size=100, live_paths=None):
    # Deterministic pseudo-random sample, independent of filenames and time.
    # Restricting to a freshly enumerated live library prevents stale paths from
    # the previously cached SQLite scan producing 100 failed FFmpeg attempts.
    from rdi_music_dj import excluded
    raw=db.execute("SELECT path,size,modified FROM tracks").fetchall()
    filtered=[x for x in raw if not excluded(x[0]) and
              (live_paths is None or x[0] in live_paths)]
    return sorted(filtered,key=lambda x:hashlib.sha256(x[0].encode("utf-8","surrogateescape")).hexdigest())[:sample_size]

def run(limit=100,sample_size=100):
    if not DB.is_file():
        raise RuntimeError("No existing scanned station music DB")
    model_integrity()
    names=class_names()
    import onnxruntime as ort
    options=ort.SessionOptions()
    options.intra_op_num_threads=1
    options.inter_op_num_threads=1
    options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    session=ort.InferenceSession(str(MODEL),sess_options=options,providers=["CPUExecutionProvider"])
    inputs=session.get_inputs()
    if len(inputs)!=1 or inputs[0].name!="waveform":
        raise RuntimeError("YAMNet model input incompatibility")
    db=sqlite3.connect(DB,timeout=20)
    try:
        init(db)
        # Oracle's media container moved some of the old root inventory; do
        # NOT rely on a cached Docker volume path. Probe paths directly with
        # sudo stat, like the existing RDI scanner, and select 100 real files.
        ordered=sample_paths(db,100000)
        selected=[]
        inspected=0
        for candidate in ordered:
            inspected+=1
            path,size,modified=candidate
            try:
                stat=subprocess.run(["sudo","-n","stat","-c","%s %Y","--",path],
                                    capture_output=True,text=True,timeout=8,check=False)
                if stat.returncode:
                    continue
                fields=stat.stdout.strip().split()
                if len(fields)!=2 or int(fields[0])!=int(size):
                    continue
                selected.append(candidate)
                if len(selected)>=sample_size:
                    break
            except (OSError,subprocess.TimeoutExpired,ValueError):
                continue
        if not selected:
            raise RuntimeError("No real audio tracks remain at their inventoried file paths")
        print("AI_CACHED_PATHS_INSPECTED="+str(inspected),flush=True)
        print("AI_SAMPLE_CURRENT_FILES="+str(len(selected)),flush=True)
        analyzed=0
        skipped=0
        failed=0
        for path,size,modified in selected:
            old=db.execute("SELECT size,modified,model_id FROM track_ai WHERE path=?",(path,)).fetchone()
            if old==(size,modified,MODEL_ID):
                skipped+=1
                continue
            if analyzed>=limit:
                break
            try:
                prediction=analyze_one(session,path,names)
                db.execute("""INSERT INTO track_ai VALUES(?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT(path) DO UPDATE SET
                     size=excluded.size,modified=excluded.modified,model_id=excluded.model_id,
                     genre_ai=excluded.genre_ai,genre_score=excluded.genre_score,
                     voice_ai=excluded.voice_ai,voice_score=excluded.voice_score,
                     music_score=excluded.music_score,top_events=excluded.top_events,
                     analyzed_at=excluded.analyzed_at""",
                    (path,size,modified,MODEL_ID,prediction["genre_ai"],prediction["genre_score"],
                     prediction["voice_ai"],prediction["voice_score"],prediction["music_score"],
                     json.dumps(prediction["top_events"],ensure_ascii=False),
                     dt.datetime.now(dt.timezone.utc).isoformat()))
                db.commit()
                analyzed+=1
                print("AI_SAMPLE_ANALYZED="+str(analyzed)+" GENRE="+prediction["genre_ai"]+
                      " VOICE="+prediction["voice_ai"],flush=True)
            except Exception as ex:
                failed+=1
                print("AI_SAMPLE_FAILED="+type(ex).__name__,file=sys.stderr,flush=True)
                if failed>=10:
                    raise RuntimeError("Too many failed local media decodes") from None
        total=sum(1 for path,size,modified in selected if db.execute(
            "SELECT 1 FROM track_ai WHERE path=? AND size=? AND modified=? AND model_id=?",
            (path,size,modified,MODEL_ID)).fetchone())
        print("AI_TARGET_SAMPLE="+str(len(selected)))
        print("AI_SAMPLE_TOTAL_DONE="+str(total))
        print("AI_SAMPLE_NEW="+str(analyzed))
        print("AI_SAMPLE_FAILED="+str(failed))
        print("AI_PLAYLIST_WRITES=0")
        return total
    finally:
        db.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--limit",type=int,default=100)
    p.add_argument("--sample-size",type=int,default=100)
    a=p.parse_args()
    run(max(1,min(a.limit,100)),max(1,min(a.sample_size,100)))

if __name__=="__main__":
    main()
