"""Attach reviewed original reporting to RSS entries without synthesizing facts."""
import json
from pathlib import Path


def enrich_items(items, path=Path('data/news-summaries.json')):
    try:
        records = json.loads(path.read_text(encoding='utf-8')).get('items', {})
        if not isinstance(records, dict):
            return items
    except (OSError, ValueError, TypeError):
        return items
    for item in items:
        detail = records.get(str(item.get('id') or item.get('url')), records.get(item.get('url'), {}))
        if not isinstance(detail, dict):
            continue
        body = detail.get('body')
        sources = detail.get('source_urls')
        if not (isinstance(body, str) and body.strip() and isinstance(sources, list)
                and any(isinstance(url, str) and url.startswith('https://') for url in sources)):
            continue
        item.update(body=body.strip(), extended_summary=True,
                    content_language=detail.get('language', ''), source_urls=sources)
    return items
