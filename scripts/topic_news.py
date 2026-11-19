#!/usr/bin/env python3
"""Bilancio tematico RDI: titoli recenti in italiano e romeno da Google News RSS.

Mostra soltanto titolo, editore, data e link originale/Google News.
Nessun testo integrale di terzi e nessuna notizia generata dall'IA.
"""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import datetime as dt
import email.utils
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# A category has two distinct, language-aware search queries.
# Keep these useful alongside the existing Romanian, Italian and diaspora news.
TOPIC_SEARCHES = (
    ("Muzică", "musica concerti cantanti nuovi album festival when:2d", "muzică artiști concerte albume festivaluri when:2d"),
    ("Cinema și seriale", "cinema film serie tv uscite festival when:2d", "filme cinema seriale actori premiere when:2d"),
    ("Tehnologie", "tecnologia smartphone software cybersecurity innovazione when:2d", "tehnologie telefoane software securitate cibernetică when:2d"),
    ("Inteligență artificială", '"intelligenza artificiale" modelli AI aziende ricerca when:2d', '"inteligența artificială" modele AI cercetare when:2d'),
    ("Educație", "scuola università istruzione formazione studenti when:2d", "educație școală universitate elevi studenți when:2d"),
    ("Știință", "scienza ricerca spazio astronomia scoperte when:2d", "știință cercetare descoperiri spațiu when:2d"),
    ("Sănătate", "salute medicina prevenzione ricerca sanitaria when:2d", "sănătate medicină prevenție cercetare when:2d"),
    ("Mediu și climă", "ambiente clima biodiversità energie rinnovabili when:2d", "mediu climă natură energie regenerabilă when:2d"),
    ("Sport", "sport calcio tennis ciclismo campionati when:2d", "sport fotbal tenis competiții campionate when:2d"),
    ("Cultură și cărți", "cultura libri arte musei teatro mostre when:2d", "cultură cărți literatură artă teatru when:2d"),
    ("Călătorii", "viaggi turismo itinerari destinazioni trasporti when:2d", "călătorii turism destinații trasee when:2d"),
    ("Economie și consumatori", "consumatori prezzi risparmio economia famiglie when:2d", "consumatori prețuri economii familie when:2d"),
)
MAX_PER_TOPIC = 4


def _fetch_topic(category, query, lang, now, headers):
    params = urllib.parse.urlencode({
        "q": query, "hl": f"{lang}-{'IT' if lang == 'it' else 'RO'}",
        "gl": "IT" if lang == "it" else "RO",
        "ceid": f"{'IT' if lang == 'it' else 'RO'}:{lang}",
    })
    url = "https://news.google.com/rss/search?" + params
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=7) as response:
        root = ET.fromstring(response.read(1_300_000))

    found = []
    for entry in root.findall("./channel/item")[:25]:
        title = html.unescape(entry.findtext("title") or "").strip()
        link = (entry.findtext("link") or "").strip()
        source = html.unescape(entry.findtext("source") or "").strip()
        if not title or not link.startswith("https://") or not source:
            continue
        # Google News often appends the publication after " - ".
        if title.endswith(" - " + source):
            title = title[:-(len(source) + 3)]
        try:
            published = email.utils.parsedate_to_datetime(entry.findtext("pubDate") or "")
            if published.tzinfo is None:
                published = published.replace(tzinfo=dt.timezone.utc)
            published = published.astimezone(dt.timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if not now - dt.timedelta(hours=48) <= published <= now + dt.timedelta(hours=1):
            continue
        found.append({
            "category": category,
            "title": re.sub(r"\\s+", " ", title)[:240],
            "url": link,
            "source": source[:90],
            "published": published.isoformat(),
            "summary": "",
            "image": "",
        })
        if len(found) == 4:
            break
    return found


def collect_topic_news(now, seen_urls, headers):
    """Fetch topics concurrently; keep a small balanced IT/RO selection per topic."""
    results = defaultdict(lambda: {"it": [], "ro": []})
    with ThreadPoolExecutor(max_workers=6, thread_name_prefix="rdi-topic") as pool:
        futures = {
            pool.submit(_fetch_topic, category, query, lang, now, headers): (category, lang)
            for category, italian, romanian in TOPIC_SEARCHES
            for lang, query in (("it", italian), ("ro", romanian))
        }
        for future in as_completed(futures):
            category, lang = futures[future]
            try:
                results[category][lang] = sorted(
                    future.result(), key=lambda article: article["published"], reverse=True
                )
            except Exception as exc:
                print(f"RDI topic {category} ({lang}): RSS indisponibile ({exc})")

    output = []
    seen_titles = set()
    for category, _, _ in TOPIC_SEARCHES:
        accepted = 0
        # Alternating outlets/languages prevents a single geography dominating.
        ro, it = results[category]["ro"], results[category]["it"]
        for index in range(4):
            for bucket in (ro, it):
                if index >= len(bucket) or accepted >= MAX_PER_TOPIC:
                    continue
                article = bucket[index]
                title_key = re.sub(r"[^\\w]+", " ", article["title"].casefold()).strip()
                if article["url"] in seen_urls or title_key in seen_titles:
                    continue
                seen_urls.add(article["url"])
                seen_titles.add(title_key)
                output.append(article)
                accepted += 1
            if accepted >= MAX_PER_TOPIC:
                break
        print(f"RDI topic {category}: {accepted} titoli")
    return output
