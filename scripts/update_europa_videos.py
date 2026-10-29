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
import shutil
import subprocess
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
        "language_hint": "it" if "/it/" in urlparse(link).path else "und",
        "italian_audio_in_player_verified": False,
        "italian_audio_download_option_verified": False,
        "audio_evidence": "",
        "audio_italiano_verificato": False,
        "diritti_verificati": False,
        "status": "DA_VERIFICARE",
    }


class LenientRSS(HTMLParser):
    """Fallback per feed che includono HTML non escapato nelle descrizioni."""

    def __init__(self, source: dict):
        super().__init__(convert_charrefs=True)
        self.source = source
        self.current = None
        self.field = None
        self.items = []

    def handle_starttag(self, tag, attrs):
        if tag == "item":
            self.current = {}
            self.field = None
        elif self.current is not None and tag in {"title", "link", "pubdate"}:
            self.field = tag
            self.current.setdefault(tag, "")

    def handle_data(self, data):
        if self.current is not None and self.field is not None:
            self.current[self.field] += data

    def handle_endtag(self, tag):
        if tag == "item" and self.current is not None:
            x = self.current
            item = candidate(self.source, x.get("title", ""), x.get("link", ""), iso_date(x.get("pubdate", "")))
            if item:
                self.items.append(item)
            self.current = None
            self.field = None
        elif tag == self.field:
            self.field = None


def parse_rss(blob: bytes, source: dict) -> list[dict]:
    try:
        root = ET.fromstring(blob)
    except ET.ParseError:
        parser = LenientRSS(source)
        parser.feed(blob.decode("utf-8", errors="replace"))
        return parser.items
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
        publisher = self.source
        # Il portale AV della Commissione include anche servizi ufficiali EP.
        # Solo prefissi espliciti; questo è un indizio editoriale, NON prova di lingua/licenza.
        if re.match(r"^(EP News|EP Press conference|European Parliament)\b", title, re.I):
            publisher = dict(self.source, id="parlamento_europeo", name="Parlamento europeo (tramite AV UE)")
        obj = candidate(publisher, title, self.href, published)
        if obj:
            self.items.append(obj)
        self.href = None
        self.words = []


def parse_listing(blob: bytes, source: dict) -> list[dict]:
    parser = CommissionListing(source)
    parser.feed(blob.decode("utf-8", errors="replace"))
    return parser.items


