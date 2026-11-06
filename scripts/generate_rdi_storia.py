#!/usr/bin/env python3
"""RDI STORIA: genera cinque efemeridi documentate per la data italiana.

Fonte primaria: Wikimedia On This Day (Wikipedia).
Immagini: solo Wikimedia Commons con licenza libera verificata dall'API.
Senza risposte valide non sovrascrive i dati pubblicati.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
LATEST = ROOT / "data/storia-oggi.json"
ARCHIVE = ROOT / "data/storia-archivio"
USER_AGENT = "RDIStoria/1.0 (https://radioromanii.duckdns.org/; source attribution included)"
WIKI_URLS = (
    "https://api.wikimedia.org/feed/v1/wikipedia/{lang}/onthisday/events/{month}/{day}",
    "https://{lang}.wikipedia.org/api/rest_v1/feed/onthisday/events/{month}/{day}",
)


def fetch_json(url: str, timeout: int = 22) -> dict:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.load(response)
        if not isinstance(value, dict):
            raise ValueError("Risposta non JSON object")
        return value


def wikipedia_feed(lang: str, date: dt.date) -> list[dict]:
    for pattern in WIKI_URLS:
        url = pattern.format(lang=lang, month=date.strftime("%m"), day=date.strftime("%d"))
        try:
            value = fetch_json(url)
            events = value.get("events", [])
            if isinstance(events, list) and events:
                print("Fonte:", url, "eventi:", len(events))
                return [x for x in events if isinstance(x, dict)]
        except Exception as exc:
            print("Sorgente non disponibile:", url, str(exc)[:160], file=sys.stderr)
    return []


def short_text(text: str, limit: int = 430) -> str:
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", str(text)))).strip()
    return (text[: limit - 1].rsplit(" ", 1)[0] + "…") if len(text) > limit else text


def title_for(event: dict) -> str:
    pages = event.get("pages") if isinstance(event.get("pages"), list) else []
    for page in pages:
        if isinstance(page, dict):
            title = (page.get("titles") or {}).get("normalized") or page.get("title")
            if title:
                return short_text(str(title).replace("_", " "), 105)
    text = short_text(event.get("text") or "", 100)
    return text[:1].upper() + text[1:]


def years_match(a: dict, b: dict) -> bool:
    try:
        if int(a.get("year")) != int(b.get("year")):
            return False
    except (ValueError, TypeError):
        return False
    def ids(event):
        pages = event.get("pages") or []
        return {p.get("wikibase_item") for p in pages if isinstance(p, dict) and p.get("wikibase_item")}
    left, right = ids(a), ids(b)
    return bool(left and right and left.intersection(right))


def commons_filename(url: str) -> str | None:
    try:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname not in {"upload.wikimedia.org", "thumb.wikimedia.org"}:
            return None
        parts = urllib.parse.unquote(parsed.path).split("/")
        if "commons" not in parts:
            return None
        file = parts[-2] if "thumb" in parts else parts[-1]
        if not re.search(r"\.(jpg|jpeg|png|webp)$", file, re.I):
            return None
        return file
    except (ValueError, IndexError):
        return None


def license_ok(short_name: str) -> bool:
    s = short_name.lower().replace(" ", "").replace("-", "")
    return (
        s in {"cc0", "publicdomain", "pd"}
        or s.startswith("ccby")
        or "publicdomain" in s
    ) and not any(suffix in s for suffix in ("nc", "nd"))


def free_commons_image(event: dict, metadata_cache: dict) -> dict:
    for page in (event.get("pages") or [])[:4]:
        if not isinstance(page, dict):
            continue
        thumb = (page.get("originalimage") or {}).get("source") or (page.get("thumbnail") or {}).get("source")
        file = commons_filename(str(thumb or ""))
        if not file:
            continue
        if file not in metadata_cache:
            url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
                "action": "query", "format": "json", "prop": "imageinfo",
                "titles": "File:" + file, "iiprop": "url|extmetadata", "iiurlwidth": 1000
            })
            try:
                value = fetch_json(url)
                pages = (value.get("query") or {}).get("pages") or {}
                infos = next(iter(pages.values()), {}).get("imageinfo") or []
                metadata_cache[file] = infos[0] if infos else {}
            except Exception as exc:
                print("Metadati immagine non disponibili:", file, str(exc)[:100], file=sys.stderr)
                metadata_cache[file] = {}
        info = metadata_cache[file]
        ext = info.get("extmetadata") or {}
        licence = short_text((ext.get("LicenseShortName") or {}).get("value") or "", 90)
        if not license_ok(licence):
            continue
        image_url = info.get("thumburl") or info.get("url")
        if not image_url or not (urllib.parse.urlsplit(image_url).scheme == "https" and urllib.parse.urlsplit(image_url).hostname in {"upload.wikimedia.org", "thumb.wikimedia.org"} and urllib.parse.urlsplit(image_url).path.startswith("/wikipedia/commons/")):
            continue
        artist = short_text((ext.get("Artist") or {}).get("value") or "Wikimedia Commons", 110)
        file_page = "https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(file.replace(" ", "_"), safe="(),._-")
        return {
            "image": image_url, "image_page": file_page,
            "image_credit": artist, "image_license": licence,
            "image_note_it": "Immagine collegata all'argomento (non necessariamente scattata quel giorno)",
            "image_note_ro": "Imagine relevantă pentru subiect (nu neapărat realizată în acea zi)",
        }
    return {}


def page_source(event: dict, lang: str) -> str | None:
    for page in event.get("pages") or []:
        if not isinstance(page, dict):
            continue
        url = ((page.get("content_urls") or {}).get("desktop") or {}).get("page")
        if not isinstance(url, str):
            continue
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname == lang + ".wikipedia.org":
            return url
    return None


def create(date: dt.date) -> dict:
    primary = wikipedia_feed("it", date)
    language = "it"
    if len(primary) < 5:
        primary = wikipedia_feed("en", date)
        language = "en"
    if len(primary) < 5:
        raise RuntimeError("Troppi pochi eventi attendibili dalla fonte Wikipedia.")
    romanian = wikipedia_feed("ro", date)
    entries = []
    used_years = set()
    cache = {}
    # Prefer events with a Commons image that has reusable license metadata.
    candidates = []
    for raw in primary[:90]:
        try:
            year = int(raw["year"])
        except (ValueError, TypeError, KeyError):
            continue
        text = short_text(raw.get("text") or "")
        if not text or year < 1 or year > date.year:
            continue
        picture = free_commons_image(raw, cache)
        candidates.append((raw, year, text, picture))
        if len(candidates) >= 25:
            break
    candidates.sort(key=lambda row: (bool(row[3]), len(row[2])), reverse=True)
    for raw, year, content, picture in candidates:
        if year in used_years:
            continue
        source = page_source(raw, language)
        if not source:
            continue
        title = title_for(raw)
        item = {
            "year": year, "category": "Storia",
            "title_it": title,
            "text_it": content,
            "source": source,
        }
        if language == "en":
            # Non etichettare una traduzione inesistente come italiana.
            item["title_it"] = title
            item["text_it"] = content
            item["original_language"] = "en"
        if language == "it" and romanian:
            translated = next((r for r in romanian if years_match(raw, r)), None)
            if translated:
                item["title_ro"] = title_for(translated)
                item["text_ro"] = short_text(translated.get("text") or "")
        item.update(picture)
        entries.append(item)
        used_years.add(year)
        if len(entries) >= 5:
            break
    if len(entries) < 5:
        raise RuntimeError("Meno di cinque eventi unici e con fonte verificabile.")
    # Non pubblicare cinque contenuti privi di foto.
    if sum(bool(x.get("image")) for x in entries) < 2:
        raise RuntimeError("Sono disponibili meno di due immagini con licenza verificata; dati invariati.")
    entries.sort(key=lambda row: row["year"])
    return {
        "date": date.isoformat(), "editorial": "RDI STORIA", "status": "wikipedia-feed",
        "language": language, "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "attribution": "Testi basati sulla Wikipedia On This Day feed (CC BY-SA); fonte linkata per ogni evento. Immagini Wikimedia Commons con licenza indicata.",
        "events": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RDI STORIA - storia del giorno")
    parser.add_argument("--date", type=dt.date.fromisoformat)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    date = args.date or dt.datetime.now(ZoneInfo("Europe/Rome")).date()
    archived = ARCHIVE / (date.isoformat() + ".json")
    if not args.force and archived.exists():
        print("Edizione già archiviata:", archived)
        if not LATEST.exists() or json.loads(LATEST.read_text(encoding="utf-8")).get("date") != date.isoformat():
            LATEST.write_text(archived.read_text(encoding="utf-8"), encoding="utf-8")
        return
    result = create(date)
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    archived.write_text(content, encoding="utf-8")
    LATEST.parent.mkdir(parents=True, exist_ok=True)
    LATEST.write_text(content, encoding="utf-8")
    manifest = ARCHIVE / "index.json"
    existing = []
    if manifest.exists():
        existing = json.loads(manifest.read_text(encoding="utf-8")).get("dates", [])
    dates = sorted(set(x for x in existing if re.fullmatch(r"\d{4}-\d{2}-\d{2}", x)) | {date.isoformat()})
    manifest.write_text(json.dumps({"dates": dates}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("RDI STORIA generato:", date, len(result["events"]), "eventi,", sum(bool(e.get("image")) for e in result["events"]), "immagini")


if __name__ == "__main__":
    main()
