#!/usr/bin/env python3
"""Cache RO/IT article translations. Fail closed: never invent translations on API errors."""
import datetime as dt
import html
import json
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "news-translations.json"
now = dt.datetime.now(dt.timezone.utc)
cutoff = now - dt.timedelta(hours=48)
existing = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {"items": {}}
translations = existing.get("items", {})
if not isinstance(translations, dict):
    translations = {}
items = {}
for name in ("news.json", "editorial.json"):
    file = ROOT / name
    if not file.exists():
        continue
    for x in json.loads(file.read_text(encoding="utf-8")).get("items", []):
        try:
            date = dt.datetime.fromisoformat(str(x["published"]).replace("Z", "+00:00"))
            if not date.tzinfo or not cutoff <= date.astimezone(dt.timezone.utc) <= now:
                continue
            key = str(x.get("id") or x.get("url") or (str(x.get("title", "")) + "|" + str(x.get("published", ""))))
            items[key] = x
        except (KeyError, ValueError, TypeError):
            pass

def source_lang(x):
    url = str(x.get("url", "")).lower()
    source = str(x.get("source", "")).lower()
    if any(z in url for z in ("ansa.it", "inps.it", "lavoro.gov.it")) or "ansa" in source:
        return "it"
    if any(z in url for z in ("digi24.ro", "mae.ro", "rotalianul.com")) or "digi24" in source:
        return "ro"
    # Unknown-language sources must not be mislabeled or machine-translated without detection.
    return ""

def translate(value, source, target):
    value = str(value).strip()
    if not value:
        return ""
    if source == target:
        return value
    # Public MyMemory service caps requests; keep individual chunks below 450 bytes.
    chunks = []
    current = ""
    for word in value.split():
        if len((current + " " + word).encode("utf-8")) > 400 and current:
            chunks.append(current)
            current = word
        else:
            current = (current + " " + word).strip()
    if current:
        chunks.append(current)
    converted = []
    for part in chunks:
        url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode({"q": part, "langpair": source + "|" + target})
        request = urllib.request.Request(url, headers={"User-Agent": "RDI-News/1.0"})
        with urllib.request.urlopen(request, timeout=12) as response:
            data = json.loads(response.read(200000))
        text = html.unescape(str(data.get("responseData", {}).get("translatedText", ""))).strip()
        if data.get("responseStatus") != 200 or not text or "MYMEMORY WARNING" in text.upper():
            raise ValueError("Translation service unavailable or quota reached")
        converted.append(text)
        time.sleep(0.2)
    return " ".join(converted)

count = 0
for key, x in items.items():
    source = source_lang(x)
    if not source:
        continue
    original = {field: str(x.get(field) or "") for field in ("title", "summary", "body")}
    previous = translations.get(key, {})
    if previous.get("original") == original and previous.get("it") and previous.get("ro"):
        continue
    record = {"original": original, "source": source, source: original.copy()}
    target = "it" if source == "ro" else "ro"
    try:
        record[target] = {field: translate(value, source, target) for field, value in original.items()}
    except Exception as error:
        print("Translation not published for", key[:40], type(error).__name__)
        continue
    translations[key] = record
    count += 1
    if count >= 8:
        break
translations = {key: val for key, val in translations.items() if key in items}
CACHE.write_text(json.dumps({"updated_at": now.isoformat(), "items": translations}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Updated {count} bilingual article translations, retained {len(translations)} cached records.")
