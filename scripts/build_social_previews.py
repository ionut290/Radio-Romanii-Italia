#!/usr/bin/env python3
"""Build crawler-readable share previews for current RDI news and events."""
import datetime as dt
import hashlib
import html
import io
import json
import os
import re
import unicodedata
from pathlib import Path
from zoneinfo import ZoneInfo
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont, ImageOps
import cairosvg

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "articole"
IMAGES = ROOT / "share-images"
EVENTS = ROOT / "eventi"
BASE = "https://radioromanii.duckdns.org"
NOW = dt.datetime.now(dt.timezone.utc)
CUTOFF = NOW - dt.timedelta(hours=48)
OUT.mkdir(exist_ok=True)
IMAGES.mkdir(exist_ok=True)
EVENTS.mkdir(exist_ok=True)
logo_path = ROOT / "RADIO-LOGO.png"
logo = Image.open(logo_path).convert("RGBA") if logo_path.exists() else None

def article_id(item):
    raw = str(item.get("id") or item.get("url") or (str(item.get("title", "")) + "|" + str(item.get("published", ""))))
    h = 2166136261
    for unit in raw.encode("utf-16-le"):
        pass
    data = raw.encode("utf-16-le")
    for i in range(0, len(data), 2):
        code = data[i] | (data[i + 1] << 8)
        h = ((h ^ code) * 16777619) & 0xffffffff
    return format(h, "x")

def escape(s):
    return html.escape(str(s or ""), quote=True)

def readable_content(item):
    summary = str(item.get("summary") or "").strip()
    body = str(item.get("body") or "").strip()
    text = body if body and (item.get("extended_summary") or body.startswith(summary)) else "\n\n".join(x for x in (summary, body) if x)
    return "".join("<p>" + escape(part) + "</p>" for part in text.split("\n\n") if part.strip())

from social_cards import generate_card, _is_fallback_card

def make_image(item, ident, refresh=False, portrait=False, title=None, lang=None):
    return generate_card(item, ident, portrait=portrait, title=title, refresh=refresh, lang=lang)

def share_image_url(ident):
    """Change OG image URL whenever its pixels or contextual label change.

    Facebook may cache the old JPEG even after Scrape Again if og:image URL
    stays identical. The version query makes the newly rendered preview fresh.
    """
    asset = IMAGES / (ident + "-social.jpg")
    version = hashlib.sha256(asset.read_bytes()).hexdigest()[:12] if asset.exists() else "0"
    return BASE + "/share-images/" + ident + "-social.jpg?v=" + version

