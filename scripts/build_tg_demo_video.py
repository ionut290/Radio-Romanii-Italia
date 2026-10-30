#!/usr/bin/env python3
"""Render a local MP4 demonstration of RDI's 18:00 TV news.

Facts come from editorial.json (article rdi-20261030-alina-serban-i-matter-roma).
Exact existing RDI female voice: it-IT-ElsaNeural, via edge-tts.
The relevant Rome Pexels still is documented in data/youtube-landscapes.json,
never misrepresented as photography of the film or the event.
No deployment, AzuraCast changes, YouTube upload or remote publishing.
"""
from __future__ import annotations
import asyncio
import io
import json
import math
from pathlib import Path
import subprocess
import textwrap
import urllib.request
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from mutagen.mp3 import MP3
import imageio_ffmpeg
import edge_tts

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT / "demo-output"
STORY_ID="rdi-20261030-alina-serban-i-matter-roma"
SIZE=(1280,720)
INK=(8,22,43)
WHITE=(246,249,255)
GOLD=(246,203,120)
PAP=(207,223,238)
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SOURCE="Occhio Blu · Cinema Farnese · Turismo Roma · Cineuropa"
# An original Italian paraphrase of the RDI story, not a reenactment.
SCENES=[
    {
        "tag":"RADIO ROMÂNII DIN ITALIA", "headline":"TG RDI\nDELLE 18",
        "body":"Notizie, contesto e approfondimenti",
        "spoken":"Buonasera da Radio Românii din Italia. Questa è una dimostrazione del TG RDI della sera. Una puntata pensata per raccontare i fatti, approfondirli e spiegarne il significato per la comunità. Le notizie si chiudono alle sedici e l'edizione è prevista per le diciotto.",
        "kind":"opener"
    },
    {
        "tag":"ITALIA E DIASPORA · IL FATTO", "headline":"Il cinema romeno\narriva a Roma",
        "body":"«I Matter» in programma al festival Euro Balkan",
        "spoken":"Cominciamo da Roma. Il film I Matter, della regista romena Alina Șerban, è in programma all'Euro Balkan Film Festival. La proiezione è annunciata per il cinque novembre duemilaventisei, alle sedici e trenta, al Cinema Farnese. Il lungometraggio è una coproduzione tra Romania, Germania e Belgio.",
        "kind":"fact"
    },
    {
        "tag":"APPROFONDIMENTO · IL CONTESTO", "headline":"Una storia di identità\ne pregiudizi",
        "body":"Il racconto di un'adolescente in cerca del proprio futuro",
        "spoken":"Il film racconta la storia di Rebeca, un'adolescente che deve prendere decisioni importanti sul suo futuro, mentre affronta difficoltà familiari e pregiudizi. Il festival romano, dedicato al cinema dell'Europa sudorientale, si svolge dal trentuno ottobre al sette novembre. Secondo gli organizzatori, I Matter ha già ottenuto il premio del pubblico nella sezione Spotlight a Venezia. Questo riconoscimento non va confuso con un premio del festival di Roma.",
        "kind":"context"
    },
    {
        "tag":"APPROFONDIMENTO · LE INFORMAZIONI UTILI", "headline":"Un'occasione per\nla comunità",
        "body":"5 novembre · Cinema Farnese · Roma",
        "spoken":"Per i romeni che vivono in Italia, l'appuntamento offre l'occasione di conoscere una produzione contemporanea del proprio paese, in un contesto europeo. Il programma ufficiale indica sottotitoli in italiano e un biglietto di tre euro. Non risulta confermata, invece, la presenza della regista alla proiezione. Prima di partecipare è consigliabile verificare gli aggiornamenti degli organizzatori.",
        "kind":"impact"
    },
    {
        "tag":"RDI · PROVA TECNICA", "headline":"L'informazione\ncon più contesto",
        "body":"Fatti verificati · Fonti indicate · Voce femminile",
        "spoken":"Questo era un esempio del nostro nuovo TG, con voce femminile, immagini pertinenti, fatti e approfondimenti. Ricordiamo che questo filmato è soltanto una prova tecnica e non un'edizione in onda. Grazie per l'ascolto da Radio Românii din Italia.",
        "kind":"closing"
    }
]

def font(size,bold=False):
    return ImageFont.truetype(BOLD if bold else FONT,size)

