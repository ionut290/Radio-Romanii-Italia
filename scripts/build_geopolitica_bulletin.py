#!/usr/bin/env python3
"""Prepare an attributed, editorially screened hourly RDI radio bulletin.

Only previously reviewed stories are eligible. Automated external RSS headlines
are NOT suitable for unattended broadcast, regardless of translation status.
This script never transmits, changes AzuraCast or generates audio by itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
ROOT = Path(__file__).resolve().parent.parent
CURATED = ROOT / "data/war-zone-news.json"
EXTRA = ROOT / "data/geopolitica-radio-verified.json"
MAX_STORIES = 5
MAX_AGE_HOURS = 35  # Publication dates from the curated feed have day precision.

OPENING = {
    "ro": "Radio Românii din Italia. Ascultați RDI Geopolitica, sinteza evenimentelor internaționale.",
    "it": "Radio Românii din Italia presenta Geopolitica. Le principali notizie dal mondo, Paese per Paese.",
}
CAUTION = {
    "ro": "Relatările sunt atribuite publicațiilor și instituțiilor citate. Informațiile aflate în evoluție pot fi actualizate sau corectate.",
    "it": "Per leggere gli articoli completi, verificare le fonti e trovare gli aggiornamenti, visitate la sezione Geopolitica sul sito di Radio Românii din Italia. Le notizie in evoluzione possono essere aggiornate.",
}
OUTRO = {
    "ro": "Mai multe detalii, surse și context găsiți în secțiunea Geopolitică, pe site-ul Radio Românii din Italia. Rămâneți cu noi, muzica revine imediat.",
    "it": "Questo era RDI Geopolitica. Continuate a seguirci sul sito della radio. Tra poco torna la musica.",
}
TRANSITIONS = {
    "ro": ("În continuare.", "Tot în actualitatea internațională.", "Într-un alt subiect.", "În final."),
    "it": ("Proseguiamo.", "Ancora dall'attualità internazionale.", "In un altro aggiornamento.", "Infine."),
}


def read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def safe_source(value: object) -> bool:
    return isinstance(value, str) and value.startswith("https://") and len(value) < 2048


def display_date(date: dt.date, language: str) -> str:
    months = {
        "ro": ("ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"),
        "it": ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"),
    }
    return f"{date.day} {months[language][date.month-1]} {date.year}"


def clean_spoken(value: object, limit: int = 650) -> str:
    text = str(value or "").strip()
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text[:limit].strip(" ,.;:")


def available_items(now: dt.datetime, lang: str, curated: dict, extras: dict) -> list[dict]:
    result = []
    seen_urls = set()
    # war-zone-news.json is the existing editorially verified feed, not the raw attack leads.
    incoming = [(x, True) for x in curated.get("items", []) if isinstance(x, dict)]
    # Additional geopolitical news must be explicitly approved for radio by the redaction.
    incoming += [(x, False) for x in extras.get("items", []) if isinstance(x, dict)]
    for item, is_curated in incoming:
        if not is_curated and not (item.get("editorial_verified") is True and item.get("approved_for_radio") is True):
            continue
        title = clean_spoken(item.get("title_" + lang), 240)
        summary = clean_spoken(item.get("summary_" + lang), 700)
        source = clean_spoken(item.get("source_name"), 90)
        url = item.get("source_url")
        day = item.get("published_date")
        if not (title and len(summary) >= 40 and source and safe_source(url)):
            continue
        try:
            publication = dt.date.fromisoformat(str(day))
        except (TypeError, ValueError):
            continue
        if publication > now.date():
            continue
        # Day-precision dates are approximated to midday local, not interpreted as event times.
        published_at = dt.datetime.combine(publication, dt.time(12, 0), tzinfo=ROME)
        age_hours = (now - published_at).total_seconds() / 3600
        if age_hours > MAX_AGE_HOURS or age_hours < -12:
            continue
        if url in seen_urls:
            continue
        seen_urls.add(url)
        result.append({
            "title": title, "summary": summary, "source": source, "url": url,
            "date": publication, "region": str(item.get("region") or "").strip(),
            "id": str(item.get("id") or url), "curated": is_curated
        })
    result.sort(key=lambda item: (item["date"], item["curated"]), reverse=True)
    # Promote geographic diversity without inventing priorities or ranking political actors.
    selected = []
    covered = set()
    for item in result:
        label = item["region"].casefold()
        if label not in covered:
            selected.append(item)
            covered.add(label)
        if len(selected) == MAX_STORIES:
            return selected
    for item in result:
        if item not in selected:
            selected.append(item)
        if len(selected) == MAX_STORIES:
            break
    return selected



def country_name(item: dict, lang: str) -> str:
    """A geographical label, never a source's name or publisher."""
    raw = str(item.get("region") or "").strip()
    simplified = {
        "it": {
            "Ucraina": "Ucraina", "Sudan": "Sudan", "Cisiordania": "Cisgiordania",
            "Cisjordania": "Cisgiordania", "Gaza": "Striscia di Gaza",
            "România": "Romania", "Italia": "Italia",
        },
        "ro": {"Ucraina": "Ucraina", "Sudan": "Sudan", "Cisiordania": "Cisiordania"},
    }
    return clean_spoken(simplified.get(lang, {}).get(raw, raw or ("Mondo" if lang == "it" else "Lumea")), 70)


