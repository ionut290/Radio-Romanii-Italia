#!/usr/bin/env python3
"""Hourly source-grounded diaspora briefs, without external AI services."""
import datetime as dt
import email.utils
import hashlib
import html
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

NOW = dt.datetime.now(ZoneInfo("Europe/Rome"))
ARCHIVE = Path("editorial.json")
data = json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else {"items": []}
items = data.get("items", [])
if not isinstance(items, list):
    raise SystemExit("Invalid editorial.json: items must be a list")
known_urls = {str(x.get("url", "")).rstrip("/") for x in items}
slot = NOW.strftime("%Y-%m-%d-%H")
feeds = [
    ("Google News · diaspora Italia", "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": "români Italia diaspora when:4d", "hl": "ro", "gl": "RO", "ceid": "RO:ro"}), "Diaspora"),
    ("Google News · români Italia", "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": "\"român\" Italia when:4d", "hl": "ro", "gl": "RO", "ceid": "RO:ro"}), "Diaspora"),
    ("ANSA", "https://www.ansa.it/sito/ansait_rss.xml", "Italia"),
    ("ANSA Ultima Ora", "https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml", "Italia"),
    ("AGERPRES via Google News", "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": "site:agerpres.ro when:4d", "hl": "ro", "gl": "RO", "ceid": "RO:ro"}), "România"),
    ("Guvernul României via Google News", "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": "site:gov.ro when:4d", "hl": "ro", "gl": "RO", "ceid": "RO:ro"}), "România"),
]
keywords = ("român", "romani", "români", "romanca", "româncă", "române", "romania",
            "diaspora", "moldove", "moldova", "cetățean român", "roman")
new_items = []
for publisher, feed, category in feeds:
    try:
        request = urllib.request.Request(feed, headers={"User-Agent": "RadioRomaniiItalia/1.0 (editorial RSS)"})
        with urllib.request.urlopen(request, timeout=25) as response:
            root = ET.fromstring(response.read(2_000_000))
        for entry in root.findall("./channel/item")[:40]:
            title = html.unescape((entry.findtext("title") or "").strip())
            url = (entry.findtext("link") or "").strip()
            description = entry.findtext("description") or ""
            summary = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", description)).split())
            if not title or not url.startswith("https://") or not summary:
                continue
            if url.rstrip("/") in known_urls:
                continue
            try:
                published = email.utils.parsedate_to_datetime(entry.findtext("pubDate") or "").astimezone(dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
            age = dt.datetime.now(dt.timezone.utc) - published
            if not (dt.timedelta(0) <= age <= dt.timedelta(hours=96)):
                continue
            if category == "Diaspora" and not any(k in (title + " " + summary).lower() for k in keywords):
                continue
            image = ""
            # Use only image URLs explicitly supplied by the publisher RSS feed.
            for media in entry.iter():
                local = media.tag.split("}")[-1].lower()
                candidate = media.attrib.get("url", "")
                media_type = media.attrib.get("type", "")
                if local in ("thumbnail", "content", "enclosure") and candidate.startswith("https://"):
                    if local == "thumbnail" or media_type.startswith("image/") or re.search(r"\\.(?:jpe?g|png|webp)(?:[?#]|$)", candidate, re.I):
                        image = candidate
                        break
            if not image:
                image_match = re.search(r'<img[^>]+src=["\\\'](https://[^"\\\']+)["\\\']', description, re.I)
                if image_match:
                    image = html.unescape(image_match.group(1))
            # Only source-grounded short news briefs: no invented facts, quotes or details.
            clean_summary = summary[:380].rsplit(" ", 1)[0].rstrip(" ,;:-") + ("…" if len(summary) > 380 else "")
            if len(clean_summary) < 45:
                continue
            body = (clean_summary + "\n\n" +
                    "Informațiile sunt prezentate pe baza relatării publicate de " + publisher +
                    ". Pentru contextul complet și eventualele actualizări, consultați articolul original.")
            new_items.append({
                "id": "rss-" + hashlib.sha256(url.encode()).hexdigest()[:20],
                "editorial": True,
                "category": category,
                "title": title[:240],
                "image": image,
                "summary": clean_summary,
                "body": body,
                "published": published.isoformat(),
                "source": (entry.findtext("source") or publisher),
                "url": url,
                "byline": "Selecție știri · Radio Românii din Italia",
                "source_id": hashlib.sha256(url.encode()).hexdigest()[:16],
                "slot": slot,
            })
            known_urls.add(url.rstrip("/"))
            if len([x for x in new_items if x["category"] == category]) >= 2:
                break
    except Exception as exc:
        print(f"RSS unavailable ({publisher}): {exc}")
    if len(new_items) >= 9:
        break
if new_items:
    data["items"] = new_items + items
    data["updated_at"] = NOW.isoformat()
    ARCHIVE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"New verified-source RSS briefs: {len(new_items)}; archived articles: {len(items)}")
