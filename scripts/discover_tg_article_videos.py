#!/usr/bin/env python3
"""Find video candidates embedded in RDI news sources for rights review.

Discovery is NOT a broadcast license. Never download, republish or stream a
publisher's embedded video automatically; require a verified event_clip grant
in data/tg-video-licenses.json before the evening TG can show it.
"""
from __future__ import annotations

import argparse
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DIRECT_VIDEO_TYPES = {"video/mp4", "video/webm"}
META_NAMES = {
    "og:video", "og:video:url", "og:video:secure_url",
    "twitter:player:stream", "video:content_url",
}
MAX_PAGE_BYTES = 700_000
MAX_ITEMS = 12


def public_link(url: str) -> bool:
    try:
        p = urlparse(url)
        h = (p.hostname or "").lower()
        return (p.scheme == "https" and "." in h and
                not h.endswith((".local", ".internal", ".localhost")) and
                h not in {"localhost", "127.0.0.1", "10.0.0.1",
                          "news.google.com", "www.youtube.com"} and
                not p.username and not p.password and len(url) < 1800)
    except ValueError:
        return False


class VideoReferences(HTMLParser):
    def __init__(self, base: str):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.urls: set[str] = set()
        self.in_ld_json = False
        self.ld_json = ""

    def accept(self, candidate: str):
        url = urljoin(self.base, candidate)
        if public_link(url):
            self.urls.add(url)

    def handle_starttag(self, tag: str, attrs):
        a = dict(attrs)
        if tag == "meta" and str(a.get("property") or a.get("name") or "").lower() in META_NAMES:
            self.accept(str(a.get("content") or ""))
        if tag in {"video", "source"} and a.get("src"):
            # HTML video/source elements are candidates; not evidence of rights.
            self.accept(str(a["src"]))
        if tag == "script" and a.get("type", "").lower() == "application/ld+json":
            self.in_ld_json = True
            self.ld_json = ""

    def handle_data(self, data):
        if self.in_ld_json and len(self.ld_json) < 150_000:
            self.ld_json += data

    def handle_endtag(self, tag):
        if tag == "script" and self.in_ld_json:
            self.in_ld_json = False
            try:
                parsed = json.loads(self.ld_json)
            except ValueError:
                return
            self._walk_ld(parsed)

    def _walk_ld(self, value):
        if isinstance(value, list):
            for x in value[:30]:
                self._walk_ld(x)
        elif isinstance(value, dict):
            types = value.get("@type") or []
            if isinstance(types, str):
                types = [types]
            if "VideoObject" in types:
                for key in ("contentUrl", "embedUrl"):
                    url = value.get(key)
                    if isinstance(url, str):
                        self.accept(url)
            for key in ("@graph", "mainEntity", "video", "subjectOf"):
                if key in value:
                    self._walk_ld(value[key])


def discover_html(html: str, url: str) -> list[str]:
    parser = VideoReferences(url)
    parser.feed(html)
    # Stable ordering; YouTube and editorial embeds remain review-only.
    return sorted(parser.urls)[:10]


def collect(url: str) -> list[str]:
    if not public_link(url):
        return []
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; RDI editorial video review/1.0)",
                                "Accept": "text/html"})
    try:
        with urlopen(req, timeout=7) as response:
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type:
                return []
            if not public_link(response.url):
                return []
            html = response.read(MAX_PAGE_BYTES).decode("utf-8", "replace")
        return discover_html(html, response.url)
    except Exception:
        return []


def prepare(preview: dict, max_items: int = MAX_ITEMS) -> dict:
    stories = preview.get("candidates", [])
    rows = []
    for s in stories[:max_items]:
        url = str(s.get("source_url") or "")
        if not public_link(url):
            continue
        clips = collect(url)
        if not clips:
            continue
        rows.append({
            "article_id": s.get("id"), "article_title": s.get("title_original"),
            "article_url": url, "publisher": s.get("source_name"),
            "video_candidates": [{
                "url": clip, "rights_reviewed": False,
                "youtube_live_authorized": False,
                "broadcast_status": "NON AUTORIZZATO: verificare il permesso prima dell'uso"
            } for clip in clips],
        })
    return {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "research_only_no_broadcast_rights",
        "discovered": len(rows),
        "items": rows,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--preview", default="/tmp/rdi-tg-sera/source-preview.json")
    p.add_argument("--output", default="/tmp/rdi-tg-sera/publisher-video-candidates.json")
    args = p.parse_args()
    source = Path(args.preview)
    if not source.exists():
        raise SystemExit("Missing vetted TG source preview")
    result = prepare(json.loads(source.read_text(encoding="utf-8")))
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Unlicensed publisher video candidates identified:", result["discovered"])
    print("NOT approved for live streaming; only explicit grants may enter TG.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
