#!/usr/bin/env python3
"""Build a credited Italy/Romania visual rotation from the Pexels API.

The resulting JSON contains only direct Pexels CDN URLs plus the corresponding
Pexels asset page and photographer credit.  It intentionally does not download
or republish stock files: the live page displays the URL returned by the API.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import random
import sys
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "youtube-landscapes.json"
LICENSE = "https://www.pexels.com/license/"
PHOTO_ENDPOINT = "https://api.pexels.com/v1/search"
VIDEO_ENDPOINT = "https://api.pexels.com/v1/videos/search"
MIN_PER_COUNTRY = 5

TOPICS = {
    "Italia": ["Rome Italy skyline", "Venice Italy canal", "Dolomites Italy", "Tuscany Italy landscape", "Sicily Italy coast", "Italian lake landscape"],
    "România": ["Bucharest Romania", "Transylvania Romania", "Carpathian Mountains Romania", "Danube Delta Romania", "Romania village landscape", "Romania castle landscape"],
}


def is_host(url: str, host: str, path_prefix: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == host and parsed.path.startswith(path_prefix)


def pexels_page(url: str, kind: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and parsed.hostname == "www.pexels.com" and parsed.path.startswith(f"/{kind}/")


def credit(record: dict) -> str:
    photographer = str(record.get("photographer") or record.get("user", {}).get("name") or "Pexels").strip()
    return f"{photographer[:110]} / Pexels"


def title(country: str, topic: str) -> str:
    short = topic.replace(" Romania", "").replace(" Italy", "").upper()
    return f"{short} · {country.upper()}"


def photo_item(record: dict, country: str, topic: str, reviewed_on: str) -> dict | None:
    source = str(record.get("url") or "")
    image = str((record.get("src") or {}).get("landscape") or "")
    asset_id = str(record.get("id") or "")
    if not (asset_id.isdigit() and pexels_page(source, "photo") and is_host(image, "images.pexels.com", "/photos/")):
        return None
    return {
        "id": f"{country[:2].lower()}-photo-{asset_id}", "country": country, "title": title(country, topic),
        "kind": "photo", "src": image, "poster": image, "source_url": source, "credit": credit(record),
        "license_url": LICENSE, "audio_muted": True, "editorial_visual": True,
        "rights_reviewed": True, "reviewed_on": reviewed_on,
    }


def preferred_video_file(record: dict) -> str | None:
    candidates = []
    for item in record.get("video_files") or []:
        link = str(item.get("link") or "")
        width, height = item.get("width") or 0, item.get("height") or 0
        if item.get("file_type") != "video/mp4" or not is_host(link, "videos.pexels.com", "/video-files/"):
            continue
        if not isinstance(width, int) or not isinstance(height, int) or width < 960 or height < 540:
            continue
        ratio_distance = abs((width / height) - (16 / 9))
        candidates.append((ratio_distance, -min(width, 1920), link))
    return min(candidates)[2] if candidates else None


def video_item(record: dict, country: str, topic: str, reviewed_on: str) -> dict | None:
    source = str(record.get("url") or "")
    asset_id = str(record.get("id") or "")
    video = preferred_video_file(record)
    poster = next((str(item.get("picture") or "") for item in record.get("video_pictures") or []
                   if is_host(str(item.get("picture") or ""), "images.pexels.com", "/videos/")), "")
    if not (asset_id.isdigit() and pexels_page(source, "video") and video and poster):
        return None
    return {
        "id": f"{country[:2].lower()}-video-{asset_id}", "country": country, "title": title(country, topic),
        "kind": "video", "src": video, "poster": poster, "source_url": source, "credit": credit(record),
        "license_url": LICENSE, "audio_muted": True, "editorial_visual": True,
        "rights_reviewed": True, "reviewed_on": reviewed_on,
    }


def get_json(endpoint: str, key: str, query: str) -> dict:
    request = Request(f"{endpoint}?{urlencode({'query': query, 'orientation': 'landscape', 'per_page': 3})}",
                      headers={"Authorization": key, "Accept": "application/json", "User-Agent": "RDI-Live-Visuals/1.0"})
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


def build_config(key: str, today: str) -> dict:
    by_country: dict[str, list[dict]] = {country: [] for country in TOPICS}
    seen: set[str] = set()
    for country, topics in TOPICS.items():
        for index, topic in enumerate(topics):
            # One short video per country/topic pair where available; otherwise
            # Pexels photographs keep the rotation fresh and lightweight.
            endpoint, converter = (VIDEO_ENDPOINT, video_item) if index < 2 else (PHOTO_ENDPOINT, photo_item)
            payload = get_json(endpoint, key, topic)
            records = payload.get("videos") if endpoint == VIDEO_ENDPOINT else payload.get("photos")
            for record in records or []:
                item = converter(record, country, topic, today)
                if item and item["id"] not in seen:
                    seen.add(item["id"])
                    by_country[country].append(item)
                    break
    missing = [country for country, items in by_country.items() if len(items) < MIN_PER_COUNTRY]
    if missing:
        raise RuntimeError("Not enough valid Pexels visuals for: " + ", ".join(missing))
    for items in by_country.values():
        random.SystemRandom().shuffle(items)
    return {
        "schema_version": 1, "enabled": True, "after_news_cards": 8, "duration_seconds": 16,
        "description": "Intermezzi Pexels aggiornati automat, con autore e fonte; ordine casuale senza ripetizioni immediate.",
        "provider": "Pexels API", "provider_url": "https://www.pexels.com/",
        "generated_on": today, "items": interleave(by_country),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not key:
        print("PEXELS_API_KEY is required; no live configuration changed.", file=sys.stderr)
        return 2
    today = dt.date.today().isoformat()
    config = build_config(key, today)
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
