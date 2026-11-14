#!/usr/bin/env python3
"""RDI -> Facebook Page publisher.

Safe by default: RDI_FB_DRY_RUN=true only builds the queue and never publishes.
Set RDI_FB_DRY_RUN=false on Oracle after the Page token has been verified.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import formatdate

NEWS_URL = os.getenv(
    "RDI_NEWS_URL",
    "https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/main/news.json",
)
STATE_FILE = pathlib.Path(os.getenv("RDI_FB_STATE_FILE", "/var/lib/rdi-facebook/state.json"))
MAX_POSTS = max(1, min(int(os.getenv("RDI_FB_MAX_POSTS", "3")), 10))
DRY_RUN = os.getenv("RDI_FB_DRY_RUN", "true").lower() not in {"0", "false", "no"}
GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v27.0")
PAGE_ID = os.getenv("RDI_FB_PAGE_ID", "")
PAGE_TOKEN = os.getenv("RDI_FB_PAGE_TOKEN", "")
PAGE_TOKEN_FILE = os.getenv("RDI_FB_PAGE_TOKEN_FILE", "")
if not PAGE_TOKEN and PAGE_TOKEN_FILE:
    try:
        PAGE_TOKEN = pathlib.Path(PAGE_TOKEN_FILE).read_text(encoding="utf-8").strip()
    except OSError:
        PAGE_TOKEN = ""


def read_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": "RDI-Facebook-Publisher/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"published": {}, "last_run": None}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE_FILE)


def item_key(item: dict) -> str:
    raw = str(item.get("url") or item.get("title") or "").strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def message_for(item: dict) -> str:
    title = " ".join(str(item.get("title") or "").split())
    summary = " ".join(str(item.get("summary") or "").split())
    source = " ".join(str(item.get("source") or "RDI").split())
    category = str(item.get("category") or "").strip()
    prefix = "🇷🇴" if category.lower() == "românia" else "📰"
    lines = [f"{prefix} {title}"]
    if summary:
        lines.append(summary[:420])
    lines.append(f"Fonte: {source}")
    lines.append("#RadioRomaniiDinItalia #RDI")
    return "\n\n".join(lines)


def publish(item: dict) -> str:
    if DRY_RUN:
        return "dry-run"
    if not PAGE_ID or not PAGE_TOKEN:
        raise RuntimeError("RDI_FB_PAGE_ID e RDI_FB_PAGE_TOKEN sono obbligatori per pubblicare")
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PAGE_ID}/feed"
    body = urllib.parse.urlencode({
        "message": message_for(item),
        "link": str(item["url"]),
        "published": "true",
        "access_token": PAGE_TOKEN,
    }).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("User-Agent", "RDI-Facebook-Publisher/1.0")
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("id"):
        raise RuntimeError(f"Facebook non ha restituito l'id del post: {payload}")
    return str(payload["id"])


def main() -> None:
    feed = read_json(NEWS_URL)
    items = feed.get("items") if isinstance(feed, dict) else []
    if not isinstance(items, list):
        raise RuntimeError("news.json non contiene una lista items")
    state = load_state()
    published = state.setdefault("published", {})
    candidates = []
    for item in items:
        if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
            continue
        key = item_key(item)
        if key not in published:
            candidates.append((key, item))
    candidates.sort(key=lambda pair: str(pair[1].get("published") or ""), reverse=True)
    selected = candidates[:MAX_POSTS]
    results = []
    for key, item in selected:
        result = publish(item)
        published[key] = {
            "url": item["url"],
            "title": item["title"],
            "published_at": datetime.now(timezone.utc).isoformat(),
            "facebook_id": result,
            "mode": "dry-run" if DRY_RUN else "published",
        }
        results.append(f"{'BOZZA' if DRY_RUN else 'PUBBLICATO'}: {item['title']}")
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    print(f"RDI Facebook: {len(results)} elementi gestiti; modalità={'dry-run' if DRY_RUN else 'pubblicazione'}")
    for line in results:
        print(line)


if __name__ == "__main__":
    main()
