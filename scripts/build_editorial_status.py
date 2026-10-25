#!/usr/bin/env python3
"""Build the source-linked RDI editorial desk status.

The dashboard is a working queue: it prioritises useful Romania–Italy coverage,
rather than treating every imported headline as an editorial assignment.
"""
import datetime as dt
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data/editorial-status.json"

PRIORITY_CATEGORIES = {"diaspora", "știri consulare", "drepturile muncitorilor"}
RELEVANCE_TERMS = (
    "român", "roman", "romeni", "romania", "diaspora", "italia", "italian",
    "consulat", "ambasad", "econsulat", "inps", "patronato", "lavoro",
    "munc", "pensi", "naspi", "permesso", "reziden", "cittadin", "sanit",
    "scoal", "școal", "chirie", "locuin", "famil",
)
EXCLUDED_TERMS = (
    "serie a", "calcio", "fotbal", "diretta", "podcast", "videogallery",
    "skateboard", "festival del cinema", "oroscop", "meteo nazionale",
)

def read(path, fallback):
    try:
        data = json.loads((ROOT / path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else fallback
    except (OSError, ValueError):
        return fallback

def words(body):
    return len(str(body or "").split())

def searchable(item):
    return " ".join(str(item.get(k) or "") for k in ("title", "summary", "body", "category", "source", "reason")).casefold()

def is_relevant(item):
    text = searchable(item)
    if any(term in text for term in EXCLUDED_TERMS):
        return False
    category = str(item.get("category") or "").casefold()
    return category in PRIORITY_CATEGORIES or any(term in text for term in RELEVANCE_TERMS)

def verification_state(item):
    """Green is source-grounded long-form; yellow is useful but awaits more work."""
    body_words = words(item.get("body"))
    sources = item.get("source_urls")
    source_count = len([x for x in sources if isinstance(x, str) and x.startswith("https://")]) if isinstance(sources, list) else 0
    if bool(item.get("editorial")) and body_words >= 350 and source_count >= 2:
        return "verde"
    if body_words >= 400 and source_count >= 1:
        return "verde"
    if is_relevant(item) and (body_words >= 100 or len(str(item.get("summary") or "")) >= 80):
        return "galben"
    return "roșu"

def radio_angle(item):
    category = str(item.get("category") or "").casefold()
    if category == "știri consulare":
        return "Ce trebuie verificat sau făcut concret de către românii din Italia?"
    if category == "drepturile muncitorilor":
        return "Ce drept sau serviciu poate folosi un lucrător român din Italia?"
    if category == "diaspora":
        return "Cum schimbă această informație viața comunității românești din Italia?"
    return "De ce poate fi utilă această informație pentru românii din Italia?"

def radio_intro(item):
    text = re.sub(r"\s+", " ", str(item.get("summary") or item.get("body") or "")).strip()
    if not text:
        return "Redacția verifică informațiile disponibile înainte de difuzare."
    sentence = re.split(r"(?<=[.!?])\s+", text)[0].strip()
    return sentence[:360]

def compact(item, include_words=True):
    value = {
        "title": str(item.get("title") or "Fără titlu")[:220],
        "category": str(item.get("category") or ""),
        "published": str(item.get("published") or ""),
        "url": str(item.get("url") or "")[:500],
        "source": str(item.get("source") or "")[:120],
        "status": verification_state(item),
    }
    if include_words:
        value["words"] = words(item.get("body"))
    return value

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
        queue_entries = [dict(x, url=x.get("url") or key) for key, x in queue.items() if isinstance(x, dict)]
    else:
        queue_entries = []

    priority_pending = [x for x in queue_entries if is_relevant(x)]
    priority_pending.sort(key=lambda x: (x.get("attempts", 0), str(x.get("title") or "")))
    missing = [x for x in feed_items if not words(x.get("body"))]
    expanded = [x for x in feed_items if words(x.get("body")) >= 400]

    editorial_pool = [x for x in editorial_items + feed_items if is_relevant(x)]
    states = {name: sum(1 for x in editorial_pool if verification_state(x) == name) for name in ("verde", "galben", "roșu")}
    radio_pool = [x for x in editorial_pool if verification_state(x) in ("verde", "galben")]
    radio_pool.sort(key=lambda x: (verification_state(x) != "verde", str(x.get("published") or "")), reverse=False)

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
        "pending_total": len(priority_pending),
        "pending_filtered_out": len(queue_entries) - len(priority_pending),
        "editorial_verde": states["verde"],
        "editorial_galben": states["galben"],
        "editorial_rosu": states["roșu"],
        "pending": [{
            **compact(x, include_words=False),
            "reason": str(x.get("reason") or x.get("motivo") or "În așteptarea verificării")[:260],
            "attempts": x.get("attempts", 0) if isinstance(x.get("attempts", 0), int) else 0,
        } for x in priority_pending[:60]],
        "recent_news": [compact(x) for x in feed_items[:100]],
        "radio_briefs": [{
            **compact(x),
            "intro": radio_intro(x),
            "question": radio_angle(x),
        } for x in radio_pool[:5]],
    }
    new = json.dumps(status, ensure_ascii=False, indent=2) + "\n"
    old = DEST.read_text(encoding="utf-8") if DEST.exists() else ""
    if new != old:
        DEST.parent.mkdir(parents=True, exist_ok=True)
        DEST.write_text(new, encoding="utf-8")
    print(f"RDI: feed {len(feed_items)}, extended {len(expanded)}, priority queue {len(priority_pending)}/{len(queue_entries)}")

if __name__ == "__main__":
    main()
