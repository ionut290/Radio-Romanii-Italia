#!/usr/bin/env python3
"""Generate a balanced Romanian/Italian/diaspora news feed for GitHub Pages."""
import datetime as dt
import email.utils
import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

QUERIES = [
    ("România", "România știri actualitate politică economie sănătate when:2d", "ro", "RO"),
    ("Italia", "Italia notizie cronaca economia lavoro attualità when:2d", "it", "IT"),
    ("Diaspora", "români în Italia diaspora comunitate muncă consulat when:7d", "ro", "RO"),
]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RadioRomaniiItalia/1.1)"}
LIMIT = 18
items = []
seen = set()
now = dt.datetime.now(dt.timezone.utc)

for category, query, lang, country in QUERIES:
    params = urllib.parse.urlencode({
        "q": query, "hl": f"{lang}-{country}", "gl": country, "ceid": f"{country}:{lang}"
    })
    try:
        request = urllib.request.Request("https://news.google.com/rss/search?" + params, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=25) as response:
            root = ET.fromstring(response.read(2_000_000))
        count = 0
        for entry in root.findall("./channel/item"):
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            source = (entry.findtext("source") or "Google News").strip()
            raw_date = (entry.findtext("pubDate") or "").strip()
            if not title or not link.startswith("https://") or link in seen:
                continue
            try:
                date = email.utils.parsedate_to_datetime(raw_date).astimezone(dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
            if date > now + dt.timedelta(hours=1) or now - date > dt.timedelta(days=7):
                continue
            seen.add(link)
            items.append({
                "category": category, "title": title[:240], "url": link,
                "source": source[:90], "published": date.isoformat()
            })
            count += 1
            if count >= LIMIT:
                break
        print(f"{category}: {count} articole")
    except Exception as exc:
        print(f"Nu s-au putut prelua știrile {category}: {exc}")

output = Path("news.json")
if not items:
    if output.exists():
        print("Sursele indisponibile; păstrez ultima versiune.")
        raise SystemExit(0)
    raise SystemExit("Nu există știri și nici versiune anterioară.")
items.sort(key=lambda x: x["published"], reverse=True)
output.write_text(json.dumps({
    "updated_at": now.isoformat(), "items": items
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Publicate {len(items)} știri.")
