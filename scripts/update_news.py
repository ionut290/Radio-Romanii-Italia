#!/usr/bin/env python3
"""Build a static news feed for the public radio website using Google News RSS."""
import datetime as dt
import email.utils
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

QUERIES = [
    ("România", "România actualitate", "ro", "RO"),
    ("Italia", "Italia ultime notizie", "it", "IT"),
    ("Diaspora", "români Italia comunitate muncă", "ro", "RO"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RadioRomaniiItalia/1.0)"}
items = []
seen = set()
for category, query, lang, country in QUERIES:
    params = urllib.parse.urlencode({"q": query, "hl": f"{lang}-{country}", "gl": country, "ceid": f"{country}:{lang}"})
    url = "https://news.google.com/rss/search?" + params
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=25) as response:
            root = ET.fromstring(response.read(2_000_000))
        for entry in root.findall("./channel/item")[:18]:
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            source = (entry.findtext("source") or "Google News").strip()
            date_text = (entry.findtext("pubDate") or "").strip()
            if not title or not link or not link.startswith("https://"):
                continue
            if link in seen:
                continue
            seen.add(link)
            try:
                published = email.utils.parsedate_to_datetime(date_text).astimezone(dt.timezone.utc).isoformat()
            except (ValueError, TypeError):
                published = ""
            items.append({"category": category, "title": title[:240], "url": link, "source": source[:90], "published": published})
    except Exception as exc:
        print(f"Failed to fetch {category}: {exc}")

items.sort(key=lambda x: x["published"], reverse=True)
output = Path("news.json")
if not items:
    if output.exists():
        print("No new items fetched; keeping previous news.json")
        raise SystemExit(0)
    raise SystemExit("No news fetched and no previous feed exists")
output.write_text(json.dumps({"updated_at": dt.datetime.now(dt.timezone.utc).isoformat(), "items": items[:54]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Saved {len(items[:54])} items")
