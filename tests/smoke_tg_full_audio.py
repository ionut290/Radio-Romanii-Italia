#!/usr/bin/env python3
"""Private, non-broadcasting end-to-end smoke of RDI TG audio + TV timing.

Artificial technical phrases; NO newspaper stories or station credentials.
"""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from render_daily_tg_audio import produce

OUT=Path("/tmp/rdi-tg-technical-audio-smoke")
OUT.mkdir(parents=True,exist_ok=True)
now=dt.datetime.now(dt.timezone.utc)
edition=now.strftime("%Y%m%d")
tracks=[]
articles=[]
for n in range(1,5):
    title=f"Verifica tecnica numero {n} delle notizie serali"
    stem=("Questa è una simulazione tecnica dei collegamenti tra audio e grafica del notiziario "
          "Radio Românii din Italia. Non viene descritta una notizia realmente accaduta, "
          "né viene riportata una dichiarazione attribuita a una persona. "
          "Il parlato permette di verificare la durata effettiva della voce femminile, "
          "il corretto passaggio alle quattro sezioni del servizio giornalistico, "
          "la qualità del montaggio e la precisione del cambio di immagine. ")
    paragraphs=[
        stem+" Si sta verificando la sezione del fatto. "+stem,
        stem+" Si sta verificando la sezione del contesto. "+stem,
        stem+" Si sta verificando la sezione delle conseguenze. "+stem,
        stem+" Si sta verificando la sezione degli sviluppi. "+stem,
    ]
    articles.append({"id":f"test-n{n}","title":title,"kicker":"Solo test", "category":"Test",
       "paragraphs":paragraphs,"image":"", "image_notice":"Prova tecnica senza notizie reali",
       "video":None,"source_name":"Prova interna","source_url":"https://example.org/test",
       "sources":["https://example.org/test","https://example.net/test"]})
    tracks.append({"kind":"story","id":f"test-n{n}","text":title+". "+" ".join(paragraphs)})
data={
 "schema_version":1,"language":"it","edition_id":edition,
 "track_title":f"RDI-TG-SERA-IT-{edition}","synthetic_voice":"it-IT-ElsaNeural",
 "story_count":len(articles),"articles":articles,
 "editorial_notice":"Simulazione tecnica non per la messa in onda",
 "cutoff_at":now.isoformat(),"generated_at":now.isoformat(),
 "segments":[{"kind":"intro","text":"Questa è una prova tecnica dei tempi del TG RDI della sera. Nessuna notizia viene trasmessa in diretta e la radio resta invariata."}]+tracks+[
 {"kind":"outro","text":"La prova tecnica è terminata. L'audio e le informazioni sulle scene rimangono soltanto nel controllo interno e non verranno pubblicati."}]}
(OUT/"manifest.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
res=produce(OUT)
tv=json.loads((OUT/"tv-timing.json").read_text())
assert len(tv["timeline"])==len(articles)+4
assert tv["audio_duration_seconds"]>=240
assert tv["timeline"]==res["timeline"]
assert all(x.get("video") is None for x in tv["timeline"] if x["kind"]=="story")
print("TECHNICAL_SMOKE=PASSED duration",res["audio_duration_seconds"],"scenes",len(tv["timeline"]))