class PlainMetadata(HTMLParser):
    """Legge soltanto le etichette visibili nella scheda del portale AV UE."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text = []
        self.omit = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self.omit += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self.omit:
            self.omit -= 1

    def handle_data(self, data):
        if not self.omit and data.strip():
            self.text.append(clean(data))


def declared_language_versions(blob: bytes) -> tuple[str, bool]:
    """Italiano deve comparire nella riga 'Languages', non nel titolo/descrizione.

    Non restituisce una convalida della voce: 'Italiano' può indicare
    la disponibilità di una traccia da scegliere o scaricare.
    """
    parser = PlainMetadata()
    parser.feed(blob.decode("utf-8", errors="replace"))
    visible = " ".join(parser.text)
    m = re.search(
        r"\bLanguages\s+(?=(?:Original|Italiano|Italian|English|Deutsch|fran[cç]ais|Nederlands|español|suomi|Portugu[eê]s|polski|română)\b)(.{1,180}?)(?=\s+(?:See more|Category|Tags|Location|Personalities|Institution|Views|Related media)\b|$)",
        visible, re.I
    )
    if not m:
        return "", False
    declared = m.group(1).strip()
    # 'Italy' in una descrizione, 'IT' nel percorso URL, o 'Original' non sono prove.
    available = bool(re.search(r"\b(?:Italiano|Italian|Italien)\b", declared, re.I))
    return declared[:160], available


def fetch_rendered_metadata(url: str) -> bytes | None:
    """Fallback: usa Chrome headless per il portale Angular (solo siti UE autorizzati).

    Non riproduce o scarica i media; legge esclusivamente la scheda pubblica.
    Il runner GitHub include Chrome, mentre installazioni minime possono non
    averlo: in quel caso il risultato resta non confermato.
    """
    if not page_allowed(url) or urlparse(url).hostname != "audiovisual.ec.europa.eu":
        return None
    browser = next(
        (shutil.which(name) for name in ("google-chrome", "chromium", "chromium-browser") if shutil.which(name)),
        None,
    )
    if not browser:
        return None
    cmd = [
        browser, "--headless", "--disable-gpu", "--disable-dev-shm-usage",
        "--no-sandbox", "--no-first-run", "--no-default-browser-check",
        "--disable-extensions", "--virtual-time-budget=9000", "--dump-dom", url,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=26, check=False)
        if result.returncode == 0 and b"Languages" in result.stdout and len(result.stdout) <= 4_000_000:
            return result.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def annotate_languages(items: list[dict], now: dt.datetime, limit: int = 8) -> int:
    """Controllo graduale delle versioni linguistiche; massimo 8 HTTP per run."""
    count = 0
    candidates = sorted(items, key=lambda x: x.get("published_at") or "", reverse=True)
    for item in candidates:
        if count >= limit:
            break
        if urlparse(item.get("source_url", "")).hostname != "audiovisual.ec.europa.eu":
            continue
        checked = item.get("language_checked_at", "")
        if checked and item.get("language_probe_version") == 3:
            try:
                stamp = dt.datetime.fromisoformat(checked.replace("Z", "+00:00"))
                ttl = dt.timedelta(days=14 if item.get("language_status") in
                                   ("VERSIONE_IT_INDICATA", "ITALIANO_NON_LISTATO")
                                   else 1)
                if stamp.tzinfo and now - stamp < ttl:
                    continue
            except ValueError:
                pass
        count += 1
        try:
            language_list, has_it = declared_language_versions(fetch(item["source_url"]))
            if not language_list:
                rendered = fetch_rendered_metadata(item["source_url"])
                if rendered:
                    language_list, has_it = declared_language_versions(rendered)
            item["languages_declared"] = language_list
            item["italian_version_available"] = has_it
            item["italian_audio_candidate"] = has_it
            item["language_status"] = ("VERSIONE_IT_INDICATA" if has_it else "ITALIANO_NON_LISTATO" if language_list else "LINGUA_NON_LEGGIBILE")
        except Exception as exc:
            item["language_status"] = "METADATI_NON_DISPONIBILI"
            item["italian_version_available"] = False
            item["language_error"] = str(exc)[:110]
        item["language_checked_at"] = now.isoformat()
        item["language_probe_version"] = 3
    return count


def official_italian_examples(now: dt.datetime) -> list[dict]:
    """Esempio recente con lingua IT esplicitamente indicata nella scheda.

    Scheda verificata il 29/10/2026; non equivale ad aver ascoltato
    la traccia, verificato la licenza o scaricato un MP4.
    """
    source = SOURCES[1]
    example = candidate(
        source,
        "Informal meeting of ministers responsible for Cohesion Policy – press conference",
        "https://audiovisual.ec.europa.eu/en/media/video/I-294336",
        "2026-09-15",
    )
    example.update({
        "languages_declared": "Original English Italiano",
        "italian_version_available": True,
        "language_status": "VERSIONE_IT_INDICATA",
        "language_checked_at": "2026-10-29T12:00:00+00:00",
        "provenance": "Scheda ufficiale AV UE, 29/10/2026; audio selezionabile verificato nel player e nel menu Download, diritti da verificare",
        "italian_audio_candidate": True,
        "italian_audio_in_player_verified": True,
        "italian_audio_download_option_verified": True,
        "audio_evidence": "Browser UI: LANGUAGE > Italiano; Downloads > Audio > Italiano (IT), 29/10/2026",
    })
    return [example]


def eligible_video(item: dict, now: dt.datetime) -> bool:
    if not isinstance(item, dict):
        return False
    checks = (
        item.get("approved") is True,
        item.get("audio_italiano_verificato") is True,
        item.get("diritti_verificati") is True,
        item.get("musica_e_terzi_verificati") is True,
        item.get("video_completo") is True,
        item.get("audio_track_language") == "it",
        item.get("audio_sync_verified") is True,
        item.get("source_id") in {s["id"] for s in SOURCES},
        isinstance(item.get("title"), str) and len(item["title"].strip()) >= 7,
        isinstance(item.get("reviewed_by"), str) and bool(item["reviewed_by"].strip()),
        isinstance(item.get("reviewed_at"), str) and bool(item["reviewed_at"].strip()),
        isinstance(item.get("credit"), str) and bool(item["credit"].strip()),
        isinstance(item.get("media_url"), str) and item["media_url"].startswith("https://"),
        isinstance(item.get("source_url"), str) and page_allowed(item["source_url"]),
        isinstance(item.get("rights_url"), str) and page_allowed(item["rights_url"]),
        isinstance(item.get("duration_seconds"), int) and 15 <= item["duration_seconds"] <= 1800,
    )
    if not all(checks):
        return False
    # Mai prendere per default l'audio originale. La modalità italiana
    # deve essere esplicita: traccia interna verificata o file italiano separato.
    mode = item.get("audio_mode")
    if mode == "separate_it":
        if not (isinstance(item.get("audio_url"), str)
                and item["audio_url"].startswith("https://")
                and item.get("original_audio_muted") is True
                and isinstance(item.get("audio_offset_ms"), int)
                and -5000 <= item["audio_offset_ms"] <= 5000):
            return False
    elif mode == "embedded_it":
        if not (isinstance(item.get("audio_stream_index"), int)
                and 0 <= item["audio_stream_index"] <= 15):
            return False
    else:
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
    local_now = now.astimezone(ROME)
    today = local_now.date()
    if local_now.time() >= dt.time(18, 0):
        today += dt.timedelta(days=1)
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
    # Esempi metadati certi: non approvati per la diretta e riconfermati alla scadenza.
    for item in official_italian_examples(now):
        old = retained.get(item["id"], {})
        # Il controllo del player del 29/10 ha verificato un audio italiano
        # selezionabile e un'opzione di download audio IT, NON i diritti.
        # Registrarlo anche nel catalogo già creato nei run precedenti.
        if old:
            old.update({key: item[key] for key in (
                "italian_version_available", "italian_audio_candidate",
                "italian_audio_in_player_verified",
                "italian_audio_download_option_verified", "audio_evidence",
                "provenance")})
            retained[item["id"]] = old
        else:
            retained[item["id"]] = item
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
                old = retained.get(item["id"], {})
                # La nuova acquisizione aggiorna titolo/data ma NON cancella
                # la verifica delle lingue effettuata nelle esecuzioni precedenti.
                for key in ("languages_declared", "italian_version_available", "italian_audio_candidate", "italian_audio_in_player_verified", "italian_audio_download_option_verified", "audio_evidence", "language_status", "language_checked_at", "language_probe_version", "language_error", "provenance"):
                    if key in old:
                        item[key] = old[key]
                retained[item["id"]] = item
            diagnostics.append({"source": source["id"], "status": "ok", "found": len(found)})
        except Exception as exc:
            diagnostics.append({"source": source["id"], "status": "error", "reason": str(exc)[:160]})
    items = sorted(retained.values(), key=lambda x: (x.get("published_at") or "", x.get("id") or ""), reverse=True)[:150]
    language_checks = annotate_languages(items, now)
    italian_versions = [x for x in items if x.get("italian_version_available") is True]
    catalog = {
        "schema_version": 1,
        "updated_at": now.isoformat(),
        "success_sources": success_count,
        "sources": diagnostics,
        "items": items,
        "italian_versions": italian_versions,
        "language_checks_this_run": language_checks,
        "disclaimer": "Candidate da fonti ufficiali: il titolo o la lingua del feed NON verifica audio italiano o licenze.",
    }
    if previous.get("items") == catalog["items"] and previous.get("sources") == catalog["sources"] and previous.get("italian_versions") == catalog["italian_versions"]:
        catalog["updated_at"] = previous.get("updated_at") or catalog["updated_at"]
    # Mai sovrascrivere le approvazioni umane dal processo automatico.
    approvals = read_json(APPROVALS, {"schema_version": 1, "items": []})
    if not isinstance(approvals.get("items"), list):
        raise ValueError("data/europa-video-approved.json: items non è un elenco")
    schedule = build_schedule(approvals["items"], now)
    old_schedule = read_json(PLAYOUT, {})
    if old_schedule.get("ready_videos") == schedule["ready_videos"] and old_schedule.get("daily_schedule") == schedule["daily_schedule"]:
        schedule["generated_at"] = old_schedule.get("generated_at") or schedule["generated_at"]
    write_json(CATALOG, catalog)
    write_json(PLAYOUT, schedule)
    print(json.dumps({"sources": diagnostics, "candidates": len(items), "italian_versions_listed": len(italian_versions), "metadata_checks": language_checks, "approved": len(schedule["ready_videos"]), "live_enabled": False}, ensure_ascii=False))
    if not success_count:
        print("ATTENZIONE: fonti non raggiungibili; conservati i candidati precedenti.")


if __name__ == "__main__":
    main()
