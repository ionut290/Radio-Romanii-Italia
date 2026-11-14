#!/usr/bin/env python3
"""RDI -> TikTok publisher fed by the public RDI website.

The publisher reads news.json from the RDI site/repository, selects fresh items,
uses RDI editorial images when available, and prepares photo or video posts.
Safe by default: RDI_TIKTOK_DRY_RUN=true never sends content to TikTok.
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request

API = "https://open.tiktokapis.com/v2"
TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
DRY_RUN = os.getenv("RDI_TIKTOK_DRY_RUN", "true").lower() not in {"0", "false", "no"}
CONTENT_TYPE = os.getenv("RDI_TIKTOK_CONTENT_TYPE", "photo").strip().lower()
NEWS_URL = os.getenv(
    "RDI_NEWS_URL",
    "https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/main/news.json",
)
SITE_URL = os.getenv(
    "RDI_SITE_URL",
    "https://ionut290.github.io/Radio-Romanii-Italia/",
)
LIVE_URL = os.getenv(
    "RDI_YOUTUBE_LIVE_URL",
    "https://www.youtube.com/watch?v=_qt-NjBcbtA",
)
VIDEO_FILE = pathlib.Path(os.getenv("RDI_TIKTOK_VIDEO_FILE", "/var/lib/rdi-tiktok/rdi-live-promo.mp4"))
PHOTO_URLS = [item.strip() for item in os.getenv("RDI_TIKTOK_PHOTO_URLS", "").split(",") if item.strip()]
MAX_NEWS = max(1, min(int(os.getenv("RDI_TIKTOK_MAX_NEWS", "3")), 10))


def read_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "RDI-TikTok-Publisher/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def public_url(value: str) -> str:
    if value.startswith(("http://", "https://")):
        return value
    return urllib.parse.urljoin(SITE_URL.rstrip("/") + "/", value.lstrip("./"))


def load_site_items() -> list[dict]:
    feed = read_json(NEWS_URL)
    items = feed.get("items") if isinstance(feed, dict) else []
    if not isinstance(items, list):
        return []
    valid = [item for item in items if isinstance(item, dict) and item.get("title") and item.get("url")]
    valid.sort(key=lambda item: str(item.get("published", "")), reverse=True)
    return valid[:MAX_NEWS]


def item_image(item: dict) -> str:
    # Prefer the RDI editorial illustration, then the source image.
    return public_url(str(item.get("fallbackImage") or item.get("image") or ""))


def compose_text(items: list[dict]) -> tuple[str, str]:
    if not items:
        return (
            "🔴 RDI è in diretta 24 ore su 24",
            f"Ascolta Radio Românii din Italia in diretta. {LIVE_URL} #RDI #RadioRomaniiDinItalia",
        )
    first = items[0]
    title = " ".join(str(first.get("title", "")).split())[:150]
    lines = [f"📰 {title}"]
    summary = " ".join(str(first.get("summary", "")).split())
    if summary:
        lines.append(summary[:500])
    lines.append(f"Fonte: {first.get('source', 'RDI')}")
    lines.append(f"Leggi sul sito RDI: {public_url(str(first['url']))}")
    lines.append(f"🎙️ Ascolta RDI live: {LIVE_URL}")
    lines.append("🔔 Segui RDI per le notizie della comunità romena in Italia.")
    return title, "\n\n".join(lines)[:2200]


def api(method: str, path: str, payload: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("Manca TIKTOK_ACCESS_TOKEN")
    body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
    request = urllib.request.Request(
        f"{API}{path}",
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json; charset=UTF-8",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TikTok API HTTP {error.code}: {detail}") from error


def creator_privacy() -> str:
    creator = api("POST", "/post/publish/creator_info/query/")
    options = (creator.get("data") or {}).get("privacy_level_options") or []
    if "PUBLIC_TO_EVERYONE" in options:
        return "PUBLIC_TO_EVERYONE"
    if options:
        return options[0]
    raise RuntimeError("TikTok non ha restituito un livello privacy disponibile")


def publish_video(title: str) -> str:
    if not VIDEO_FILE.is_file():
        raise RuntimeError(f"Video non trovato: {VIDEO_FILE}")
    size = VIDEO_FILE.stat().st_size
    init = api("POST", "/post/publish/video/init/", {
        "post_info": {
            "title": title[:2200],
            "privacy_level": creator_privacy(),
            "disable_comment": False,
            "disable_duet": False,
            "disable_stitch": False,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,
            "total_chunk_count": 1,
        },
    })
    data = init.get("data") or {}
    upload_url, publish_id = data.get("upload_url"), data.get("publish_id")
    if not upload_url or not publish_id:
        raise RuntimeError(f"TikTok non ha restituito upload_url/publish_id: {init}")
    payload = VIDEO_FILE.read_bytes()
    upload = urllib.request.Request(
        upload_url,
        data=payload,
        method="PUT",
        headers={
            "Content-Type": "video/mp4",
            "Content-Length": str(size),
            "Content-Range": f"bytes 0-{size - 1}/{size}",
        },
    )
    with urllib.request.urlopen(upload, timeout=120) as response:
        if response.status not in (200, 201, 204):
            raise RuntimeError(f"Upload TikTok fallito: HTTP {response.status}")
    return str(publish_id)


def publish_photos(title: str, description: str, photo_urls: list[str]) -> str:
    if not photo_urls:
        raise RuntimeError("Il sito RDI non ha fornito immagini utilizzabili")
    result = api("POST", "/post/publish/content/init/", {
        "post_info": {
            "title": title[:150],
            "description": description[:2200],
            "privacy_level": creator_privacy(),
            "disable_comment": False,
            "auto_add_music": True,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 0,
            "photo_images": photo_urls[:35],
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO",
    })
    publish_id = (result.get("data") or {}).get("publish_id")
    if not publish_id:
        raise RuntimeError(f"TikTok non ha restituito publish_id: {result}")
    return str(publish_id)


def main() -> None:
    if CONTENT_TYPE not in {"video", "photo"}:
        raise RuntimeError("RDI_TIKTOK_CONTENT_TYPE deve essere video oppure photo")
    items = load_site_items()
    title, description = compose_text(items)
    site_photos = [item_image(item) for item in items if item_image(item)]
    photos = PHOTO_URLS or site_photos
    if DRY_RUN:
        print(f"BOZZA RDI TikTok ({CONTENT_TYPE})")
        print(f"Titolo: {title}")
        print(f"Contenuti dal sito: {len(items)} notizie")
        if CONTENT_TYPE == "photo":
            print(f"Immagini: {len(photos)}")
            print("\n" + description)
        else:
            print(f"Video locale: {VIDEO_FILE}")
        return
    publish_id = publish_video(title) if CONTENT_TYPE == "video" else publish_photos(title, description, photos)
    print(f"TikTok Direct Post avviato ({CONTENT_TYPE}): {publish_id}")


if __name__ == "__main__":
    main()
