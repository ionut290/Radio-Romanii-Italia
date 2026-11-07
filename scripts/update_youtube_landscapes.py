#!/usr/bin/env python3
"""Build a credited Italy/Romania visual rotation from Wikimedia Commons.

Commons' public MediaWiki API needs no account or API key.  The script accepts
only public-domain/CC0/CC BY/CC BY-SA images and keeps the author, licence and
original file page on every card. It never downloads or republishes media.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import random
import re
import sys
from html import unescape
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "youtube-landscapes.json"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
MIN_PER_COUNTRY = 5

# Keep the public API use deliberately light: one search per country per day.
# The API returns up to 12 candidates for each of these broad, scenic queries.
TOPICS = {
    "Italia": "Italy landscape",
    "România": "Romania landscape",
}


def is_host(url: str, host: str, path_prefix: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == host and parsed.path.startswith(path_prefix)


def is_commons_image(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname in {"upload.wikimedia.org", "thumb.wikimedia.org"} and parsed.path.startswith("/wikipedia/commons/")


def clean_html(value: object) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", unescape(text)).strip()


def title(country: str, topic: str) -> str:
    if country == "Italia":
        return "PEISAJ ITALIAN · ITALIA"
    if country == "România":
        return "PEISAJ ROMÂNESC · ROMÂNIA"
    short = topic.replace(" Romania", "").replace(" Italy", "").upper()
    return f"{short} · {country.upper()}"


def permitted_license(name: str, url: str) -> bool:
    compact = name.casefold().replace(" ", "")
    if not (url.startswith("https://creativecommons.org/") or url.startswith("https://commons.wikimedia.org/")):
        return False
    if "cc0" in compact or "publicdomain" in compact:
        return True
    return compact.startswith("ccby") and "-nc" not in compact and "-nd" not in compact


def commons_item(page: dict, country: str, topic: str, reviewed_on: str) -> dict | None:
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata") or {}
    asset_id = str(page.get("pageid") or "")
    image = str(info.get("thumburl") or "")
    filename = str(page.get("title") or "")
    licence_name = clean_html((meta.get("LicenseShortName") or {}).get("value"))
    licence_url = str((meta.get("LicenseUrl") or {}).get("value") or "")
    author = clean_html((meta.get("Artist") or {}).get("value")) or "Wikimedia Commons"
    if not (asset_id.isdigit() and filename.startswith("File:") and is_commons_image(image)
            and re.search(r"\.(?:jpe?g|png|webp)$", urlparse(image).path, re.I)
            and permitted_license(licence_name, licence_url)):
        return None
    return {
        "id": f"{country[:2].lower()}-commons-{asset_id}", "country": country, "title": title(country, topic),
        "kind": "commons", "src": image, "poster": image,
        "source_url": "https://commons.wikimedia.org/wiki/" + quote(filename.replace(" ", "_"), safe=":_"),
        "credit": f"{author[:100]} · {licence_name} / Wikimedia Commons", "license_url": licence_url,
        "audio_muted": True, "editorial_visual": True,
        "rights_reviewed": True, "reviewed_on": reviewed_on,
    }


def get_json(query: str) -> dict:
    params = {"action": "query", "format": "json", "formatversion": "2", "generator": "search",
              "gsrsearch": f"{query} filetype:bitmap", "gsrnamespace": "6", "gsrlimit": "12",
              "prop": "imageinfo", "iiprop": "url|extmetadata", "iiurlwidth": "1280"}
    request = Request(f"{COMMONS_API}?{urlencode(params)}", headers={"Accept": "application/json", "User-Agent": "RDI-Live-Visuals/1.0"})
    with urlopen(request, timeout=20) as response:
        return json.load(response)


def interleave(by_country: dict[str, list[dict]]) -> list[dict]:
    result: list[dict] = []
    indexes = {country: 0 for country in by_country}
    while any(indexes[country] < len(by_country[country]) for country in by_country):
        for country in ("Italia", "România"):
            index = indexes[country]
            if index < len(by_country[country]):
                result.append(by_country[country][index])
                indexes[country] += 1
    return result[:20]


def build_config(today: str) -> dict:
    by_country: dict[str, list[dict]] = {country: [] for country in TOPICS}
    seen: set[str] = set()
    for country, topics in TOPICS.items():
        payload = get_json(topics)
        for record in (payload.get("query") or {}).get("pages") or []:
            item = commons_item(record, country, topics, today)
            if item and item["id"] not in seen:
                seen.add(item["id"])
                by_country[country].append(item)
    missing = [country for country, items in by_country.items() if len(items) < MIN_PER_COUNTRY]
    if missing:
        raise RuntimeError("Not enough valid Wikimedia visuals for: " + ", ".join(missing))
    for items in by_country.values():
        random.SystemRandom().shuffle(items)
    return {
        "schema_version": 1, "enabled": True, "after_news_cards": 8, "duration_seconds": 16,
        "description": "Intermezzi Wikimedia Commons aggiornati automat, con autore e licență; ordine casuale senza ripetizioni immediate.",
        "provider": "Wikimedia Commons API", "provider_url": "https://commons.wikimedia.org/",
        "generated_on": today, "items": interleave(by_country),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    today = dt.date.today().isoformat()
    config = build_config(today)
    text = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
    if args.dry_run:
        print(text)
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"Wrote {len(config['items'])} credited visuals to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
