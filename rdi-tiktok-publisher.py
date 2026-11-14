#!/usr/bin/env python3
"""RDI -> TikTok Content Posting API publisher.

Supports approved video direct posts and photo posts. Safe by default:
RDI_TIKTOK_DRY_RUN=true never sends content to TikTok.
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

API = "https://open.tiktokapis.com/v2"
TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
DRY_RUN = os.getenv("RDI_TIKTOK_DRY_RUN", "true").lower() not in {"0", "false", "no"}
CONTENT_TYPE = os.getenv("RDI_TIKTOK_CONTENT_TYPE", "video").strip().lower()
VIDEO_FILE = pathlib.Path(os.getenv("RDI_TIKTOK_VIDEO_FILE", "/var/lib/rdi-tiktok/rdi-live-promo.mp4"))
PHOTO_URLS = [item.strip() for item in os.getenv("RDI_TIKTOK_PHOTO_URLS", "").split(",") if item.strip()]
TITLE = os.getenv(
    "RDI_TIKTOK_TITLE",
    "🔴 RDI è in diretta 24 ore su 24 | Link nel profilo #RDI #RadioRomaniiDinItalia",
)
DESCRIPTION = os.getenv(
    "RDI_TIKTOK_DESCRIPTION",
    "Ascolta Radio Românii din Italia in diretta 24/7. Segui RDI per notizie, musica e aggiornamenti dalla comunità romena in Italia.",
)


def api(method: str, path: str, payload: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("Manca TIKTOK_ACCESS_TOKEN")
    body = None
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode()
    request = urllib.request.Request(f"{API}{path}", data=body, method=method, headers=headers)
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


def publish_video() -> str:
    if not VIDEO_FILE.is_file():
        raise RuntimeError(f"Video non trovato: {VIDEO_FILE}")
    size = VIDEO_FILE.stat().st_size
    init = api("POST", "/post/publish/video/init/", {
        "post_info": {
            "title": TITLE[:2200],
            "privacy_level": creator_privacy(),
            "disable_comment": False,
            "disable_duet": False,
            "disable_stitch": False,
            "brand_organic_toggle": True,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": size,
            "total_chunk_count": 1,
        },
    })
    data = init.get("data") or {}
    upload_url = data.get("upload_url")
    publish_id = data.get("publish_id")
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
    return publish_id


def publish_photos() -> str:
    if not PHOTO_URLS:
        raise RuntimeError("Manca RDI_TIKTOK_PHOTO_URLS")
    if len(PHOTO_URLS) > 35:
        raise RuntimeError("TikTok permette al massimo 35 foto per post")
    result = api("POST", "/post/publish/content/init/", {
        "post_info": {
            "title": TITLE[:150],
            "description": DESCRIPTION[:2200],
            "privacy_level": creator_privacy(),
            "disable_comment": False,
            "auto_add_music": True,
        },
        "source_info": {
            "source": "PULL_FROM_URL",
            "photo_cover_index": 0,
            "photo_images": PHOTO_URLS,
        },
        "post_mode": "DIRECT_POST",
        "media_type": "PHOTO",
    })
    publish_id = (result.get("data") or {}).get("publish_id")
    if not publish_id:
        raise RuntimeError(f"TikTok non ha restituito publish_id: {result}")
    return publish_id


def main() -> None:
    if CONTENT_TYPE not in {"video", "photo"}:
        raise RuntimeError("RDI_TIKTOK_CONTENT_TYPE deve essere video oppure photo")
    if DRY_RUN:
        if CONTENT_TYPE == "video":
            if not VIDEO_FILE.is_file():
                raise RuntimeError(f"Video non trovato: {VIDEO_FILE}")
            print(f"BOZZA TikTok video: {VIDEO_FILE.name} ({VIDEO_FILE.stat().st_size} byte)")
        else:
            if not PHOTO_URLS:
                raise RuntimeError("Manca RDI_TIKTOK_PHOTO_URLS")
            print(f"BOZZA TikTok foto: {len(PHOTO_URLS)} URL")
        return
    publish_id = publish_video() if CONTENT_TYPE == "video" else publish_photos()
    print(f"TikTok Direct Post avviato ({CONTENT_TYPE}): {publish_id}")


if __name__ == "__main__":
    main()
