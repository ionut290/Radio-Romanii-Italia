#!/usr/bin/env python3
"""Hourly source-grounded diaspora briefs, without external AI services."""
import datetime as dt
import email.utils
import hashlib
import html
from html.parser import HTMLParser
import json
import re
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from zoneinfo import ZoneInfo

NOW = dt.datetime.now(ZoneInfo("Europe/Rome"))
ARCHIVE = Path("editorial.json")
data = json.loads(ARCHIVE.read_text(encoding="utf-8")) if ARCHIVE.exists() else {"items": []}
items = data.get("items", [])
if not isinstance(items, list):
    raise SystemExit("Invalid editorial.json: items must be a list")
# Retain only articles published within the preceding 48 hours.
# Missing or invalid dates are discarded rather than retained indefinitely.
def is_recent(article):
    try:
        published = dt.datetime.fromisoformat(str(article.get("published", "")).replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=ZoneInfo("Europe/Rome"))
        return NOW - dt.timedelta(hours=48) <= published.astimezone(NOW.tzinfo) <= NOW
    except (ValueError, TypeError, OverflowError):
        return False

original_count = len(items)
items = [article for article in items if is_recent(article)]
expired_count = original_count - len(items)
known_urls = {str(x.get("url", "")).rstrip("/") for x in items}
known_titles = {re.sub(r"\W+", " ", str(x.get("title", "")).casefold()).strip() for x in items}
slot = NOW.strftime("%Y-%m-%d-%H")
# Prefer previously researched, source-attributed editorial reporting when available.
# The supplement is maintained separately from the RSS import so facts are not invented.
DETAILS = Path("data/news-summaries.json")
try:
    researched = json.loads(DETAILS.read_text(encoding="utf-8")).get("items", {}) if DETAILS.exists() else {}
    if not isinstance(researched, dict):
        researched = {}
except (OSError, ValueError, TypeError) as exc:
    print(f"Extended reporting unavailable: {exc}")
    researched = {}

def source_grounded_body(url, summary):
    """Use longer original reporting only where a researched source-backed draft exists."""
    detail = researched.get(url, {})
    if not isinstance(detail, dict):
        detail = {}
    body = str(detail.get("body") or "").strip()
    source_urls = detail.get("source_urls") or []
    if (len(body) >= 600 and isinstance(source_urls, list)
            and any(isinstance(link, str) and link.startswith("https://") for link in source_urls)):
        return body, True
    return summary, False

# Enrich existing briefs, too; do not overwrite already longer editorial texts.
backfilled = 0
for existing in items:
    url = str(existing.get("url") or "")
    draft, researched_flag = source_grounded_body(url, str(existing.get("summary") or ""))
    if researched_flag and len(draft) > len(str(existing.get("body") or "")):
        existing["body"] = draft
        existing["extended_summary"] = True
        backfilled += 1

feeds = [
    ("Google News · diaspora Italia", "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": "români Italia diaspora when:4d", "hl": "ro", "gl": "RO", "ceid": "RO:ro"}), "Diaspora"),
    ("Google News · români Italia", "https://news.google.com/rss/search?" + urllib.parse.urlencode({"q": "\"român\" Italia when:4d", "hl": "ro", "gl": "RO", "ceid": "RO:ro"}), "Diaspora"),

]
keywords = ("român", "romani", "români", "romanca", "româncă", "române", "romania", "diaspora", "cetățean român")
italy_terms = ("italia", "italie", "italian", "roma ", "milano", "torino", "bologna", "napoli", "firenze", "venezia", "palermo", "genova", "perugia", "cesena", "re modena")
class ArticleImageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image = ""
    def handle_starttag(self, tag, attrs):
        if tag.lower() != "meta" or self.image:
            return
        a = dict(attrs)
        if a.get("property", "").lower() in ("og:image", "og:image:url") or a.get("name", "").lower() == "twitter:image":
            candidate = html.unescape(a.get("content", ""))
            if candidate.startswith("https://"):
                self.image = candidate

