#!/usr/bin/env python3
"""Generate a balanced Romanian/Italian/diaspora news feed for GitHub Pages."""
import datetime as dt
import email.utils
import json
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

DIRECT_FEEDS = [
    ("România", "https://www.digi24.ro/rss/Stiri/Digi24/", "Digi24"),
    ("Italia", "https://www.ansa.it/sito/ansait_rss.xml", "ANSA"),
    ("Diaspora", "https://rotalianul.com/feed/", "Rotalianul"),
]

QUERIES = [
    ("România", "România știri actualitate politică economie sănătate when:2d", "ro", "RO"),
    ("Italia", "Italia notizie cronaca economia lavoro attualità when:2d", "it", "IT"),
    ("Diaspora", "români în Italia diaspora comunitate muncă consulat when:7d", "ro", "RO"),
    ("Știri consulare", "((site:roma.mae.ro OR site:bologna.mae.ro OR site:milano.mae.ro OR site:torino.mae.ro OR site:trieste.mae.ro) consulat România Italia OR site:agerpres.ro/comunicate/ Ambasada României în Italia) when:14d", "ro", "RO"),
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
            if date > now + dt.timedelta(hours=1) or now - date > dt.timedelta(days=14 if category == "Știri consulare" else 7):
                continue
            seen.add(link)
            description = re.sub(r"<[^>]+>", " ", entry.findtext("description") or "")
            description = html.unescape(re.sub(r"\\s+", " ", description)).strip()
            if description.lower().startswith(title.lower()[:35]):
                description = ""
            items.append({
                "category": category, "title": title[:240], "url": link,
                "source": source[:90], "published": date.isoformat(),
                "summary": description[:350], "image": ""
            })
            count += 1
            if count >= LIMIT:
                break
        print(f"{category}: {count} articole")
    except Exception as exc:
        print(f"Nu s-au putut prelua știrile {category}: {exc}")

# Dedicated consular queries: Google News indexes institutional releases inconsistently.
# Keep only official Romanian diplomatic pages or AGERPRES embassy communiques.
CONSULAR_QUERIES = [
    '"Ambasada României în Italia" site:agerpres.ro/comunicate/ when:30d',
    'site:roma.mae.ro "comunicat" when:30d',
    'site:bologna.mae.ro "consulat" when:30d',
    '"Consulatul General al României" Italia site:agerpres.ro/comunicate/ when:30d',
]
for query in CONSULAR_QUERIES:
    params = urllib.parse.urlencode({"q": query, "hl": "ro-RO", "gl": "RO", "ceid": "RO:ro"})
    try:
        request = urllib.request.Request("https://news.google.com/rss/search?" + params, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=25) as response:
            root = ET.fromstring(response.read(2_000_000))
        for entry in root.findall("./channel/item")[:15]:
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            source = (entry.findtext("source") or "").strip()
            try:
                date = email.utils.parsedate_to_datetime(entry.findtext("pubDate") or "").astimezone(dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
            if not title or not link.startswith("https://") or link in seen or date > now + dt.timedelta(hours=1) or now - date > dt.timedelta(days=30):
                continue
            # Google News RSS links point to news.google.com, not to the publisher.
            # Validate the publisher field and title instead of testing the redirect URL.
            publisher = source.casefold()
            headline = title.casefold()
            official = any(host in publisher for host in ("mae.ro", "agerpres"))
            diplomatic = any(word in headline for word in (
                "ambasada româniei", "ambasadei româniei",
                "consulatul româniei", "consulatului româniei",
                "consulatul general", "consulatului general",
                "ambasadorul româniei", "ambasadoarea româniei",
                "gabriela dancău", "servicii consulare", "misiunea diplomatică"
            ))
            if not (official and diplomatic):
                continue
            seen.add(link)
            raw = entry.findtext("description") or ""
            summary = re.sub(r"\\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()
            items.append({"category": "Știri consulare", "title": title[:240], "url": link,
                          "source": source[:90] or "Comunicat oficial", "published": date.isoformat(),
                          "summary": summary[:350], "image": ""})
    except Exception as exc:
        print(f"Sursa consulară indisponibilă ({query}): {exc}")

# Direct publisher feeds may provide genuine summaries and image metadata.
# Only RSS excerpts are displayed; full articles remain at the publisher.
for category, feed_url, publisher in DIRECT_FEEDS:
    try:
        request = urllib.request.Request(feed_url, headers=HEADERS)
        with urllib.request.urlopen(request, timeout=20) as response:
            root = ET.fromstring(response.read(2_000_000))
        fresh = []
        for entry in root.findall("./channel/item")[:25]:
            title = (entry.findtext("title") or "").strip()
            link = (entry.findtext("link") or "").strip()
            if not title or not link.startswith("https://") or link in seen:
                continue
            try:
                published = email.utils.parsedate_to_datetime(entry.findtext("pubDate") or "").astimezone(dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
            if published > now + dt.timedelta(hours=1) or now - published > dt.timedelta(days=7):
                continue
            raw = entry.findtext("description") or ""
            summary = html.unescape(re.sub(r"<[^>]+>", " ", raw))
            summary = re.sub(r"\\s+", " ", summary).strip()[:350]
            image = ""
            for child in entry.iter():
                local = child.tag.split("}")[-1].lower()
                candidate = child.attrib.get("url", "")
                if local in ("thumbnail", "content", "enclosure") and candidate.startswith("https://"):
                    mime = child.attrib.get("type", "")
                    if mime.startswith("image/") or local == "thumbnail" or re.search(r"\\.(jpg|jpeg|png|webp)(\\?|$)", candidate, re.I):
                        image = candidate
                        break
            if not image:
                match = re.search(r'<img[^>]+src=["\\\'](https://[^"\\\']+)', raw, re.I)
                if match:
                    image = html.unescape(match.group(1))
            fresh.append({"category": category, "title": title[:240], "url": link,
                          "source": publisher, "published": published.isoformat(),
                          "summary": summary, "image": image})
            seen.add(link)
        # Prefer the direct publisher's RSS when it is available.
        if fresh:
            items = [item for item in items if item["category"] != category]
            items.extend(fresh[:LIMIT])
        print(f"{publisher}: {len(fresh)} știri RSS")
    except Exception as exc:
        print(f"{publisher} RSS indisponibil: {exc}")

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
