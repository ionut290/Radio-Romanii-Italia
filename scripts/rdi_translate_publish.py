#!/usr/bin/env python3
"""RDI: brevi notizie RO->IT con fonte; pubblica soltanto riassunti RSS sufficienti."""
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

ENDPOINT = os.getenv("RDI_TRANSLATE_URL", "http://127.0.0.1:15000/translate")
OUTPUT = Path("editorial.json")
NOW = dt.datetime.now(dt.timezone.utc)
SEARCHES = [
    "români Italia diaspora comunitate when:2d",
    "români Italia muncă consulat when:2d",
]
def normalize(s):
    return re.sub(r"\W+", " ", s.casefold()).strip()
def translate(text):
    req = urllib.request.Request(ENDPOINT, data=json.dumps({
        "q": text, "source": "ro", "target": "it", "format": "text"
    }).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as response:
        result = json.load(response).get("translatedText", "").strip()
    if not result or result == text or len(result) < 25:
        raise ValueError("Traduzione insufficiente")
    return result
def main():
    data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    old = data.get("items")
    if not isinstance(old, list):
        raise ValueError("Archivio editoriale non valido")
    known_urls = {str(x.get("url", "")).rstrip("/") for x in old if isinstance(x, dict)}
    known_titles = {normalize(str(x.get("title", ""))) for x in old if isinstance(x, dict)}
    new = []
    healthy = 0
    for query in SEARCHES:
        params = urllib.parse.urlencode({"q":query,"hl":"ro","gl":"RO","ceid":"RO:ro"})
        req = urllib.request.Request("https://news.google.com/rss/search?"+params,
                                     headers={"User-Agent":"RDI-IT-Publisher/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=22) as res:
                root = ET.fromstring(res.read(1200000))
            healthy += 1
        except Exception as exc:
            print("Fonte non disponibile:",type(exc).__name__)
            continue
        for entry in root.findall("./channel/item")[:35]:
            title = html.unescape((entry.findtext("title") or "").strip())
            link = (entry.findtext("link") or "").strip()
            raw = entry.findtext("description") or ""
            summary = " ".join(html.unescape(re.sub(r"<[^>]*>", " ", raw)).split())
            if not title or not link.startswith("https://") or link.rstrip("/") in known_urls:
                continue
            if normalize(title) in known_titles:
                continue
            try:
                published = email.utils.parsedate_to_datetime(entry.findtext("pubDate") or "").astimezone(dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
            if not dt.timedelta(0) <= NOW-published <= dt.timedelta(hours=48):
                continue
            if not re.search(r"român|români|române|romania|diaspora", title, re.I):
                continue
            # News RSS descriptions often repeat the title verbatim: these are NOT articles.
            if len(summary) < 120 or normalize(summary) == normalize(title) or normalize(summary).startswith(normalize(title)) and len(summary) < len(title)+90:
                continue
            try:
                title_it = translate(title)
                summary_it = translate(summary)
            except Exception as exc:
                print("Traduzione scartata:",type(exc).__name__)
                continue
            if len(summary_it) < 90 or normalize(summary_it) == normalize(title_it):
                continue
            source = (entry.findtext("source") or "Google News").strip()
            new.append({
                "id":"rdi-translated-"+hashlib.sha256(link.encode()).hexdigest()[:20],
                "editorial":True,
                "category":"Diaspora",
                "title":title_it[:240],
                "summary":summary_it[:1200],
                "body":summary_it[:1200],
                "published":published.isoformat(),
                "source":source,
                "source_urls":[link],
                "url":link,
                "image":"",
                "byline":"RDI · Traduzione automatica da fonte citata",
                "content_language":"it",
                "translation_disclaimer":"Traduzione automatica di un breve estratto RSS; per dettagli consultare la fonte originale.",
                "extended_summary":False,
            })
            known_urls.add(link.rstrip("/"))
            known_titles.add(normalize(title))
            known_titles.add(normalize(title_it))
            if len(new)>=2:
                break
        if len(new)>=2:
            break
    if not healthy:
        raise SystemExit("Fonti RSS indisponibili: nessuna pubblicazione")
    if new:
        data["items"] = new + old
        data["updated_at"] = dt.datetime.now(ZoneInfo("Europe/Rome")).isoformat()
        OUTPUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Traduzioni pubblicabili: {len(new)}; nessuna notizia incompleta pubblicata")
if __name__=="__main__":
    main()
