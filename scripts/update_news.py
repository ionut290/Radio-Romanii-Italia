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
from zoneinfo import ZoneInfo

DIRECT_FEEDS = [
    ("România", "https://www.digi24.ro/rss/Stiri/Digi24/", "Digi24"),
    ("Italia", "https://www.ansa.it/sito/ansait_rss.xml", "ANSA"),
]

QUERIES = [
    ("România", "România știri actualitate politică economie sănătate when:2d", "ro", "RO"),
    ("Italia", "Italia notizie cronaca economia lavoro attualità when:2d", "it", "IT"),
    ("Diaspora", "români în Italia diaspora comunitate muncă consulat when:7d", "ro", "RO"),
    ("Drepturile muncitorilor", "\"romeni in Italia\" drepturi munca pensii patronato sindicat when:7d", "ro", "RO"),
    ("Știri consulare", '"Ambasada României" Italia consulat when:3d', "ro", "RO"),
    ("Știri consulare", '"Consulatul General al României" Italia when:3d', "ro", "RO"),
    ("Drepturile muncitorilor", "site:inps.it lavoratori stranieri pensione assegno unico NASpI when:7d", "it", "IT"),
    ("Drepturile muncitorilor", "site:lavoro.gov.it OR site:ispettorato.gov.it diritti lavoratori stranieri when:7d", "it", "IT"),
    ("Drepturile muncitorilor", "site:inail.it sicurezza lavoro stranieri infortuni when:7d", "it", "IT"),
    ("Diaspora", "site:agenziaentrate.gov.it cittadini UE residenza fiscale tasse when:7d", "it", "IT"),
    ("Diaspora", "romeni Italia scuola figli sanità pensioni cittadinanza when:5d", "it", "IT"),
    ("Diaspora", "comunitatea românească Italia asociație festival eveniment when:5d", "ro", "RO"),
    ("Diaspora", "romeni Bologna Milano Torino Roma Napoli Firenze Padova Verona evenimente when:5d", "ro", "RO"),
    ("Știri consulare", "site:mae.ro Italia consulat români documente programări when:7d", "ro", "RO"),
    ("Știri consulare", "site:econsulat.ro servicii consulare Italia when:14d", "ro", "RO"),
    ("Diaspora", "site:rotalianul.com români Italia when:3d", "ro", "RO"),
    ("Diaspora", "site:gazetaromaneasca.com români Italia when:3d", "ro", "RO"),
]
WORKER_TERMS = ("român", "români", "românilor", "romania", "romania", "romeno", "romeni", "rumeno", "rumeni", "rumeni", "române", "romane", "moldoven", "diaspora")
WORKER_ITALY_TERMS = ("italia", "italy", "italian", "italien", "inps", "patronato", "cgil", "naspi", "permesso di soggiorno", "contract de muncă", "contracte de muncă", "lavoro")
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RadioRomaniiItalia/1.1)"}
LIMIT = 18
MAX_PER_CATEGORY = 35
MAX_TOTAL = 120
ITALY_CONTEXT = ("italia", "italy", "italian", "romeni", "români", "diaspora", "roma", "milano", "torino", "bologna", "napoli", "sicilia", "trentino", "veneto", "inps", "consulat", "ambasada", "patronato", "permesso", "lavoro")
CONSULAR_CONTEXT = ("românia", "româniei", "român", "romeni", "romeno", "rumeno", "ambasada", "consulat", "econsulat")
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
            if category in ("Diaspora", "Știri consulare"):
                context = html.unescape(title + " " + (entry.findtext("description") or "")).casefold()
                terms = CONSULAR_CONTEXT if category == "Știri consulare" else ITALY_CONTEXT
                if not any(term in context for term in terms):
                    continue
            if category == "Drepturile muncitorilor":
                context = (title + " " + (entry.findtext("description") or "")).casefold()
                if "site:" not in query and (not any(term in context for term in WORKER_TERMS) or not any(term in context for term in WORKER_ITALY_TERMS)):
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
    '"Ambasada României în Italia" site:agerpres.ro/comunicate/ when:3d',
    'site:roma.mae.ro "comunicat" when:3d',
    'site:bologna.mae.ro "consulat" when:3d',
    '"Consulatul General al României" Italia site:agerpres.ro/comunicate/ when:3d',
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
        # Add direct RSS without removing other publishers in the category.
        if fresh:
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
# Preserve verified, editorially written consular stories across automatic refreshes.
# Keep source URLs as stable IDs and retain only the last 45 days.
if output.exists():
    try:
        previous = json.loads(output.read_text(encoding="utf-8")).get("items", [])
        current_urls = {item["url"] for item in items}
        for item in previous:
            if item.get("category") != "Știri consulare" or not item.get("editorial_verified"):
                continue
            try:
                published = dt.datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError):
                continue
            if item.get("url") not in current_urls and now - published <= dt.timedelta(days=45):
                items.append(item)
                current_urls.add(item["url"])
    except (OSError, ValueError, TypeError) as exc:
        print(f"Arhiva consulară nu poate fi citită: {exc}")
