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
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import formatdate

NEWS_URL = os.getenv(
    "RDI_NEWS_URL",
    "https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/main/news.json",
)
STATE_FILE = pathlib.Path(os.getenv("RDI_FB_STATE_FILE", "/var/lib/rdi-facebook/state.json"))
SHARE_QUEUE_FILE = pathlib.Path(os.getenv("RDI_FB_SHARE_QUEUE_FILE", "/var/lib/rdi-facebook/share-queue.json"))
MAX_POSTS = max(1, min(int(os.getenv("RDI_FB_MAX_POSTS", "3")), 10))
DRY_RUN = os.getenv("RDI_FB_DRY_RUN", "true").lower() not in {"0", "false", "no"}
GRAPH_VERSION = os.getenv("FB_GRAPH_VERSION", "v27.0")
YOUTUBE_LIVE_URL = os.getenv("RDI_YOUTUBE_LIVE_URL", "https://www.youtube.com/watch?v=_qt-NjBcbtA")
RDI_APP_URL = os.getenv("RDI_APP_URL", "https://radioromanii.duckdns.org/index.html")
RDI_PAGE_URL = os.getenv("RDI_PAGE_URL", "https://www.facebook.com/profile.php?id=61595529061512")
DAILY_LIMIT = max(1, min(int(os.getenv("RDI_FB_MAX_DAILY_POSTS", "12")), 50))
LIVE_PROMO_INTERVAL_HOURS = max(1, min(int(os.getenv("RDI_FB_LIVE_PROMO_INTERVAL_HOURS", "6")), 24))
NEWS_MIN_INTERVAL_MINUTES = max(30, min(int(os.getenv("RDI_FB_NEWS_MIN_INTERVAL_MINUTES", "90")), 360))
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


def save_share_queue(items: list[dict]) -> None:
    """Prepara contenuti per la condivisione manuale nei soli gruppi autorizzati."""
    SHARE_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "notice": "Condividere solo nei gruppi autorizzati e rispettando le regole del gruppo.",
        "items": [
            {"title": item.get("title"), "url": item.get("url"), "message": message_for(item)}
            for item in items
        ],
    }
    tmp = SHARE_QUEUE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, SHARE_QUEUE_FILE)


def item_key(item: dict) -> str:
    raw = str(item.get("url") or item.get("title") or "").strip()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def growth_cta(item: dict) -> str:
    """CTA variabile per crescita organica, senza spam o promesse artificiose."""
    variants = [
        f"🔔 Segui RDI per ricevere le notizie della diaspora e dell'Italia: {RDI_PAGE_URL}",
        f"📌 Ti interessa questo tema? Segui la pagina RDI e condividi il post con chi vive in Italia: {RDI_PAGE_URL}",
        f"🌍 RDI informa ogni giorno la comunità romena in Italia. Segui la pagina: {RDI_PAGE_URL}",
    ]
    return variants[int(item_key(item), 16) % len(variants)]


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
    lines.append(f"🎙️ Ascolta RDI live su YouTube: {YOUTUBE_LIVE_URL}")
    lines.append(f"📻 Apri l’app RDI: {RDI_APP_URL}")
    lines.append(growth_cta(item))
    return "\n\n".join(lines)


def publish(item: dict, message: str | None = None) -> str:
    if DRY_RUN:
        return "dry-run"
    if not PAGE_ID or not PAGE_TOKEN:
        raise RuntimeError("RDI_FB_PAGE_ID e RDI_FB_PAGE_TOKEN sono obbligatori per pubblicare")
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PAGE_ID}/feed"
    body = urllib.parse.urlencode({
        "message": message if message is not None else message_for(item),
        "link": str(item["url"]),
        "published": "true",
        "access_token": PAGE_TOKEN,
    }).encode("utf-8")
    request = urllib.request.Request(url, data=body, method="POST")
    request.add_header("User-Agent", "RDI-Facebook-Publisher/1.0")
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            details = json.loads(raw).get("error", {}).get("message", raw)
        except json.JSONDecodeError:
            details = raw
        raise RuntimeError(f"Facebook API HTTP {error.code}: {details}") from error
    if not payload.get("id"):
        raise RuntimeError(f"Facebook non ha restituito l'id del post: {payload}")
    return str(payload["id"])


