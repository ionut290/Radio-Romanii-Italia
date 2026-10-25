#!/usr/bin/env python3
"""Append editorial articles to a persistent public archive before/after feed pruning.

Runs in editorial.yml. The time-limited homepage list is *not* the archive.
"""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CURRENT = ROOT / "editorial.json"
DEST = ROOT / "data/editorial-archive.json"

def load(path, fallback):
    if not path.exists():
        return fallback
    value = json.loads(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else fallback

def main():
    current = load(CURRENT, {"items": []})
    previous = load(DEST, {"items": []})
    records = {}
    for article in previous.get("items", []):
        if isinstance(article, dict):
            key = str(article.get("id") or article.get("url") or "").strip()
            if key:
                records[key] = article
    added = 0
    for article in current.get("items", []):
        if not isinstance(article, dict) or not article.get("editorial"):
            continue
        if not article.get("title") or not article.get("published") or not article.get("url"):
            continue
        key = str(article.get("id") or article.get("url"))
        if key not in records:
            added += 1
        # The latest publication is authoritative, including any editorial corrections.
        records[key] = article
    values = sorted(records.values(), key=lambda a: str(a.get("published", "")), reverse=True)
    target = {"description": "Arhiva permanentă a materialelor publicate de redacția RDI; feedul de actualitate rămâne limitat la 48 de ore.", "items": values}
    new = json.dumps(target, ensure_ascii=False, indent=2) + "\n"
    old = DEST.read_text(encoding="utf-8") if DEST.exists() else ""
    if new != old:
        DEST.parent.mkdir(parents=True, exist_ok=True)
        DEST.write_text(new, encoding="utf-8")
    print(f"Arhivă: {len(values)} materiale; {added} adăugate.")

if __name__ == "__main__":
    main()
