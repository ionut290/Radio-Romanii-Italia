#!/usr/bin/env python3
"""RDI AI MUSIC Top 3: build a single, synchronized broadcast MP3.

This script only reads approved, explicitly YouTube-authorized audio from RDI.
It never edits the radio station or starts the YouTube stream.
"""
from __future__ import annotations
import argparse, asyncio, datetime, json, pathlib, re, subprocess, urllib.request
from zoneinfo import ZoneInfo

API="https://radio-romanii-italia.duckdns.org/api/ai-music"
ROOT=pathlib.Path("/tmp/rdi-ai-top3")
TIMEOUT=35
VOICE="it-IT-DiegoNeural"
ROME=ZoneInfo("Europe/Rome")
ID=re.compile(r"^[0-9a-f]{32}$")

def run(*args):
    subprocess.run(args,check=True,stdout=subprocess.DEVNULL,timeout=250)

def probe(path):
    p=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
         "-of","default=noprint_wrappers=1:nokey=1",str(path)],
         capture_output=True,text=True,timeout=25,check=True)
    duration=float(p.stdout.strip())
    if not 0.2<duration<3600: raise ValueError("Invalid audio duration")
    return duration

def get_json(url):
    req=urllib.request.Request(url,headers={"User-Agent":"RDI-Top3-Audio/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as f:
        return json.loads(f.read(120_000))

def download(id_,destination):
    if not ID.fullmatch(id_):raise ValueError("Invalid track identifier")
    req=urllib.request.Request(API+"/spotlight/"+id_+"/audio",
            headers={"User-Agent":"RDI-Top3-Audio/1.0"})
    with urllib.request.urlopen(req,timeout=TIMEOUT) as f,open(destination,"wb") as dst:
        if f.status!=200: raise RuntimeError("Audio unavailable")
        limit=40*1024*1024
        while True:
            chunk=f.read(1024*1024)
            if not chunk:break
            limit-=len(chunk)
            if limit<0:raise ValueError("Audio exceeds authorized source limit")
            dst.write(chunk)
    if not 1000<destination.stat().st_size<40*1024*1024:
        raise ValueError("Missing source audio data")
    probe(destination)

async def say(message,destination):
    import edge_tts
    await edge_tts.Communicate(message,VOICE,rate="-4%").save(str(destination))
    probe(destination)

def normalized(src,dst):
    run("ffmpeg","-hide_banner","-loglevel","error","-y",
        "-i",str(src),"-vn",
        "-af","aresample=44100,loudnorm=I=-17:LRA=10:TP=-1.5",
        "-ac","2","-ar","44100","-c:a","libmp3lame","-b:a","128k",
        "-id3v2_version","3",str(dst))
    return probe(dst)

def speech_for(rank,track):
    position={3:"al terzo posto",2:"al secondo posto",1:"al primo posto"}[rank]
    title=re.sub(r"[^\w \-',.!?àèéìòùÀÈÉÌÒÙ]", " ",track["title"])[:140].strip()
    artist=re.sub(r"[^\w \-',.!?àèéìòùÀÈÉÌÒÙ]", " ",track["artist"])[:100].strip()
    return f"E ora, {position} della classifica Erre Di I Ai Music Spotlight: {title}, di {artist}. Ascoltiamola!"

def produce(folder,now=None):
    now=now or datetime.datetime.now(ROME)
    folder.mkdir(parents=True,exist_ok=True)
    item=get_json(API+"/top3/authorized")
    tracks=item.get("tracks")
    if not item.get("ready") or not isinstance(tracks,list) or len(tracks)!=3:
        raise RuntimeError("Three approved, original-audio tracks with explicit YouTube consent are required")
    for t in tracks:
        if not ID.fullmatch(str(t.get("id",""))) or not t.get("title") or not t.get("artist"):
            raise ValueError("Invalid authorized track")
    if len(set(x["id"] for x in tracks))!=3:raise ValueError("Duplicate tracks")
    reversed_top=list(reversed(tracks))
    codes=["intro","number3","number2","number1","outro"]
    names=["Erre Di I Ai Music Spotlight! Benvenuti alla Top tre del giorno. La classifica scelta dalla community!",
           *(speech_for(rank,t) for rank,t in zip([3,2,1],reversed_top)),
           "Questa era la Top tre di Erre Di I Ai Music Spotlight! Ascolta, vota e scopri i nuovi artisti su radioromanii punto duck d n s punto org!"]
    async def create_speech():
        for code,script in zip(codes,names):
            await say(script,folder/(code+"-voice.mp3"))
    asyncio.run(create_speech())
    edition_day=now.strftime("%Y-%m-%d")
    title="RDI-AI-TOP3-"+now.strftime("%Y%m%d")
    pieces=[("intro",folder/"intro-voice.mp3")]
    for rank,track in zip([3,2,1],reversed_top):
        source=folder/(track["id"]+"-source.mp3")
        download(track["id"],source)
        pieces.append(("number"+str(rank),folder/("number"+str(rank)+"-voice.mp3")))
        pieces.append(("song"+str(rank),source))
    pieces.append(("outro",folder/"outro-voice.mp3"))
    t=0.0
    normalized_files=[]
    parts={}
    for index,(label,source) in enumerate(pieces):
        target=folder/f"clip-{index:02d}.mp3"
        length=normalized(source,target)
        parts[label]=(t,t+length)
        t+=length
        normalized_files.append(target)
    segments=[]
    for rank,track in zip([3,2,1],reversed_top):
        begin=parts["number"+str(rank)][0]
        music_start=parts["song"+str(rank)][0]
        finish=parts["song"+str(rank)][1]
        segments.append({"id":track["id"],"rank":rank,
            "title":track["title"],"artist":track["artist"],"votes":int(track["votes"]),
            "start":round(begin,2),"music_start":round(music_start,2),"end":round(finish,2)})
    listfile=folder/"concat.txt"
    listfile.write_text("".join("file '"+str(p.resolve())+"'\n" for p in normalized_files),encoding="utf-8")
    dest=folder/(title+".mp3")
    run("ffmpeg","-hide_banner","-loglevel","error","-y",
         "-f","concat","-safe","0","-i",str(listfile),"-c:a","copy",
         "-metadata","title="+title,"-metadata","artist=RDI AI MUSIC",
         "-metadata","album=RDI AI MUSIC - Top 3",
         "-id3v2_version","3",str(dest))
    actual=probe(dest)
    if abs(actual-t)>3:raise ValueError("Final audio timing mismatch")
    manifest={"edition_id":title,"edition_day":edition_day,"track_title":title,
         "duration_seconds":round(actual,2),"segments":segments,
         "original_audio_authorized":True,"published":False}
    (folder/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
    print("RDI_TOP3_PREPARED="+title)
    print("AUDIO_DURATION_SECONDS="+str(round(actual,2)))
    for x in segments:
        print(f"RANK_{x['rank']}={x['artist']} - {x['title']} / {x['start']}..{x['end']}")
    return manifest

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=pathlib.Path,default=ROOT)
    args=parser.parse_args()
    produce(args.output)
