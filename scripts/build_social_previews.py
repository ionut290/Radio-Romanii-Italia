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

def make_image(item, ident, refresh=False):
    dest = IMAGES / (ident + ".jpg")
    source = str(item.get("image") or "")
    # SVG editoriali: rigenera il JPEG anche se esiste, per evitare anteprime obsolete.
    if dest.exists() and not refresh and not source.lower().split("?")[0].endswith(".svg"):
        return dest
    background = Image.new("RGB", (1200, 630), "#19314b")
    try:
        if source.startswith("./") or source.startswith("/"):
            path = ROOT / source.lstrip("./")
            if path.suffix.lower() == ".svg":
                img = Image.open(io.BytesIO(cairosvg.svg2png(url=str(path)))).convert("RGB")
            elif path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"):
                img = Image.open(path).convert("RGB")
            else:
                img = None
        elif source.startswith("https://"):
            host = urlsplit(source).hostname or ""
            if host.endswith((".jpg", ".jpeg", ".png", ".webp")):
                pass
            req = Request(source, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(req, timeout=10 if refresh else 3) as response:
                payload = response.read(4_000_000)
            img = Image.open(io.BytesIO(payload)).convert("RGB")
        else:
            img = None
        if img is not None:
            background = ImageOps.fit(img, (1200, 630))
    except Exception as e:
        print("Image fallback:", ident, str(e)[:80])
    overlay = Image.new("RGBA", (1200, 630), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle((0, 495, 1200, 630), fill=(10, 25, 43, 185))
    draw.text((42, 560), "RDI  |  Radio Romanii din Italia", fill=(255, 255, 255, 245))
    if logo:
        brand = logo.copy()
        brand.thumbnail((270, 270))
        brand.putalpha(brand.getchannel("A").point(lambda v: int(v * .22)))
        overlay.alpha_composite(brand, (1200 - brand.width - 35, 630 - brand.height - 35))
    Image.alpha_composite(background.convert("RGBA"), overlay).convert("RGB").save(dest, quality=83, optimize=True)
    return dest

translations_file = ROOT / "news-translations.json"
translations = json.loads(translations_file.read_text(encoding="utf-8")).get("items", {}) if translations_file.exists() else {}
details_path = ROOT / "data" / "news-summaries.json"
expanded = json.loads(details_path.read_text(encoding="utf-8")).get("items", {}) if details_path.exists() else {}
articles = {}
for filename in ("news.json", "editorial.json"):
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
    image_url = BASE + "/share-images/" + ident + ".jpg"
    url = BASE + "/articole/" + ident + "-social.html"
    make_image(item, ident)
    intro = readable_content(item) or "<p>" + escape(title) + "</p>"
    target = BASE + "/?articolo=" + ident
    html_page = f"""<!doctype html><html lang="ro"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | RDI</title><meta name="description" content="{escape(summary)}"><link rel="canonical" href="{escape(url)}"><meta property="og:type" content="article"><meta property="og:site_name" content="RDI - Radio Romanii din Italia"><meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(summary)}"><meta property="og:url" content="{escape(url)}"><meta property="og:image" content="{escape(image_url)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title)}"><meta name="twitter:description" content="{escape(summary)}"><meta name="twitter:image" content="{escape(image_url)}"><style>body{{font:18px system-ui;background:#101827;color:white;max-width:760px;margin:35px auto;padding:15px}}img{{width:100%;border-radius:16px}}a{{color:#f2c66c}}</style></head><body><img src="{escape(image_url)}" alt="RDI"><h1>{escape(title)}</h1><section id="article-summary">{intro}</section><p><a href="{escape(target)}">Leggi su RDI / Citește pe RDI →</a></p></body></html>"""
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
        localized_target = BASE + "/?articolo=" + ident + "&lang=" + language
        page = html_page.replace(escape(title), escape(local_title)).replace(escape(url), escape(localized_url)).replace(escape(target), escape(localized_target)).replace('<html lang="ro">', '<html lang="' + language + '">')
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
valid_images = set(articles)
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
    valid_images.add(image_id)
    make_image(event, image_id, refresh=True)
    title = str(event["title"])
    description = str(event.get("description") or title)
    dates = event["date"] + (" → " + end.isoformat() if end != start else "")
    meta = " · ".join(str(x) for x in (dates, event.get("city"), event.get("region")) if x)
    summary = " ".join((meta + " — " + description).split())[:190]
    url = BASE + "/eventi/" + ident + "-social.html"
    image_url = BASE + "/share-images/" + image_id + ".jpg"
    target = BASE + "/evenimente.html?event=" + ident + "#event-" + ident
    body = readable_content({"body": description})
    source = ""
    if str(event.get("url") or "").startswith("https://"):
        source = '<p><a href="' + escape(event["url"]) + '" target="_blank" rel="noopener noreferrer">' + escape(event.get("source") or "Organizator") + ' ↗</a></p>'
    page = f'''<!doctype html><!-- rdi-event-preview --><html lang="ro"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)} | RDI</title><meta name="description" content="{escape(summary)}"><link rel="canonical" href="{escape(url)}"><meta property="og:type" content="article"><meta property="og:site_name" content="RDI - Radio Romanii din Italia"><meta property="og:title" content="{escape(title)}"><meta property="og:description" content="{escape(summary)}"><meta property="og:url" content="{escape(url)}"><meta property="og:image" content="{escape(image_url)}"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{escape(title)}"><meta name="twitter:description" content="{escape(summary)}"><meta name="twitter:image" content="{escape(image_url)}"><link rel="stylesheet" href="../rdi-sharing.css?v=20261023-events"><style>body{{font:18px system-ui;background:#101827;color:white;max-width:760px;margin:35px auto;padding:15px}}img{{width:100%;border-radius:16px}}a{{color:#f2c66c}}p{{line-height:1.6}}</style><script src="../rdi-sharing.js?v=20261023-events"></script></head><body><img src="{escape(image_url)}" alt="{escape(title)}"><h1>{escape(title)}</h1><p>{escape(meta)}</p><div id="event-share"></div><section id="event-description">{body}</section>{source}<p><a href="{escape(target)}">Leggi su RDI / Citește pe RDI →</a></p><script>const eventData={json.dumps({**event, "eventId": ident, "summary": meta, "body": description}, ensure_ascii=True).replace('<', chr(92) + 'u003c')};document.getElementById("event-share").append(rdiShareButton(eventData));</script></body></html>'''
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
for folder, suffix in ((OUT, ".html"), (IMAGES, ".jpg")):
    for existing in folder.glob("*" + suffix):
        if (folder == OUT and existing.name not in valid_pages) or (folder == IMAGES and existing.stem not in valid_images):
            existing.unlink()
print(f"Generated {len(articles)} current article previews; expired files removed.")
print(f"Generated {len(valid_event_pages)} event pages; events remain shareable through their end date.")
