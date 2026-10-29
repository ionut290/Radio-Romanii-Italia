#!/usr/bin/env python3
"""RDI Europa: catalogo di POSSIBILI video istituzionali, mai playout automatico.

Solo fonti ufficiali; nessun titolo, lingua del sito o feed equivale a
verifica della traccia italiana o dei diritti del singolo file.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data/europa-video-candidates.json"
APPROVALS = ROOT / "data/europa-video-approved.json"
PLAYOUT = ROOT / "data/europa-video-playout.json"
ROME = ZoneInfo("Europe/Rome")
SOURCES = [
    {
        "id": "parlamento_europeo",
        "name": "Parlamento europeo",
        "type": "rss",
        "url": "https://www.europarl.europa.eu/rss/video/other-events/it.xml",
        "site": "https://multimedia.europarl.europa.eu/it",
    },
    {
        "id": "commissione_europea",
        "name": "Commissione europea",
        "type": "listing",
        "url": "https://audiovisual.ec.europa.eu/en/media/video",
        "site": "https://audiovisual.ec.europa.eu/en/media/video",
    },
]
ALLOWED_PAGES = ("europarl.europa.eu", "audiovisual.ec.europa.eu")
RE_VIDEO = re.compile(r"/(?:[a-z]{2}/)?media/video/I-\d+", re.I)
RE_DATE = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
RE_TIME = re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b")


def read_json(path: Path, fallback):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return fallback


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return
    path.write_text(text, encoding="utf-8")


def fetch(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "RadioRomaniiDinItalia/1.0 editorial-video-monitor", "Accept": "application/xml,text/xml,text/html,*/*"})
    with urlopen(req, timeout=18) as response:
        body = response.read(3_000_001)
        if len(body) > 3_000_000:
            raise ValueError("Risposta troppo grande")
        return body


def page_allowed(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and any(
        parsed.hostname == domain or (parsed.hostname or "").endswith("." + domain)
        for domain in ALLOWED_PAGES
    )


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", " ", text or ""))).strip()


def iso_date(value: str) -> str:
    if not value:
        return ""
    try:
        return email.utils.parsedate_to_datetime(value).astimezone(dt.timezone.utc).isoformat()
    except (ValueError, TypeError):
        pass
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
    except ValueError:
        return ""


def candidate(source: dict, title: str, url: str, published: str = ""):
    link = urljoin(source["url"], url)
    title = clean(title)[:220]
    if len(title) < 7 or not page_allowed(link):
        return None
    identifier = hashlib.sha256((source["id"] + "|" + link.rstrip("/")).encode()).hexdigest()[:18]
    return {
        "id": identifier,
        "source_id": source["id"],
        "source": source["name"],
        "title": title,
        "source_url": link,
        "published_at": published,
        "language_hint": "it" if source["type"] == "rss" else "und",
        "audio_italiano_verificato": False,
        "diritti_verificati": False,
        "status": "DA_VERIFICARE",
    }


def parse_rss(blob: bytes, source: dict) -> list[dict]:
    root = ET.fromstring(blob)
    items = []
    for item in root.findall(".//item"):
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        published = iso_date(item.findtext("pubDate") or "")
        obj = candidate(source, title, link, published)
        if obj:
            items.append(obj)
    atom = "{http://www.w3.org/2005/Atom}"
    for item in root.findall(".//" + atom + "entry"):
        link = next((a.get("href", "") for a in item.findall(atom + "link") if a.get("rel", "alternate") == "alternate"), "")
        obj = candidate(source, item.findtext(atom + "title") or "", link, iso_date(item.findtext(atom + "updated") or ""))
        if obj:
            items.append(obj)
    return items


class CommissionListing(HTMLParser):
    def __init__(self, source: dict):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.href = None
        self.words = []
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == "a" and self.href is None:
            href = dict(attrs).get("href", "")
            if RE_VIDEO.search(href):
                self.href = href
                self.words = []

    def handle_data(self, data):
        if self.href is not None:
            self.words.append(data)

    def handle_endtag(self, tag):
        if tag != "a" or self.href is None:
            return
        value = clean(" ".join(self.words))
        dates = RE_DATE.findall(value)
        published = ""
        if dates:
            try:
                published = dt.datetime.strptime(dates[0], "%d/%m/%Y").date().isoformat()
            except ValueError:
                pass
        title = RE_DATE.sub("", value)
        title = RE_TIME.sub("", title).strip(" ·-– ")
        obj = candidate(self.source, title, self.href, published)
        if obj:
            self.items.append(obj)
        self.href = None
        self.words = []


def parse_listing(blob: bytes, source: dict) -> list[dict]:
    parser = CommissionListing(source)
    parser.feed(blob.decode("utf-8", errors="replace"))
    return parser.items


def eligible_video(item: dict, now: dt.datetime) -> bool:
    if not isinstance(item, dict):
        return False
    checks = (
        item.get("approved") is True,
        item.get("audio_italiano_verificato") is True,
        item.get("diritti_verificati") is True,
        item.get("musica_e_terzi_verificati") is True,
        item.get("video_completo") is True,
        item.get("source_id") in {s["id"] for s in SOURCES},
        isinstance(item.get("title"), str) and len(item["title"].strip()) >= 7,
        isinstance(item.get("reviewed_by"), str) and bool(item["reviewed_by"].strip()),
        isinstance(item.get("reviewed_at"), str) and bool(item["reviewed_at"].strip()),
        isinstance(item.get("credit"), str) and bool(item["credit"].strip()),
        isinstance(item.get("media_url"), str) and item["media_url"].startswith("https://"),
        isinstance(item.get("source_url"), str) and page_allowed(item["source_url"]),
        isinstance(item.get("rights_url"), str) and page_allowed(item["rights_url"]),
        isinstance(item.get("duration_seconds"), int) and 15 <= item["duration_seconds"] <= 900,
    )
    if not all(checks):
        return False
    try:
        if dt.datetime.fromisoformat(item["reviewed_at"].replace("Z", "+00:00")).tzinfo is None:
            return False
        if item.get("expires_at"):
            expiry = dt.datetime.fromisoformat(item["expires_at"].replace("Z", "+00:00"))
            if expiry.tzinfo is None or expiry <= now:
                return False
    except (ValueError, TypeError):
        return False
    return True


def build_schedule(approved: list[dict], now: dt.datetime) -> dict:
    # Elenco solo per la futura regia. Non comanda AzuraCast né FFmpeg.
    valid = [x for x in approved if eligible_video(x, now)]
    valid.sort(key=lambda x: (x["source_id"], x["source_url"]))
    days = []
    today = now.astimezone(ROME).date()
    for offset in range(8):
        day = today + dt.timedelta(days=offset)
        pick = valid[(day.toordinal() - dt.date(2026, 1, 1).toordinal()) % len(valid)] if valid else None
        slot = dt.datetime.combine(day, dt.time(18, 0), ROME)
        days.append({
            "date": day.isoformat(),
            "starts_at": slot.isoformat(),
            "video_id": pick.get("id", "") if pick else "",
            "status": "PRONTO_PER_REGIA" if pick else "NESSUN_VIDEO_APPROVATO",
        })
    return {
        "schema_version": 1,
        "generated_at": now.isoformat(),
        "live_enabled": False,
        "playback_mode": "STAGING_ONLY",
        "timezone": "Europe/Rome",
        "daily_time": "18:00",
        "ready_videos": valid,
        "daily_schedule": days,
        "note": "Richiede regia AV con switch audio+video. Non usare come playlist live finché non collaudata.",
    }


def main():
    now = dt.datetime.now(dt.timezone.utc)
    previous = read_json(CATALOG, {})
    retained = {x["id"]: x for x in previous.get("items", []) if isinstance(x, dict) and x.get("id")}
    diagnostics = []
    success_count = 0
    for source in SOURCES:
        try:
            blob = fetch(source["url"])
            found = parse_rss(blob, source) if source["type"] == "rss" else parse_listing(blob, source)
            if not found:
                raise ValueError("nessun collegamento video rilevato: il formato della fonte potrebbe essere cambiato")
            success_count += 1
            for item in found:
                retained[item["id"]] = item
            diagnostics.append({"source": source["id"], "status": "ok", "found": len(found)})
        except Exception as exc:
            diagnostics.append({"source": source["id"], "status": "error", "reason": str(exc)[:160]})
    items = sorted(retained.values(), key=lambda x: (x.get("published_at") or "", x.get("id") or ""), reverse=True)[:150]
    catalog = {
        "schema_version": 1,
        "updated_at": now.isoformat(),
        "success_sources": success_count,
        "sources": diagnostics,
        "items": items,
        "disclaimer": "Candidate da fonti ufficiali: il titolo o la lingua del feed NON verifica audio italiano o licenze.",
    }
    # Mai sovrascrivere le approvazioni umane dal processo automatico.
    approvals = read_json(APPROVALS, {"schema_version": 1, "items": []})
    if not isinstance(approvals.get("items"), list):
        raise ValueError("data/europa-video-approved.json: items non è un elenco")
    write_json(CATALOG, catalog)
    write_json(PLAYOUT, build_schedule(approvals["items"], now))
    print(json.dumps({"sources": diagnostics, "candidates": len(items), "approved": len(build_schedule(approvals["items"], now)["ready_videos"]), "live_enabled": False}, ensure_ascii=False))
    if not success_count:
        print("ATTENZIONE: fonti non raggiungibili; conservati i candidati precedenti.")


if __name__ == "__main__":
    main()
