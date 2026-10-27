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
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

OUTPUT = Path("data/geopolitica-news.json")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RadioRomaniiItalia-Geopolitica/1.0; editorial news index)"}
# Each search labels a news topic for browsing; labels do not assert the truth of a headline.
QUERIES = [
    ("diplomatie", "global", "global diplomacy UN peace negotiations summit when:1d", "en", "US"),
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
    ("clima", "global", "climate diplomacy COP climate agreement environment when:1d", "en", "US"),
    ("diplomatie", "americi", "United States Latin America diplomacy summit when:3d", "en", "US"),
    ("diplomatie", "asia", "Asia Pacific China India diplomacy foreign policy when:3d", "en", "US"),
]
MAX_PER_QUERY = 9
MAX_TOTAL = 60
MAX_NEW_BILINGUAL_TITLES = 72  # bounded API requests per hourly run
NOW = dt.datetime.now(dt.timezone.utc)
TODAY_ROME = NOW.astimezone(ZoneInfo('Europe/Rome')).date()
seen_urls = set()
seen_titles = set()
entries = []
failures = []

try:
    old_data = json.loads(OUTPUT.read_text(encoding="utf-8"))
    old_titles = {x["id"]: x for x in old_data.get("items", []) if isinstance(x, dict) and x.get("id")}
except (OSError, ValueError, TypeError):
    old_titles = {}

def translate_google(value, target):
    # The language of an RSS title may differ from the language of the search query.
    query = urllib.parse.urlencode({"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": value})
    request = urllib.request.Request(
        "https://translate.googleapis.com/translate_a/single?" + query,
        headers={"User-Agent": "Mozilla/5.0 (compatible; RDI-WorldDesk/1.1)"}
    )
    with urllib.request.urlopen(request, timeout=9) as response:
        data = json.loads(response.read(300000))
    translated = html.unescape("".join(str(piece[0] or "") for piece in data[0] if piece and piece[0])).strip()
    source_lang = str(data[2] or "").lower() if len(data) > 2 else ""
    if not translated or len(translated) < 5:
        raise ValueError("empty translation")
    if source_lang and source_lang != target and translated.casefold() == value.casefold() and len(value.split()) >= 4:
        raise ValueError("untranslated text")
    return translated[:260]

def strip_source_suffix(title, publisher):
    # Some RSS headlines include the publisher name as a suffix.
    suffix = " - " + publisher
    return title[:-len(suffix)].strip() if publisher and title.endswith(suffix) else title

def add_bilingual_titles(items):
    # Preserve translations when the matching original headline has not changed.
    pending = []
    for item in items:
        previous = old_titles.get(item["id"], {})
        if previous.get("title") == item["title"] and previous.get("title_ro") and previous.get("title_it"):
            item["title_ro"] = previous["title_ro"]
            item["title_it"] = previous["title_it"]
            item["translation_status"] = previous.get("translation_status", "machine_translation")
        else:
            pending.append(item)
    # Spread translations across every topic rather than only the first feed.
    by_topic = {}
    for item in pending:
        by_topic.setdefault(item["category"], []).append(item)
    prioritized = []
    topics = list(by_topic)
    while any(by_topic.values()):
        for topic in topics:
            if by_topic[topic]:
                prioritized.append(by_topic[topic].pop(0))
    completed = 0
    consecutive_failures = 0
    for item in prioritized:
        if completed >= MAX_NEW_BILINGUAL_TITLES or consecutive_failures >= 5:
            break
        try:
            original = item["title"]
            ro = translate_google(original, "ro")
            it = translate_google(original, "it")
            item["title_ro"] = ro
            item["title_it"] = it
            item["translation_status"] = "machine_translation"
            completed += 1
            consecutive_failures = 0
            time.sleep(0.15)
        except Exception as exc:
            consecutive_failures += 1
            print("Titlu nepublicat până la traducere:", item["id"], type(exc).__name__)
    print("Titluri bilingve noi:", completed, "titluri rămase:", len(pending) - completed)


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
        title = strip_source_suffix(title, publisher)
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
        if when > NOW + dt.timedelta(hours=1) or when.astimezone(ZoneInfo('Europe/Rome')).date() != TODAY_ROME:
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
        print("Nessuna notizia pubblicata oggi (ora italiana): il feed del giorno sarà vuoto.")
    entries.sort(key=lambda row: row["published"], reverse=True)
    entries[:] = entries[:MAX_TOTAL]
    add_bilingual_titles(entries)
    output = {
        "schema_version": 2,
        "updated_at": NOW.isoformat().replace("+00:00", "Z"),
        "origin": "Google News RSS / publisher headlines",
        "verification": "external_headlines_not_independently_verified",
        "translation_policy": "Display only records translated into the selected Romanian or Italian language; translations may be automatic.",
        "note_ro": "Flux automat de titluri. Verificați întotdeauna articolul și data la publicația citată.",
        "note_it": "Flusso automatico di titoli. Verificare sempre il pezzo e la data presso la fonte citata.",
        "items": entries,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Salvate {len(output['items'])} titluri, {len(failures)} erori de preluare.")

if __name__ == "__main__":
    main()
