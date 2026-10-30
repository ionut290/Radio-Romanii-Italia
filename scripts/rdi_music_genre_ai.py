#!/usr/bin/env python3
"""RDI: optional second, specialist GTZAN genre estimator (CPU ONNX, local only).

MODEL: onnx-community/ast-finetuned-gtzan-ONNX, BSD-3-Clause.
MODEL ARCH: MIT/AST, fine-tuned on GTZAN with only 10 historical genre
classes. Predictions are not ground truth, especially for modern urban subgenres.
No radio API calls, no playlist or audio file mutation.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT=Path(__file__).resolve().parent
DB=Path.home()/"rdi-music/music.db"
MODEL=ROOT/"models"/"ast-gtzan-q4.onnx"
PREPROCESSOR=ROOT/"models"/"ast-preprocessor"
MODEL_SHA256="e065d352521c32bf9ddda62c3b4aa9effab003533c0f0b367befaa7b68b0cd51"
MODEL_ID="ast-gtzan-onnx-q4-7f313d5"
LABELS=("blues","classical","country","disco","hiphop","jazz","metal","pop","reggae","rock")
BROAD={
    "blues":"blues","classical":"classical","country":"acoustic",
    "disco":"dance","hiphop":"urban","jazz":"jazz_lounge","metal":"rock",
    "pop":"pop","reggae":"reggae","rock":"rock"
}
# "trap" and "R&B" aren't classes in GTZAN; never claim to recognize them.
DURATION=22
OFFSET=35


def verify_model():
    if not MODEL.is_file() or not 45_000_000 < MODEL.stat().st_size < 80_000_000:
        raise RuntimeError("No validated AST genre ONNX model available")
    h=hashlib.sha256()
    with MODEL.open("rb") as fp:
        for chunk in iter(lambda:fp.read(1_048_576),b""):
            h.update(chunk)
    if h.hexdigest()!=MODEL_SHA256:
        raise ValueError("AST genre model SHA256 mismatch")
    config=json.loads((PREPROCESSOR/"preprocessor_config.json").read_text())
    if (config.get("feature_extractor_type"),config.get("sampling_rate"),
        config.get("max_length"),config.get("num_mel_bins"))!=(
        "ASTFeatureExtractor",16000,1024,128):
        raise ValueError("AST audio preprocessor configuration changed")


def decide(logits):
    """Return conservative, labeled estimate. Softmax is not calibrated accuracy."""
    import numpy as np
    vec=np.asarray(logits,dtype=np.float64).reshape(-1)
    if vec.size!=10 or not np.isfinite(vec).all():
        raise ValueError("Genre model must return 10 finite logits")
    scores=np.exp(vec-np.max(vec))
    scores/=np.sum(scores)
    idx=list(np.argsort(-scores))
    first,second=int(idx[0]),int(idx[1])
    top=float(scores[first]); margin=top-float(scores[second])
    trusted=top>=0.55 and margin>=0.20
    return {"genre":BROAD[LABELS[first]] if trusted else "non_identificato",
            "candidate":LABELS[first],"score":round(top,3),
            "alternative":LABELS[second],"margin":round(margin,3),
            "needs_review":True,"model":MODEL_ID}

def decode(path):
    import numpy as np
    prefix=[] if os.geteuid()==0 else ["sudo","-n"]
    cmd=prefix+["nice","-n","15","ffmpeg","-nostdin","-v","error",
        "-threads","1","-ss",str(OFFSET),"-t",str(DURATION),"-i",path,
        "-vn","-ar","16000","-ac","1","-f","f32le",
        "-acodec","pcm_f32le","-"]
    out=subprocess.run(cmd,capture_output=True,timeout=40,check=False)
    if out.returncode:
        raise RuntimeError("Local genre audio decoding failed")
    audio=np.frombuffer(out.stdout,dtype="<f4")
    if audio.size<16000*5 or audio.size>16000*25:
        raise ValueError("Too short or malformed genre sample")
    return audio

def current_samples(db, sample_size):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='track_ai'").fetchone():
        raise RuntimeError("YAMNet pilot dataset missing")
    # Analyze exactly the same validated, already decoded 100 local tracks.
    rows=db.execute(
        "SELECT path,size,modified FROM track_ai WHERE model_id=? ORDER BY path",
        ("yamnet-google-v1-audiomagic-f25b741",)).fetchall()
    return rows[:min(sample_size,100)]

def run(limit=100):
    verify_model()
    import onnxruntime as ort
    from transformers import ASTFeatureExtractor
    feature=ASTFeatureExtractor.from_pretrained(str(PREPROCESSOR),local_files_only=True)
    opts=ort.SessionOptions()
    opts.intra_op_num_threads=1
    opts.inter_op_num_threads=1
    opts.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    opts.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_BASIC
    model=ort.InferenceSession(str(MODEL),sess_options=opts,providers=["CPUExecutionProvider"])
    input_name=model.get_inputs()[0].name
    db=sqlite3.connect(DB,timeout=30)
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS track_gtzan (
         path TEXT PRIMARY KEY,size INTEGER,modified REAL,model_id TEXT,
         genre TEXT,candidate TEXT,score REAL,alternative TEXT,margin REAL,analyzed_at TEXT
         )""")
        db.commit()
        rows=current_samples(db,100)
        if len(rows)<80:
            raise RuntimeError("First pilot must contain most of the 100 analyzed YAMNet tracks")
        done=0
        failures=0
        for path,size,modified in rows:
            old=db.execute("SELECT size,modified,model_id FROM track_gtzan WHERE path=?",(path,)).fetchone()
            if old==(size,modified,MODEL_ID):
                continue
            if done>=limit:
                break
            try:
                audio=decode(path)
                inputs=feature(audio,sampling_rate=16000,return_tensors="np")["input_values"]
                if inputs.shape!=(1,1024,128):
                    raise ValueError("Incorrect AST audio feature shape")
                scores=model.run(None,{input_name:inputs.astype("float32")})[0]
                res=decide(scores)
                db.execute("""INSERT INTO track_gtzan VALUES(?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(path) DO UPDATE SET size=excluded.size,modified=excluded.modified,
                  model_id=excluded.model_id,genre=excluded.genre,candidate=excluded.candidate,
                  score=excluded.score,alternative=excluded.alternative,
                  margin=excluded.margin,analyzed_at=excluded.analyzed_at""",
                  (path,size,modified,MODEL_ID,res["genre"],res["candidate"],res["score"],
                   res["alternative"],res["margin"],dt.datetime.now(dt.timezone.utc).isoformat()))
                db.commit()
                done+=1
                print("GTZAN_SAMPLE_DONE="+str(done)+" GENRE="+res["candidate"]+
                      " VETTED="+str(res["genre"]!="non_identificato"),flush=True)
            except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as ex:
                failures+=1
                print("GTZAN_DECODE_FAIL="+type(ex).__name__,file=sys.stderr,flush=True)
                if failures>=8:
                    raise RuntimeError("Too many specialist genre classification errors") from None
        counts=db.execute(
            "SELECT COUNT(*),SUM(CASE WHEN genre!='non_identificato' THEN 1 ELSE 0 END) FROM track_gtzan WHERE model_id=?",
            (MODEL_ID,)).fetchone()
        print("GTZAN_TOTAL_ANALYZED="+str(counts[0]))
        print("GTZAN_CONFIDENT_GENRES="+str(counts[1] or 0))
        print("GTZAN_PLAYLIST_WRITES=0")
    finally:
        db.close()

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--limit",type=int,default=100)
    a=p.parse_args()
    run(max(1,min(a.limit,100)))

if __name__=="__main__":
    main()
