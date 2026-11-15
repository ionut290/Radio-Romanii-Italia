#!/usr/bin/env python3
"""RDI: notizie italiane documentate da feed RSS; nessuna generazione di fatti."""
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

NOW = dt.datetime.now(dt.timezone.utc)
PATH = Path("editorial.json")
archive = json.loads(PATH.read_text(encoding="utf-8"))
items = archive.get("items", [])
if not isinstance(items, list):
    raise SystemExit("editorial.json: items non validi")
queries = [
    ("Diaspora", "romeni in Italia comunità lavoro scuola consolato when:2d"),
    ("Italia", "Italia notizie lavoro economia sanità società when:1d"),
    ("Diaspora", "Romania Italia cittadini romeni pensioni documenti when:3d"),
]
existing_urls = {str(i.get("url", "")).rstrip("/") for i in items}
existing_titles = {re.sub(r"\W+", " ", str(i.get("title", "")).casefold()).strip() for i in items}
new = []
failures = []
for category, query in queries:
    params = urllib.parse.urlencode({"q": query, "hl": "it", "gl": "IT", "ceid": "IT:it"})
    url = "https://news.google.com/rss/search?" + params
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RadioRomaniiItalia/1.0"})
        with urllib.request.urlopen(req, timeout=20) as response:
            root = ET.fromstring(response.read(1500000))
        for entry in root.findall("./channel/item")[:35]:
            title = html.unescape((entry.findtext("title") or "").strip())
            link = (entry.findtext("link") or "").strip()
            source = (entry.findtext("source") or "Google News").strip()
            if not title or not link.startswith("https://"):
                continue
            try:
                date = email.utils.parsedate_to_datetime(entry.findtext("pubDate") or "").astimezone(dt.timezone.utc)
            except (TypeError, ValueError, OverflowError):
                continue
            if not dt.timedelta(0) <= NOW - date <= dt.timedelta(hours=36):
                continue
            title_key = re.sub(r"\W+", " ", title.casefold()).strip()
            if link.rstrip("/") in existing_urls or title_key in existing_titles:
                continue
            raw = entry.findtext("description") or ""
            summary = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())
            if len(summary) < 60:
                continue
            # Feed snippet may include the title. Avoid fake elaboration.
            item = {
                "id": "rdi-it-" + hashlib.sha256(link.encode()).hexdigest()[:20],
                "editorial": True,
                "category": category,
                "title": title[:240],
                "summary": summary[:1200],
                "body": summary[:1200],
                "image": "",
                "published": date.isoformat(),
                "source": source[:150],
                "url": link,
                "byline": "Selezione notizie in italiano · RDI",
                "content_language": "it",
                "source_urls": [link],
                "extended_summary": False,
            }
            new.append(item)
            existing_urls.add(link.rstrip("/"))
            existing_titles.add(title_key)
            if len(new) >= 3:
                break
    except Exception as exc:
        failures.append(f"{category}: {exc}")
    if len(new) >= 3:
        break
if len(failures) == len(queries):
    raise SystemExit("Tutte le fonti RSS indisponibili: " + "; ".join(failures))
if new:
    archive["items"] = new + items
    archive["updated_at"] = dt.datetime.now(ZoneInfo("Europe/Rome")).isoformat()
    PATH.write_text(json.dumps(archive, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"RDI IT: {len(new)} notizie nuove; {len(failures)} fonti non raggiungibili")
