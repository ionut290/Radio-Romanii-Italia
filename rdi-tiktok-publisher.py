#!/usr/bin/env python3
"""RDI -> TikTok Direct Post publisher.

Generates no fake engagement. Publishes only an approved RDI promo video.
TikTok authorization is required; keep the access token in a secret.
"""
from __future__ import annotations

import json
import os
import pathlib
import urllib.error
import urllib.request

API = "https://open.tiktokapis.com/v2"
TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "").strip()
VIDEO_FILE = pathlib.Path(os.getenv("RDI_TIKTOK_VIDEO_FILE", "/var/lib/rdi-tiktok/rdi-live-promo.mp4"))
DRY_RUN = os.getenv("RDI_TIKTOK_DRY_RUN", "true").lower() not in {"0", "false", "no"}
TITLE = os.getenv(
    "RDI_TIKTOK_TITLE",
    "🔴 RDI è in diretta 24 ore su 24 | Link nel profilo #RDI #RadioRomaniiDinItalia",
)


def api(method: str, path: str, payload: dict | None = None) -> dict:
    if not TOKEN:
        raise RuntimeError("Manca TIKTOK_ACCESS_TOKEN")
    body = None
    headers = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json; charset=UTF-8"}
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode()
    request = urllib.request.Request(f"{API}{path}", data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TikTok API HTTP {error.code}: {detail}") from error


def main() -> None:
    if not VIDEO_FILE.is_file():
        raise RuntimeError(f"Video non trovato: {VIDEO_FILE}")
    size = VIDEO_FILE.stat().st_size
    if DRY_RUN:
        print(f"BOZZA TikTok: {VIDEO_FILE.name} ({size} byte)")
        return

    creator = api("POST", "/post/publish/creator_info/query/")
    info = creator.get("data") or {}
    options = info.get("privacy_level_options") or []
    privacy = "PUBLIC_TO_EVERYONE" if "PUBLIC_TO_EVERYONE" in options else (options[0] if options else None)
    if not privacy:
        raise RuntimeError("TikTok non ha restituito un livello privacy disponibile")

    init = api("POST", "/post/publish/video/init/", {
        "post_info": {
            "title": TITLE[:2200],
            "privacy_level": privacy,
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
    print(f"TikTok Direct Post avviato: {publish_id}")


if __name__ == "__main__":
    main()
