#!/usr/bin/env python3
"""Additional verified public RSS titles for the RDI editorial aggregator.

No full-text scraping, photos or third-party article copies: only titles and links.
Sources are isolated, fetched concurrently and may fail without blocking RDI.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import email.utils
import html
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# Category, publisher, public feed, allowed destination host.
# News providers stay distinct from institutional sources.
EXTRA_RSS = (
    ("România", "Adevărul", "https://adevarul.ro/rss/index", "adevarul.ro"),
    ("România", "Economedia", "https://www.economedia.ro/feed", "economedia.ro"),
    ("România", "Radio România Actualități", "https://www.romania-actualitati.ro/rss", "romania-actualitati.ro"),
    ("România", "Profit.ro", "https://www.profit.ro/rss", "profit.ro"),
    ("România", "Economica.net", "https://www.economica.net/feed", "economica.net"),
    ("Italia", "Il Sole 24 Ore", "https://www.ilsole24ore.com/rss/italia--attualita.xml", "ilsole24ore.com"),
    ("Italia", "Il Sole 24 Ore Economia", "https://www.ilsole24ore.com/rss/economia.xml", "ilsole24ore.com"),
    ("Italia", "la Repubblica", "https://www.repubblica.it/rss/homepage/rss2.0.xml", "repubblica.it"),
    ("Italia", "Corriere della Sera", "https://www.corriere.it/rss/homepage.xml", "corriere.it"),
    ("Italia", "BolognaToday", "https://www.bolognatoday.it/rss", "bolognatoday.it"),
    ("Italia", "Il Resto del Carlino", "https://www.ilrestodelcarlino.it/rss", "ilrestodelcarlino.it"),
    ("Italia", "Today", "https://www.today.it/rss", "today.it"),
    ("Italia", "Fanpage", "https://www.fanpage.it/feed/", "fanpage.it"),
    ("Mondo", "BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml", "bbc.co.uk"),
    ("Mondo", "The Guardian", "https://www.theguardian.com/world/rss", "theguardian.com"),
    ("Mondo", "Al Jazeera English", "https://www.aljazeera.com/xml/rss/all.xml", "aljazeera.com"),
    ("Mondo", "France 24", "https://www.france24.com/en/rss", "france24.com"),
    ("Mondo", "Deutsche Welle", "https://rss.dw.com/xml/rss-en-all", "dw.com"),
    ("Mondo", "Euronews English", "https://www.euronews.com/rss?format=mrss&level=theme&name=news", "euronews.com"),
    ("Mondo", "POLITICO Europe", "https://www.politico.eu/feed/", "politico.eu"),
    ("Unione europea", "Banca Centrale Europea", "https://www.ecb.europa.eu/rss/press.html", "ecb.europa.eu"),
    ("Istituzioni", "ONU", "https://news.un.org/feed/subscribe/en/news/all/rss.xml", "news.un.org"),
    ("Istituzioni", "INPS", "https://www.inps.it/it/it.rss.news.xml", "inps.it"),
)

OFFICIAL_PUBLISHERS = frozenset(("Banca Centrale Europea", "ONU", "INPS"))


def _hostname_matches(address, trusted):
    try:
        parsed = urllib.parse.urlparse(address)
        host = (parsed.hostname or "").casefold()
        return parsed.scheme == "https" and (host == trusted or host.endswith("." + trusted))
    except (ValueError, AttributeError):
        return False


def _text(element, name):
    for child in list(element):
        if child.tag.split("}")[-1].lower() == name:
            return (child.text or "").strip()
    return ""


def _published(entry):
    raw = _text(entry, "pubdate") or _text(entry, "published") or _text(entry, "updated")
    if not raw:
        return None
    try:
        date = email.utils.parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        try:
            date = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if date.tzinfo is None:
        date = date.replace(tzinfo=dt.timezone.utc)
    return date.astimezone(dt.timezone.utc)


def _article_link(entry):
    for child in list(entry):
        if child.tag.split("}")[-1].lower() != "link":
            continue
        if child.attrib.get("rel", "alternate") not in ("alternate", ""):
            continue
        link = (child.attrib.get("href") or child.text or "").strip()
        if link.startswith("https://"):
            return link
    return ""


def _fetch_one(spec, now, headers):
    category, publisher, feed, publisher_host = spec
    try:
        request = urllib.request.Request(feed, headers=headers)
        with urllib.request.urlopen(request, timeout=8) as response:
            if "xml" not in response.headers.get("Content-Type", "").lower() and "rss" not in response.headers.get("Content-Type", "").lower():
                # Some feeds use application/octet-stream; parse the body in that case.
                if response.headers.get("Content-Type", "").lower().startswith("text/html"):
                    raise ValueError("RSS returned HTML")
            root = ET.fromstring(response.read(1_700_000))
        results = []
        for entry in root.iter():
            if entry.tag.split("}")[-1].lower() not in ("item", "entry"):
                continue
            title = " ".join(html.unescape(_text(entry, "title")).split())
            url = _article_link(entry)
            date = _published(entry)
            if not title or not url or not _hostname_matches(url, publisher_host) or date is None:
                continue
            age = now - date
            if not dt.timedelta(hours=-1) <= age <= dt.timedelta(hours=48):
                continue
            item = {
                "category": category,
                "title": title[:240],
                "url": url,
                "source": publisher,
                "published": date.isoformat(),
                "summary": "",  # Avoid redistributing copyrighted excerpts.
                "image": "",
                "source_tier": "official" if publisher in OFFICIAL_PUBLISHERS else "news",
            }
            if publisher in OFFICIAL_PUBLISHERS:
                item["source_type"] = "comunicato_istituzionale"
            results.append(item)
            if len(results) >= 6:
                break
        return publisher, results, None
    except Exception as exc:
        return publisher, [], str(exc)


def collect_extra_news(now, already_seen, headers):
    """Fetch 23 outlets concurrently, with no duplicate records in the shared feed."""
    articles = []
    with ThreadPoolExecutor(max_workers=8, thread_name_prefix="rdi-rss") as pool:
        tasks = [pool.submit(_fetch_one, spec, now, headers) for spec in EXTRA_RSS]
        for future in as_completed(tasks):
            publisher, fetched, error = future.result()
            if error:
                print(f"RSS secondario {publisher}: non disponibile ({error})")
                continue
            accepted = 0
            for item in fetched:
                url = item["url"]
                if url in already_seen:
                    continue
                already_seen.add(url)
                articles.append(item)
                accepted += 1
            print(f"RSS secondario {publisher}: {accepted} titoli")
    return articles
