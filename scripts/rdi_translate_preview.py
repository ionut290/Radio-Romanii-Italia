#!/usr/bin/env python3
"""RDI: test locale RO->IT, senza pubblicare né modificare file editoriali."""
import datetime as dt
import email.utils
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

ENDPOINT = os.getenv("RDI_TRANSLATE_URL", "http://127.0.0.1:5000/translate")
QUERIES = [
    'români Italia diaspora comunitate when:3d',
    'români Italia consulat muncă when:3d',
]
def translate(text):
    payload = json.dumps({"q": text, "source": "ro", "target": "it", "format": "text"}).encode()
    req = urllib.request.Request(ENDPOINT, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=40) as response:
        value = json.load(response).get("translatedText", "").strip()
    if not value or value == text:
        raise ValueError("Traduzione mancante o uguale all'originale")
    return value

def fetch_titles():
    now = dt.datetime.now(dt.timezone.utc)
    found, seen = [], set()
    for query in QUERIES:
        params = urllib.parse.urlencode({"q": query, "hl": "ro", "gl": "RO", "ceid": "RO:ro"})
        req = urllib.request.Request("https://news.google.com/rss/search?" + params,
                                    headers={"User-Agent": "RDI-Italian-Translator/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=20) as response:
                root = ET.fromstring(response.read(1200000))
        except Exception as exc:
            print(f"Fonte momentaneamente non disponibile: {type(exc).__name__}", file=sys.stderr)
            continue
        for item in root.findall("./channel/item"):
            title = html.unescape((item.findtext("title") or "").strip())
            url = (item.findtext("link") or "").strip()
            if not title or not url.startswith("https://") or url in seen:
                continue
            try:
                date = email.utils.parsedate_to_datetime(item.findtext("pubDate") or "").astimezone(dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
            if not dt.timedelta(0) <= now-date <= dt.timedelta(hours=72):
                continue
            if not re.search(r"român|români|române|romania|diaspora", title, re.I):
                continue
            seen.add(url)
            found.append({"title_ro": title, "source_url": url, "published": date.isoformat()})
            if len(found) == 3:
                return found
    return found

def main():
    health = translate("Comunitatea românească din Italia participă la evenimente culturale.")
    print("TEST TRADUTTORE:", health)
    result = []
    for item in fetch_titles():
        try:
            result.append({**item, "title_it": translate(item["title_ro"]), "status": "bozza_non_pubblicata"})
        except Exception as exc:
            print(f"Traduzione fallita: {type(exc).__name__}", file=sys.stderr)
    os.makedirs("data", exist_ok=True)
    dest = "data/rdi-translation-preview.json"
    with open(dest, "w", encoding="utf-8") as out:
        json.dump({"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                   "published": False, "items": result}, out, ensure_ascii=False, indent=2)
    print(f"BOZZE: {len(result)}; nessuna pubblicazione; file {dest}")
if __name__ == "__main__":
    main()