def broadcast_summary(text: str, lang: str, source: str) -> str:
    """Remove newspaper/publisher credits from the spoken text, not from metadata.

    Keep substantive caveats about unconfirmed reports and official claims.
    """
    text = clean_spoken(text, 700)
    if lang == "it":
        text = re.sub(r"^(?:Secondo|Stando a)\s+(?:Reuters(?:\s+e\s+AP)?|Associated Press|AP)\s*,?\s*",
                      "", text, flags=re.IGNORECASE)
        text = re.sub(r"^Reuters\s+(?:riferisce|segnala)\s+che\s+", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^Reuters\s+cita\s+(il sindaco[^:]{0,100}):\s*",
                      r"\1 ha riferito che ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bUn testimone Reuters\b", "Un testimone", text, flags=re.IGNORECASE)
        text = re.sub(r"\bReuters(?:\s+e\s+AP)?\s+(?:riferisce|riporta)\s+che\s+",
                      "", text, flags=re.IGNORECASE)
        text = re.sub(r"\bReuters\s+(?:dichiara|precisa)\s+che\s+non\s+ha\s+potuto\s+verificare\s+(?:indipendentemente|autonomamente)\s+",
                      "Non è stato possibile verificare indipendentemente ", text, flags=re.IGNORECASE)
        # A publisher name can appear inside an editorial summary; don't read it.
        for outlet in ("Reuters", "Associated Press", "Internazionale"):
            text = re.sub(r"\b" + re.escape(outlet) + r"\b", "", text, flags=re.IGNORECASE)
    elif lang == "ro":
        text = re.sub(r"\bReuters(?:\s+și\s+AP)?\b", "", text, flags=re.IGNORECASE)
    if source:
        # Never voice the stored outlet name. Retain it for the written article.
        text = text.replace(source, "")
    return re.sub(r"\s+", " ", text).strip(" ,.;:")


def build(now: dt.datetime, lang: str, curated: dict, extras: dict) -> dict | None:
    now = now.astimezone(ROME)
    stories = available_items(now, lang, curated, extras)
    if not stories:
        return None
    date_text = display_date(now.date(), lang)
    hour_text = f"{now.hour:02d}:{now.minute:02d}"
    intro = (f"Ediția de la ora {hour_text}, {date_text}."
             if lang == "ro" else f"Edizione delle {hour_text} del {date_text}.")
    segments = [{
        "kind": "intro",
        "text": "\n".join((OPENING[lang], intro, CAUTION[lang])),
    }]
    public_articles = []
    for index, item in enumerate(stories):
        label = country_name(item, lang)
        title = item["title"]
        summary = broadcast_summary(item["summary"], lang, item["source"])
        # Don't repeat "Ucraina: Ucraina: ...".
        title_spoken = re.sub(r"^" + re.escape(label) + r"\s*[:—-]\s*", "", title, flags=re.IGNORECASE)
        transition = "" if index == 0 else TRANSITIONS[lang][min(index - 1, len(TRANSITIONS[lang]) - 1)] + " "
        segment = {
            "kind": "story", "id": item["id"], "country": label,
            "title": title, "summary": summary,
            "text": transition + label + ". " + title_spoken.rstrip(".") + ". " + summary.rstrip(".") + ".",
        }
        segments.append(segment)
        public_articles.append({
            "id": item["id"], "country": label, "title": title,
            "summary": summary, "article_url": item["url"],
            "source_name": item["source"], "published_date": item["date"].isoformat(),
        })
    segments.append({"kind": "outro", "text": OUTRO[lang]})
    transcript = "\n\n".join(item["text"] for item in segments) + "\n"
    edition_id = now.strftime("%Y%m%d-%H%M")
    return {
        "language": lang, "generated_at": now.isoformat(),
        "edition_id": edition_id,
        "track_title": f"RDI-GEOPOLITICA-{lang.upper()}-{edition_id}",
        "story_count": len(stories),
        "sources": [{
            "id": x["id"], "url": x["url"], "source": x["source"],
            "published_date": x["date"].isoformat()
        } for x in stories],
        "articles": public_articles,
        "segments": segments,
        "text": transcript,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=("ro", "it"), default="it")
    parser.add_argument("--output", default="/tmp/rdi-geopolitica")
    args = parser.parse_args()
    now = dt.datetime.now(ROME)
    program = build(now, args.language, read_json(CURATED), read_json(EXTRA))
    if not program:
        print("Nessun bollettino: nessuna notizia abbastanza recente e revisionata.")
        return 2
    dest = Path(args.output)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "bulletin.txt").write_text(program["text"], encoding="utf-8")
    (dest / "manifest.json").write_text(json.dumps({k: v for k, v in program.items() if k != "text"}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Bollettino {args.language} preparato: {program['story_count']} notizie, {len(program['text'].split())} parole.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