def news_score(item: dict) -> tuple[int, str]:
    category = str(item.get("category") or "").lower()
    score = 0
    if "diaspora" in category:
        score += 40
    elif "românia" in category or "romania" in category:
        score += 30
    elif "italia" in category:
        score += 25
    elif "lavoro" in category or "comunit" in category:
        score += 20
    if item.get("summary"):
        score += 5
    source_tier = str(item.get("source_tier") or "").lower()
    if source_tier == "community":
        score -= 3
    published = str(item.get("published") or "")
    return score, published


def live_promo_message() -> str:
    return "\n\n".join([
        "🔴 RDI È IN DIRETTA 24 ORE SU 24",
        "Ascolta Radio Românii din Italia in qualsiasi momento.",
        f"🎙️ Ascolta il live su YouTube: {YOUTUBE_LIVE_URL}",
        f"📻 Apri l’app RDI: {RDI_APP_URL}",
        f"🔔 Segui la pagina RDI per non perdere i prossimi aggiornamenti: {RDI_PAGE_URL}",
        "#RadioRomaniiDinItalia #RDI #Live",
    ])

def main() -> None:
    feed = read_json(NEWS_URL)
    items = feed.get("items") if isinstance(feed, dict) else []
    if not isinstance(items, list):
        raise RuntimeError("news.json non contiene una lista items")
    state = load_state()
    published = state.setdefault("published", {})
    now = datetime.now(timezone.utc)
    last_live = state.get("last_live_promo_at")
    live_due = True
    if last_live:
        try:
            live_due = (now - datetime.fromisoformat(str(last_live))).total_seconds() >= LIVE_PROMO_INTERVAL_HOURS * 3600
        except ValueError:
            live_due = True
    if live_due:
        live_item = {
            "title": "RDI è in diretta 24 ore su 24",
            "url": YOUTUBE_LIVE_URL,
            "source": "RDI",
            "summary": "Radio Românii din Italia trasmette in diretta 24 ore su 24.",
        }
        promo_result = publish(live_item, live_promo_message())
        state["last_live_promo_at"] = now.isoformat()
        print(f"{'BOZZA' if DRY_RUN else 'PUBBLICATO'}: promemoria live RDI 24/7 ({promo_result})")
    candidates = []
    for item in items:
        if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
            continue
        key = item_key(item)
        if key not in published:
            candidates.append((key, item))
    candidates.sort(key=lambda pair: news_score(pair[1]), reverse=True)
    last_news_times = [
        str(value.get("published_at", ""))
        for value in published.values()
        if isinstance(value, dict) and value.get("published_at")
    ]
    news_due = True
    if last_news_times:
        try:
            last_news = max(datetime.fromisoformat(value) for value in last_news_times)
            news_due = (now - last_news).total_seconds() >= NEWS_MIN_INTERVAL_MINUTES * 60
        except ValueError:
            news_due = True
    today = now.date().isoformat()
    posted_today = sum(
        1 for value in published.values()
        if isinstance(value, dict) and str(value.get("published_at", "")).startswith(today)
    )
    remaining_today = max(0, DAILY_LIMIT - posted_today)
    selected = candidates[:min(MAX_POSTS, remaining_today)] if news_due else []
    save_share_queue([item for _, item in selected])
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
    print(f"RDI Facebook: {len(results)} elementi gestiti; modalità={'dry-run' if DRY_RUN else 'pubblicazione'}; pubblicati oggi={posted_today + len(results)}/{DAILY_LIMIT}; prossimo intervallo notizie={NEWS_MIN_INTERVAL_MINUTES} min")
    print(f"Coda condivisione gruppi: {len(selected)} contenuti pronti per approvazione manuale")
    for line in results:
        print(line)


if __name__ == "__main__":
    main()
