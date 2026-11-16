#!/usr/bin/env python3
"""Audit RDI's complete editorial archives on Oracle without changing production files."""
import argparse
import datetime as dt
import json
from pathlib import Path
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")

def load(root, name):
    path = root / name
    if not path.is_file():
        raise FileNotFoundError(f"Required repository file missing: {name}")
    return json.loads(path.read_text(encoding="utf-8"))

def items(data):
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        value = data.get("items", [])
        if isinstance(value, list):
            return [x for x in value if isinstance(x, dict)]
        if isinstance(value, dict):
            return [dict(v, url=v.get("url") or k) for k, v in value.items() if isinstance(v, dict)]
    return []

def entries(value):
    if isinstance(value, dict):
        return [dict(v, url=v.get("url") or k) for k, v in value.items() if isinstance(v, dict)]
    if isinstance(value, list):
        return [v for v in value if isinstance(v, dict)]
    return []

def words(text):
    return len(str(text or "").split())

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument("--output", type=Path, default=None)
    args = p.parse_args()
    root = args.repo.resolve()
    news = load(root, "news.json")
    geo = load(root, "data/geopolitica-news.json")
    summaries = load(root, "data/news-summaries.json")
    articles = load(root, "data/geopolitica-articles.json")
    ordinary = items(news)
    geopolitical = items(geo)
    summary_records = entries(summaries.get("items", {}) if isinstance(summaries, dict) else summaries)
    article_records = entries(articles.get("items", {}) if isinstance(articles, dict) else articles)
    pending = entries(summaries.get("pending", {})) if isinstance(summaries, dict) else []

    def overview(feed, archive):
        index = {str(x.get("url") or ""): x for x in archive if x.get("url")}
        missing, short, verified = [], [], []
        for item in feed:
            url = str(item.get("url") or "")
            entry = index.get(url)
            body = (entry or {}).get("body") or item.get("body") or ""
            count = words(body)
            record = {"url": url, "title": item.get("title", ""), "words": count}
            if count == 0:
                missing.append(record)
            elif count < 400:
                short.append(record)
            else:
                verified.append(record)
        return {"feed_total": len(feed), "archive_records": len(archive),
                "matching_400_words": len(verified), "missing_body": len(missing),
                "short_body": len(short), "missing_examples": missing[:20],
                "short_examples": short[:20],
                "note": "400+ parole indica lunghezza, non verifica indipendente delle fonti."}

    report = {
        "audited_at": dt.datetime.now(ROME).isoformat(),
        "repository": str(root),
        "ordinary": overview(ordinary, summary_records),
        "geopolitical": overview(geopolitical, article_records),
        "ordinary_pending_records": len(pending),
        "mode": "read_only",
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)

if __name__ == "__main__":
    main()