def ellipse_bg(img,seed):
    d=ImageDraw.Draw(img)
    for i in range(45):
        x=550+int(190*math.sin(seed+i*.3)); y=120+int(190*math.cos(seed+i*.19))
        r=5+i*5
        d.ellipse((x-r,y-r,x+r,y+r),outline=(24,48,76),width=2)
    for i in range(0,720,36):
        d.line((0,i,1280,i),fill=(10,26,49),width=1)

def get_rome():
    cfg=json.loads((ROOT/"data/youtube-landscapes.json").read_text(encoding="utf-8"))
    row=next(x for x in cfg["items"] if x["id"]=="it-roma-pexels")
    if not (row.get("rights_reviewed") and row.get("source_url") and "pexels.com" in row["poster"]):
        raise ValueError("Rome still lacks RDI's source/rights metadata")
    try:
        req=urllib.request.Request(row["poster"],headers={"User-Agent":"Mozilla/5.0 RDI-Demo/1.0"})
        with urllib.request.urlopen(req,timeout=24) as resp:
            data=resp.read(8_000_000)
        im=Image.open(io.BytesIO(data)).convert("RGB")
        print("Rome contextual still loaded from RDI-approved Pexels record")
        return im
    except Exception as ex:
        print("Rome poster temporarily unavailable; using contextual graphic",type(ex).__name__)
        return None