translations_file = ROOT / "news-translations.json"
translations = json.loads(translations_file.read_text(encoding="utf-8")).get("items", {}) if translations_file.exists() else {}
details_path = ROOT / "data" / "news-summaries.json"
expanded = json.loads(details_path.read_text(encoding="utf-8")).get("items", {}) if details_path.exists() else {}
articles = {}
for filename in ("news.json", "editorial.json", "data/daily-thought.json"):
    path = ROOT / filename
    if not path.exists():
        continue
    items = json.loads(path.read_text(encoding="utf-8")).get("items", [])
    for item in items:
        detail = expanded.get(str(item.get("id") or item.get("url")), expanded.get(item.get("url"), {}))
        if detail.get("body"):
            item = {**item, "body": detail["body"], "extended_summary": True}
        try:
            stamp = dt.datetime.fromisoformat(str(item["published"]).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                continue
            if not (CUTOFF <= stamp.astimezone(dt.timezone.utc) <= NOW):
                continue
            if not item.get("title"):
                continue
            articles[article_id(item)] = item
        except (ValueError, TypeError, KeyError):
            continue

valid_pages = set()
for ident, item in articles.items():
    title = str(item.get("title", ""))
    summary = " ".join(str(item.get("summary") or item.get("description") or item.get("body") or item.get("title") or "").split())[:190]
    url = BASE + "/articole/" + ident + "-social.html"
    make_image(item, ident)
    make_image(item, ident, portrait=True)
    image_url = share_image_url(ident)
    # The image Meta fetches must live on RDI. Hotlinking publisher CDNs
    # (e.g. s.iw.ro) caused a blank Facebook preview even when the image
    # loaded normally in the news card. generate_card() retries photo fetch,
    # but always publishes a valid same-origin JPEG.
    preview_image_url = image_url
    image_dimensions = '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">'
    intro = readable_content(item) or "<p>" + escape(title) + "</p>"
    target = BASE + "/?articolo=" + ident
    html_page = f"""<!doctype html><html lang="ro"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | RDI</title><meta name="description" content="{escape(summary)}"><link rel="canonical" href="{escape(url)}"><meta property="og:type" content="article"><meta property="og:site_name" content="RDI - Radio Romanii din Italia"><meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(summary)}"><meta property="og:url" content="{escape(url)}"><meta property="og:image" content="{escape(preview_image_url)}">{image_dimensions}<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title)}"><meta name="twitter:description" content="{escape(summary)}"><meta name="twitter:image" content="{escape(preview_image_url)}"><style>body{{font:18px system-ui;background:#101827;color:white;max-width:760px;margin:35px auto;padding:15px}}img{{width:100%;border-radius:16px}}a{{color:#f2c66c}}</style></head><body><img src="{escape(preview_image_url)}" alt="RDI"><h1>{escape(title)}</h1><section id="article-summary">{intro}</section><p><a href="{escape(target)}">Leggi su RDI / Citește pe RDI →</a></p></body></html>"""
    for name in (ident + ".html", ident + "-social.html"):
        (OUT / name).write_text(html_page, encoding="utf-8")
        valid_pages.add(name)
    key = str(item.get("id") or item.get("url") or (str(item.get("title", "")) + "|" + str(item.get("published", ""))))
    record = translations.get(key, {})
    for language in ("ro", "it"):
        localized = record.get(language, {})
        if not localized.get("title"):
            continue
        local_title = str(localized["title"])
        local_summary = " ".join(str(localized.get("summary") or localized.get("body") or localized.get("title") or summary).split())[:190]
        localized_url = BASE + "/articole/" + ident + "-" + language + "-social.html"
        make_image(item, ident + "-" + language, title=local_title, lang=language)
        make_image(item, ident + "-" + language, portrait=True, title=local_title, lang=language)
        local_image_url = share_image_url(ident + "-" + language)
        localized_target = BASE + "/?articolo=" + ident + "&lang=" + language
        page = html_page.replace(escape(title), escape(local_title)).replace(escape(url), escape(localized_url)).replace(escape(target), escape(localized_target)).replace(escape(image_url), escape(local_image_url)).replace('<html lang="ro">', '<html lang="' + language + '">')
        page = page.replace('<section id="article-summary">' + intro + '</section>', '<section id="article-summary">' + (readable_content(localized) or intro) + '</section>')
        if summary:
            page = page.replace(escape(summary), escape(local_summary))
        for name in (ident + "-" + language + ".html", ident + "-" + language + "-social.html"):
            (OUT / name).write_text(page, encoding="utf-8")
            valid_pages.add(name)
def event_legacy_id(item):
    city = str(item.get("city") or "italia")
    if city.startswith("Altedo") and item.get("date") == "2026-11-28":
        return "altedo-2026-11-28"
    slug = unicodedata.normalize("NFD", city.lower())
    slug = re.sub(r"[\u0300-\u036f]", "", slug)
    return str(item["date"]) + "-" + re.sub(r"[^a-z0-9]+", "-", slug)


valid_event_pages = set()
valid_images = {variant for ident in articles for variant in (ident + '-social', ident + '-facebook')}
for ident, item in articles.items():
    key = str(item.get('id') or item.get('url') or (str(item.get('title', '')) + '|' + str(item.get('published', ''))))
    record = translations.get(key, {})
    for language in ('ro', 'it'):
        if record.get(language, {}).get('title'):
            valid_images.add(ident + '-' + language + '-social')
            valid_images.add(ident + '-' + language + '-facebook')
events_path = ROOT / "events-auto.json"
today = NOW.astimezone(ZoneInfo("Europe/Rome")).date()
events = json.loads(events_path.read_text(encoding="utf-8")).get("events", []) if events_path.exists() else []
for event in events:
    try:
        start = dt.date.fromisoformat(event["date"])
        end = dt.date.fromisoformat(event.get("endDate") or event["date"])
    except (KeyError, TypeError, ValueError):
        continue
    if end < today or not event.get("title"):
        continue
    legacy = event_legacy_id(event)
    ident = legacy + "-" + article_id({"id": event.get("url") or str(event["title"]) + "|" + event["date"]})
    image_id = "event-" + ident
    valid_images.update((image_id + '-social', image_id + '-facebook'))
    make_image(event, image_id, refresh=True)
    make_image(event, image_id, refresh=True, portrait=True)
    title = str(event["title"])
    description = str(event.get("description") or title)
    dates = event["date"] + (" → " + end.isoformat() if end != start else "")
    meta = " · ".join(str(x) for x in (dates, event.get("city"), event.get("region")) if x)
    summary = " ".join((meta + " — " + description).split())[:190]
    url = BASE + "/eventi/" + ident + "-social.html"
    image_url = share_image_url(image_id)
    target = BASE + "/evenimente.html?event=" + ident + "#event-" + ident
    body = readable_content({"body": description})
    source = ""
    if str(event.get("url") or "").startswith("https://"):
        source = '<p><a href="' + escape(event["url"]) + '" target="_blank" rel="noopener noreferrer">' + escape(event.get("source") or "Organizator") + ' ↗</a></p>'
    page = f'''<!doctype html><!-- rdi-event-preview --><html lang="ro"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | RDI</title><meta name="description" content="{escape(summary)}"><link rel="canonical" href="{escape(url)}"><meta property="og:type" content="article"><meta property="og:site_name" content="RDI - Radio Romanii din Italia"><meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(summary)}"><meta property="og:url" content="{escape(url)}"><meta property="og:image" content="{escape(image_url)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title)}"><meta name="twitter:description" content="{escape(summary)}"><meta name="twitter:image" content="{escape(image_url)}"><link rel="stylesheet" href="../rdi-sharing.css?v=20261024-ios-native-fb-v2"><style>body{{font:18px system-ui;background:#101827;color:white;max-width:760px;margin:35px auto;padding:15px}}img{{width:100%;border-radius:16px}}a{{color:#f2c66c}}p{{line-height:1.6}}</style><script src="../rdi-sharing.js?v=20261024-ios-native-fb-v2"></script></head><body><img src="{escape(image_url)}" alt="{escape(title)}"><h1>{escape(title)}</h1><p>{escape(meta)}</p><div id="event-share"></div><section id="event-description">{body}</section>{source}<p><a href="{escape(target)}">Leggi su RDI / Citește pe RDI →</a></p><script>const eventData={json.dumps({**event, "eventId": ident, "summary": meta, "body": description}, ensure_ascii=True).replace('<', chr(92) + 'u003c')};document.getElementById("event-share").append(rdiShareButton(eventData));</script></body></html>'''
    # Preserve existing shared event URLs, while distinct same-city events get
    # their own stable canonical address. No redirect: crawlers read this page.
    for name in (ident + ".html", ident + "-social.html", legacy + ".html"):
        if name == legacy + ".html" and name in valid_event_pages:
            continue
        (EVENTS / name).write_text(page, encoding="utf-8")
        valid_event_pages.add(name)

for existing in EVENTS.glob("*.html"):
    if existing.name not in valid_event_pages and "<!-- rdi-event-preview -->" in existing.read_text(encoding="utf-8"):
        existing.unlink()
# Preserve previews linked from the Facebook publication register, including
# articles that have disappeared from the rolling news feed. Scheduled and
# published Facebook URLs must not become 404s when RSS items expire.
registry_path = ROOT / "data" / "facebook-drafts.json"
if registry_path.exists():
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise RuntimeError("Cannot read Facebook publication register; refusing to prune previews") from exc
    for entry in registry.get("items", []):
        path = urlsplit(str(entry.get("article_url") or "")).path
        match = re.fullmatch(r"/articole/([0-9a-f]+)-(?:ro|it)-social\.html", path)
        if not match:
            continue
        ident = match.group(1)
        for ending in (".html", "-social.html", "-ro.html", "-ro-social.html", "-it.html", "-it-social.html"):
            name = ident + ending
            if (OUT / name).is_file():
                valid_pages.add(name)
        for ending in ("-social", "-facebook", "-ro-social", "-ro-facebook", "-it-social", "-it-facebook"):
            name = ident + ending
            if (IMAGES / (name + ".jpg")).is_file():
                valid_images.add(name)

for folder, suffix in ((OUT, ".html"), (IMAGES, ".jpg")):
    for existing in folder.glob("*" + suffix):
        if (folder == OUT and existing.name not in valid_pages) or (folder == IMAGES and existing.stem not in valid_images):
            existing.unlink()
print(f"Generated {len(articles)} current article previews; expired files removed.")
print(f"Generated {len(valid_event_pages)} event pages; events remain shareable through their end date.")