def article_image(url):
    # Only publisher-supplied public preview images; do not scrape article galleries.
    if not url.startswith("https://") or "news.google.com/" in url:
        return ""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; RadioRomaniiItalia/1.0)"})
        with urllib.request.urlopen(req, timeout=7) as response:
            if "text/html" not in response.headers.get("Content-Type", ""):
                return ""
            page = response.read(180_000).decode("utf-8", errors="ignore")
        parser = ArticleImageParser()
        parser.feed(page)
        return parser.image
    except Exception as exc:
        print(f"Preview image unavailable: {url[:90]} ({exc})")
        return ""

new_items = []
feed_successes = 0
for publisher, feed, category in feeds:
    try:
        request = urllib.request.Request(feed, headers={"User-Agent": "RadioRomaniiItalia/1.0 (editorial RSS)"})
        with urllib.request.urlopen(request, timeout=25) as response:
            root = ET.fromstring(response.read(2_000_000))
        feed_successes += 1
        for entry in root.findall("./channel/item")[:40]:
            title = html.unescape((entry.findtext("title") or "").strip())
            url = (entry.findtext("link") or "").strip()
            description = entry.findtext("description") or ""
            summary = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", description)).split())
            if not title or not url.startswith("https://") or not summary:
                continue
            normalized_title = re.sub(r"\W+", " ", title.casefold()).strip()
            if url.rstrip("/") in known_urls or normalized_title in known_titles:
                continue
            try:
                published = email.utils.parsedate_to_datetime(entry.findtext("pubDate") or "").astimezone(dt.timezone.utc)
            except (ValueError, TypeError, OverflowError):
                continue
            age = dt.datetime.now(dt.timezone.utc) - published
            if not (dt.timedelta(0) <= age <= dt.timedelta(hours=48)):
                continue
            context = (title + " " + summary).lower()
            if not (any(k in context for k in keywords) and any(k in context for k in italy_terms)):
                continue
            image = ""
            # Avoid publisher photographs and previews: only original RDI artwork may be attached.
            # RSS briefs intentionally have no image unless original RDI artwork is created separately.
            # Only source-grounded short news briefs: no invented facts, quotes or details.
            clean_summary = summary  # Preserve the complete source-provided brief; never expand with invented facts.
            if len(clean_summary) < 45:
                continue
            body, is_extended = source_grounded_body(url, clean_summary)
            # No repetition or fabricated filler to meet a word count.
            # Short source feeds remain transparently short until independently researched.
            new_items.append({
                "id": "rss-" + hashlib.sha256(url.encode()).hexdigest()[:20],
                "editorial": True,
                "category": category,
                "title": title[:240],
                "image": image,
                "summary": clean_summary,
                "body": body,
                "extended_summary": is_extended,
                "published": published.isoformat(),
                "source": (entry.findtext("source") or publisher),
                "url": url,
                "byline": "Selecție știri · Radio Românii din Italia",
                "source_id": hashlib.sha256(url.encode()).hexdigest()[:16],
                "slot": slot,
            })
            known_urls.add(url.rstrip("/"))
            known_titles.add(normalized_title)
            if len(new_items) >= 3:
                break
    except Exception as exc:
        print(f"RSS unavailable ({publisher}): {exc}")
    if len(new_items) >= 3:
        break
# If both RSS sources fail, make the workflow fail visibly rather than reporting success.
if feed_successes == 0:
    raise SystemExit("All editorial RSS feeds failed; retry at the next scheduled run")
# Do not attach external publisher preview images to existing entries.
if new_items or expired_count or backfilled:
    data["items"] = new_items + items
    data["updated_at"] = NOW.isoformat()
    ARCHIVE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"New verified-source RSS briefs: {len(new_items)}; expired articles removed: {expired_count}; archived articles: {len(items)}")