# Keep the public feed strictly limited to the last 72 hours, including
# previously verified consular stories. Invalid timestamps are discarded.
cutoff = now - dt.timedelta(days=3)
today_italy = now.astimezone(ZoneInfo("Europe/Rome")).date()
def is_recent(item):
    try:
        date = dt.datetime.fromisoformat(item["published"].replace("Z", "+00:00"))
        return cutoff <= date.astimezone(dt.timezone.utc) <= now + dt.timedelta(hours=1)
    except (KeyError, TypeError, ValueError, AttributeError):
        return False

items = [item for item in items if is_recent(item)]
# Păstrăm toate știrile din ultimele 72 de ore, fără eliminare pe baza zilei calendaristice.
items.sort(key=lambda x: x["published"], reverse=True)
# Consular stories must concern Romania's missions or travel guidance for Italy.
# Also avoid repeated reports of the same Italy transport protests under different headlines.
filtered = []
seen_consular_events = set()
for item in items:
    if item.get("category") == "Știri consulare" and not item.get("editorial_verified"):
        headline = item.get("title", "").casefold()
        italian_relevance = any(term in headline for term in ("italia", "italiei", "italy", "italiano", "roma", "milano", "torino", "bologna", "napoli", "sicilia", "consulatul româniei", "consulatul general al româniei", "ambasada româniei în italia"))
        consular_relevance = any(term in headline for term in ("mae", "consulat", "ambasad", "atenționare de călătorie", "avertisment pentru români", "servicii consulare"))
        if not italian_relevance or not consular_relevance:
            continue
        event_key = None
        if any(term in headline for term in ("transportator", "camion", "tir-uri")) and any(term in headline for term in ("protest", "blocaj", "blocat", "trafic")):
            event_key = "italia-proteste-transportatori"
        if event_key and event_key in seen_consular_events:
            continue
        if event_key:
            seen_consular_events.add(event_key)
    filtered.append(item)
items = filtered

# Remove repeat headlines carried by different syndication links.
deduped = []
seen_titles = set()
for item in items:
    title_key = re.sub(r"[^\\w]+", " ", item.get("title", "").rsplit(" - ", 1)[0].casefold()).strip()
    if title_key and title_key in seen_titles:
        continue
    if title_key:
        seen_titles.add(title_key)
    deduped.append(item)
items = deduped
per_category = {}
balanced = []
for item in items:
    category = item["category"]
    if per_category.get(category, 0) >= MAX_PER_CATEGORY:
        continue
    balanced.append(item)
    per_category[category] = per_category.get(category, 0) + 1
    if len(balanced) >= MAX_TOTAL:
        break
items = balanced
output.write_text(json.dumps({
    "updated_at": now.isoformat(), "items": items
}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Publicate {len(items)} știri.")
