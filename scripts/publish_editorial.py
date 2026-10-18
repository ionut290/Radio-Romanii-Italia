#!/usr/bin/env python3
"""Publish two source-grounded original editorial briefs per Italian time slot."""
import datetime as dt
import email.utils
import hashlib
import html
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

now = dt.datetime.now(ZoneInfo("Europe/Rome"))
key = os.getenv("OPENAI_API_KEY")
if not key:
    print("OPENAI_API_KEY missing; skip without publishing")
    raise SystemExit(0)
path = Path("editorial.json")
data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"items": []}
items = data.get("items", [])
slot = now.strftime("%Y-%m-%d-%H-") + f"{now.minute // 10:01d}"
if sum(x.get("slot") == slot for x in items) >= 1:
    print("Slot already published")
    raise SystemExit(0)
feeds = [
    ("Diaspora", "https://rotalianul.com/feed/", "Rotalianul"),
    ("Italia", "https://www.ansa.it/sito/ansait_rss.xml", "ANSA"),
    ("România", "https://www.digi24.ro/rss/Stiri/Digi24/", "Digi24"),
]
candidates = []
for category, url, publisher in feeds:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RadioRomaniiItalia/1.0"})
        with urllib.request.urlopen(req, timeout=20) as res:
            root = ET.fromstring(res.read(1_500_000))
        for e in root.findall("./channel/item")[:25]:
            title = (e.findtext("title") or "").strip()
            link = (e.findtext("link") or "").strip()
            raw = e.findtext("description") or ""
            summary = re.sub(r"\\s+", " ", html.unescape(re.sub(r"<[^>]*>", " ", raw))).strip()
            try:
                pub = email.utils.parsedate_to_datetime(e.findtext("pubDate") or "")
                pub = pub.astimezone(dt.timezone.utc)
            except (ValueError, TypeError):
                continue
            if not title or not link.startswith("https://") or not summary or not (dt.datetime.now(dt.timezone.utc) - pub < dt.timedelta(hours=72)):
                continue
            identity = hashlib.sha256(link.encode()).hexdigest()[:16]
            if any(x.get("source_id") == identity for x in items):
                continue
            candidates.append(dict(category=category, title=title, summary=summary[:700], url=link, source=publisher, source_id=identity, published=pub.isoformat()))
    except Exception as exc:
        print(f"{publisher}: {exc}")
if not candidates:
    print("No eligible sourced news")
    raise SystemExit(0)
# Prioritize the diaspora, then the newest news, and publish at most one per ten-minute run.
candidates.sort(key=lambda x: (x["category"] == "Diaspora", x["published"]), reverse=True)
for candidate in candidates[:8]:
    if sum(x.get("slot") == slot for x in items) >= 1:
        break
    prompt = (
        "Scrie în limba română un articol ORIGINAL pentru diaspora românească din Italia. "
        "Folosește NUMAI informațiile confirmate în titlul și rezumatul RSS de mai jos. "
        "Nu inventa detalii, citate, cifre, date, declarații sau consecințe juridice. "
        "Dacă informațiile sunt insuficiente, răspunde cu {}. "
        "Răspunde EXCLUSIV în JSON cu title, summary, body; body 120-230 de cuvinte "
        "doar dacă sunt susținute de sursă, altfel mai scurt. Nu copia textul original. "
        "Menționează publicația-sursă și invită cititorul să consulte sursa pentru detalii.\n"
        + json.dumps(candidate, ensure_ascii=False)
    )
    payload = json.dumps({"model": os.getenv("EDITORIAL_MODEL", "gpt-4.1-mini"), "input": prompt, "max_output_tokens": 900}).encode()
    req = urllib.request.Request("https://api.openai.com/v1/responses", data=payload,
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=70) as response:
            result = json.load(response)
        answer = "".join(c.get("text", "") for o in result.get("output", []) for c in o.get("content", []) if c.get("type") == "output_text")
        article = json.loads(answer.strip().removeprefix("```json").removesuffix("```").strip())
        if not all(isinstance(article.get(k), str) and article[k].strip() for k in ("title", "summary", "body")):
            continue
        items.append({
            "editorial": True, "slot": slot, "source_id": candidate["source_id"],
            "category": candidate["category"], "title": article["title"][:240],
            "summary": article["summary"][:350], "body": article["body"][:3000],
            "url": candidate["url"], "source": "Radio Românii din Italia · " + candidate["source"],
            "published": now.isoformat(), "image": ""
        })
    except Exception as exc:
        print(f"Generation skipped for {candidate['source']}: {exc}")
# Retain older items in the editorial archive; only the frontend hides after 24h.
if any(x.get("slot") == slot for x in items):
    path.write_text(json.dumps({"updated_at": now.isoformat(), "items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Editorial articles in slot: {sum(x.get('slot') == slot for x in items)}")
