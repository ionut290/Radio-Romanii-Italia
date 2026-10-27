#!/usr/bin/env python3
"""RDI Geopolitică: index of source-attributed RSS headlines, not independently verified reports.
No event coordinates, casualty counts, invented summaries or publisher photographs.
"""
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

OUTPUT = Path("data/geopolitica-news.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RadioRomaniiItalia-Geopolitica/1.0; editorial news index)"}
# Each search labels a news topic for browsing; labels do not assert the truth of a headline.
QUERIES = [
    ("diplomatie", "global", "global diplomacy UN peace negotiations summit when:3d", "en", "US"),
    ("diplomatie", "europa", "UE diplomație relații internaționale negocieri when:3d", "ro", "RO"),
    ("conflicte", "europa", "Ukraine Russia war peace negotiations civilians when:3d", "en", "US"),
    ("conflicte", "orient", "Gaza Israel Middle East humanitarian ceasefire when:3d", "en", "US"),
    ("conflicte", "africa", "Sudan Congo Sahel conflict humanitarian crisis when:3d", "en", "US"),
    ("europa", "europa", "Uniunea Europeană Bruxelles politica externă Comisia Europeană when:3d", "ro", "RO"),
    ("europa", "europa", "Unione Europea politica estera Consiglio europeo when:3d", "it", "IT"),
    ("economie", "global", "world economy IMF trade tariffs central banks when:3d", "en", "US"),
    ("energie", "global", "oil gas OPEC energy security IEA when:3d", "en", "US"),
    ("securitate", "europa", "NATO defense alliance European security when:3d", "en", "US"),
    ("securitate", "asia", "China Taiwan Japan Indo Pacific security when:3d", "en", "US"),
    ("tehnologie", "global", "AI semiconductor chip export controls space race when:3d", "en", "US"),
    ("clima", "global", "climate diplomacy COP climate agreement environment when:4d", "en", "US"),
    ("diplomatie", "americi", "United States Latin America diplomacy summit when:3d", "en", "US"),
    ("diplomatie", "asia", "Asia Pacific China India diplomacy foreign policy when:3d", "en", "US"),
]
MAX_PER_QUERY = 9
MAX_TOTAL = 100
NOW = dt.datetime.now(dt.timezone.utc)
seen_urls = set()
seen_titles = set()
entries = []
failures = []

def normalized_title(value):
    value = html.unescape(value)
    value = re.sub(r"\s+[-–—]\s+[^-–—]{2,60}$", "", value)
    return re.sub(r"\s+", " ", value).strip().casefold()

def fetch_query(topic, region, query, lang, country):
    params = urllib.parse.urlencode({"q": query, "hl": f"{lang}-{country}", "gl": country, "ceid": f"{country}:{lang}"})
    request = urllib.request.Request("https://news.google.com/rss/search?" + params, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=10) as response:
        content = response.read(1800000)
    feed = ET.fromstring(content)
    count = 0
    for item in feed.findall("./channel/item"):
        title = html.unescape((item.findtext("title") or "").strip())
        link = html.unescape((item.findtext("link") or "").strip())
        publisher = html.unescape((item.findtext("source") or "Google News").strip())
        date_string = (item.findtext("pubDate") or "").strip()
        if not title or len(title) < 12 or not link.startswith("https://") or len(link) > 3000:
            continue
        try:
            when = email.utils.parsedate_to_datetime(date_string)
            if when.tzinfo is None:
                when = when.replace(tzinfo=dt.timezone.utc)
            when = when.astimezone(dt.timezone.utc)
        except (TypeError, ValueError, OverflowError):
            continue
        if when > NOW + dt.timedelta(hours=1) or NOW - when > dt.timedelta(days=5):
            continue
        # Google News RSS descriptions contain related-article HTML rather than reliable summaries.
        # We intentionally do not turn that HTML into an editorial summary.
        identity = normalized_title(title)
        if identity in seen_titles or link in seen_urls:
            continue
        seen_titles.add(identity)
        seen_urls.add(link)
        entries.append({
            "id": "geo-" + hashlib.sha256((link + title).encode("utf-8")).hexdigest()[:16],
            "category": topic,
            "region": region,
            "title": title[:240],
            "summary": "",
            "source": publisher[:90],
            "published": when.isoformat().replace("+00:00", "Z"),
            "url": link,
            "review_status": "external_headline_unverified"
        })
        count += 1
        if count >= MAX_PER_QUERY:
            break
    return count

def main():
    for topic, region, query, lang, country in QUERIES:
        try:
            count = fetch_query(topic, region, query, lang, country)
            print(f"{topic} / {region}: {count} știri")
        except Exception as exc:
            failures.append(f"{topic}/{region}: {type(exc).__name__}: {exc}")
            print("Sursa RSS indisponibilă:", failures[-1])
    if not entries:
        if OUTPUT.exists():
            print("Nu s-au obținut rezultate; versiunea anterioară este păstrată nemodificată.")
            return
        raise SystemExit("Nicio sursă disponibilă; nu publicăm date fictive.")
    entries.sort(key=lambda row: row["published"], reverse=True)
    output = {
        "schema_version": 1,
        "updated_at": NOW.isoformat().replace("+00:00", "Z"),
        "origin": "Google News RSS / publisher headlines",
        "verification": "external_headlines_not_independently_verified",
        "note_ro": "Flux automat de titluri. Verificați întotdeauna articolul și data la publicația citată.",
        "note_it": "Flusso automatico di titoli. Verificare sempre il pezzo e la data presso la fonte citata.",
        "items": entries[:MAX_TOTAL],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Salvate {len(output['items'])} titluri, {len(failures)} erori de preluare.")

if __name__ == "__main__":
    main()