def fill_crop(photo,size,seed):
    w,h=size
    scale=max(w/photo.width,h/photo.height)
    p=photo.resize((math.ceil(photo.width*scale),math.ceil(photo.height*scale)),Image.Resampling.LANCZOS)
    shift=seed*27
    left=max(0,min(p.width-w,(p.width-w)//2+shift))
    top=max(0,(p.height-h)//2)
    return p.crop((left,top,left+w,top+h))

def multiline(draw,xy,lines,f,fill,spacing=13):
    y=xy[1]
    for s in lines:
        draw.text((xy[0],y),s,font=f,fill=fill,stroke_width=0)
        y+=f.size+spacing
    return y

def generate_slide(scene,index,photo,seconds):
    w,h=SIZE
    im=Image.new("RGB",SIZE,INK)
    ellipse_bg(im,index+1)
    d=ImageDraw.Draw(im)
    d.rectangle((0,0,14,h),fill=(196,38,49))
    if photo is not None and scene["kind"] in ("fact","context","impact"):
        side=fill_crop(photo,(740,h),index-2)
        im.paste(side,(w-740,0))
        # Exact photos are geographic background only, not purported event stills.
        shade=Image.new("RGBA",SIZE,(0,0,0,0))
        sd=ImageDraw.Draw(shade)
        for x in range(w):
            t=max(0,min(1,(x-415)/820))
            alpha=round(255*(.99-.52*t))
            sd.line((x,0,x,h),fill=(7,20,40,alpha),width=1)
        im=Image.alpha_composite(im.convert("RGBA"),shade).convert("RGB")
    d=ImageDraw.Draw(im)
    d.rectangle((35,30,730,88),fill=(9,29,55))
    d.text((56,47),"RDI",font=font(30,True),fill=GOLD)
    d.text((145,55),"RADIO ROMÂNII DIN ITALIA",font=font(20,True),fill=WHITE)
    d.rounded_rectangle((1000,35,1244,76),radius=18,fill=(174,37,49))
    d.text((1026,44),"PROVA • NON IN ONDA",font=font(15,True),fill=WHITE)
    d.text((66,180),scene["tag"],font=font(21,True),fill=GOLD)
    headlines=scene["headline"].split("\n")
    multiline(d,(64,236),headlines,font(58 if scene["kind"]!="opener" else 78,True),WHITE,17)
    base=244+len(headlines)*(58+17)+36 if scene["kind"]!="opener" else 244+len(headlines)*95+26
    text=scene["body"]
    # wrap to fit visually and prevent clipping in televised safe areas
    wrapped=textwrap.wrap(text,width=43 if scene["kind"]!="opener" else 39)
    multiline(d,(67,base),wrapped,font(24),PAP,8)
    d.line((67,622,1218,622),fill=(166,188,205),width=2)
    d.text((67,643),"TG DELLE 18  ·  CHIUSURA NOTIZIE ORE 16:00",font=font(17,True),fill=GOLD)
    d.text((67,676),"RDI · EDIZIONE DIMOSTRATIVA · 30 OTTOBRE 2026",font=font(14),fill=PAP)
    d.text((1243,663),f"{index+1:02d}/{len(SCENES):02d}",anchor="ra",font=font(21,True),fill=WHITE)
    if photo is not None and scene["kind"] in ("fact","context","impact"):
        d.text((1243,588),"ROMA · REPERTORIO PEXELS · NON IL FILM",anchor="ra",font=font(13,True),fill=WHITE,stroke_fill=INK,stroke_width=2)
    elif scene["kind"] in ("fact","context","impact"):
        d.text((1243,588),"GRAFICA ILLUSTRATIVA · NON IL FILM",anchor="ra",font=font(13,True),fill=WHITE)
    return im

async def write_voice(text,path):
    for retry in range(3):
        try:
            await edge_tts.Communicate(text,"it-IT-ElsaNeural",rate="-5%").save(str(path))
            if path.stat().st_size>3000: return
        except Exception as ex:
            print("Voice generation retry",retry+1,type(ex).__name__)
            await asyncio.sleep(1+retry)
    raise RuntimeError("Female voice it-IT-ElsaNeural unavailable; cannot issue silent demo")

def ffmpeg(*args):
    cmd=[imageio_ffmpeg.get_ffmpeg_exe(),"-hide_banner","-loglevel","error","-y",*map(str,args)]
    subprocess.run(cmd,check=True)

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    article=next((item for item in json.loads((ROOT/"editorial.json").read_text(encoding="utf-8"))["items"] if item.get("id")==STORY_ID),None)
    if not article or len(article.get("body",""))<1500 or len(article.get("source_urls",[]))<3:
        raise RuntimeError("The editorially documented Rome article is not present; stop demo")
    photo=get_rome()
    parts=[]
    timing=[]
    elapsed=0.0
    for i,scene in enumerate(SCENES):
        base=OUT/f"scene-{i:02d}"
        voice=base.with_suffix(".mp3")
        asyncio.run(write_voice(scene["spoken"],voice))
        sec=MP3(str(voice)).info.length
        if not 5<sec<95: raise ValueError("Unexpected narration duration")
        still=base.with_suffix(".jpg")
        generate_slide(scene,i,photo,sec).save(still,quality=94,subsampling=0)
        video=base.with_suffix(".mp4")
        ffmpeg("-loop","1","-framerate","15","-i",still,"-i",voice,
               "-t",f"{sec:.3f}","-vf","scale=1280:720:flags=lanczos,format=yuv420p",
               "-c:v","libx264","-preset","veryfast","-b:v","1250k",
               "-c:a","aac","-b:a","128k","-ar","44100","-ac","2",
               "-r","15","-movflags","+faststart","-shortest",video)
        parts.append(video)
        timing.append({"part":scene["kind"],"start_seconds":round(elapsed,2),"end_seconds":round(elapsed+sec,2)})
        elapsed+=sec
        print("Rendered",scene["kind"],f"{sec:.1f}s")
    concat=OUT/"concat.txt"
    concat.write_text("".join("file '"+p.name+"'\n" for p in parts),encoding="utf-8")
    target=OUT/"RDI-TG-18-VIDEO-PROVA.mp4"
    ffmpeg("-f","concat","-safe","0","-i",concat,"-c","copy","-movflags","+faststart",target)
    if not target.exists() or target.stat().st_size<200_000:
        raise RuntimeError("Preview video invalid")
    manifest={
        "title":"TG RDI delle 18 · VIDEO DI PROVA",
        "type":"demo_not_for_broadcast","voice":"it-IT-ElsaNeural",
        "source_article":article["url"] if "url" in article else article["id"],
        "editorial_sources":article["source_urls"],
        "visual_source":"Florian Delée / Pexels via data/youtube-landscapes.json",
        "visual_notice":"Roma, immagini di repertorio; non fotogrammi del film",
        "duration_seconds":round(elapsed,1),"scenes":timing,"video":target.name
    }
    (OUT/"metadata.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("DEMO VIDEO READY",target,round(target.stat().st_size/1_000_000,2),"MB",round(elapsed),"sec")

if __name__=="__main__":
    main()
