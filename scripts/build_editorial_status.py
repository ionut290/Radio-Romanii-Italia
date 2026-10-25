#!/usr/bin/env python3
"""Create a small, source-linked editorial status snapshot for the RDI dashboard."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data/editorial-status.json"

def read(path, fallback):
    try:
        data = json.loads((ROOT / path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except (OSError, ValueError):
        return fallback

def words(body):
    return len(str(body or "").split())

def main():
    news = read("news.json", {"items": []})
    editorial = read("editorial.json", {"items": []})
    summary = read("data/news-summaries.json", {"items": {}, "pending": {}})
    translations = read("news-translations.json", {"items": {}})
    archive = read("data/editorial-archive.json", {"items": []})
    feed_items = [x for x in news.get("items", []) if isinstance(x, dict)]
    editorial_items = [x for x in editorial.get("items", []) if isinstance(x, dict)]
    queue = summary.get("pending", {})
    if isinstance(queue, list):
        queue_entries = [x for x in queue if isinstance(x, dict)]
    elif isinstance(queue, dict):
        queue_entries = [
            dict(x, url=x.get("url") or key)
            for key, x in queue.items() if isinstance(x, dict)
        ]
    else:
        queue_entries = []
    missing = [x for x in feed_items if not words(x.get("body"))]
    expanded = [x for x in feed_items if words(x.get("body")) >= 400]
    status = {
        "news_updated_at": news.get("updated_at"),
        "editorial_updated_at": editorial.get("updated_at"),
        "translations_updated_at": translations.get("updated_at"),
        "feed_total": len(feed_items),
        "feed_extended_400": len(expanded),
        "feed_missing_body": len(missing),
        "feed_short_body": len(feed_items) - len(missing) - len(expanded),
        "editorial_total": len(editorial_items),
        "archived_editorials": len(archive.get("items", [])),
        "translation_records": len(translations.get("items", {})),
        "pending_total": len(queue_entries),
        "pending": [{
            "title": str(x.get("title") or "Fără titlu")[:220],
            "url": str(x.get("url") or "")[:500],
            "reason": str(x.get("reason") or x.get("motivo") or "În așteptarea verificării")[:260],
            "attempts": x.get("attempts", 0) if isinstance(x.get("attempts", 0), int) else 0
        } for x in queue_entries[:120]],
        "recent_news": [{
            "title": str(x.get("title") or "")[:220],
            "category": str(x.get("category") or ""),
            "published": str(x.get("published") or ""),
            "url": str(x.get("url") or ""),
            "words": words(x.get("body")),
            "source": str(x.get("source") or "")
        } for x in feed_items[:100]]
    }
    new = json.dumps(status, ensure_ascii=False, indent=2) + "\n"
    old = DEST.read_text(encoding="utf-8") if DEST.exists() else ""
    if new != old:
        DEST.parent.mkdir(parents=True, exist_ok=True)
        DEST.write_text(new, encoding="utf-8")
    print(f"RDI: feed {len(feed_items)}, complete {len(expanded)}, no body {len(missing)}, pending {len(queue_entries)}")

if __name__ == "__main__":
    main()
