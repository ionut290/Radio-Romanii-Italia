#!/usr/bin/env python3
"""RDI TG delle 18: editorial preparation, never autonomous publication.

Cutoff: 16:00 Europe/Rome. Selects source-backed articles and asks the model
for attributed Italian television narration, context and next developments.
Without usable sources or OPENAI_API_KEY the workflow creates no edition.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse
from zoneinfo import ZoneInfo
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from tg_video_rights import resolve_for_stories

ROOT = Path(__file__).resolve().parent.parent
ROME = ZoneInfo("Europe/Rome")
SOURCE_FILES = (ROOT / "news.json", ROOT / "editorial.json")
API_URL = "https://api.openai.com/v1/chat/completions"
MAX_STORIES = 9
MIN_STORIES = 4
MODEL = os.getenv("RDI_TG_MODEL", "gpt-4.1-mini")
BAD_HOSTS = {"news.google.com", "translate.google.com", "bing.com", "www.bing.com"}
CATEGORIES = {
    "Diaspora": ("Comunità romena in Italia", 8),
    "Drepturile muncitorilor": ("Lavoro e diritti", 7),
    "Știri consulare": ("Servizi e consolati", 7),
    "Italia": ("Italia", 6),
    "România": ("Romania", 6),
    "Știri din redacție": ("Primo piano", 5),
}
INTRO = ("Buonasera da Radio Românii din Italia. Questo è il TG RDI delle diciotto. "
         "Le notizie sono aggiornate alle sedici, ora italiana. "
         "Dai fatti principali alle conseguenze per la vita quotidiana: ecco il nostro approfondimento.")
OUTRO = ("Questo era il TG RDI della sera. Gli articoli e i collegamenti alle fonti "
         "sono disponibili sul sito Radio Românii din Italia. "
         "Gli sviluppi successivi alle sedici saranno trattati nei prossimi aggiornamenti. "
         "Grazie per averci seguito.")


def read_items(path: Path) -> list[dict]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data.get("items", []) if isinstance(data.get("items"), list) else []
    except (OSError, ValueError, TypeError, AttributeError):
        return []


def cutoff_for(now: dt.datetime) -> dt.datetime:
    if now.tzinfo is None:
        raise ValueError("Aware datetime required")
    day = now.astimezone(ROME).date()
    return dt.datetime(day.year, day.month, day.day, 16, 0, tzinfo=ROME)


def unique_sources(item: dict) -> list[str]:
    raw = item.get("source_urls") or []
    if not isinstance(raw, list):
        return []
    hosts: set[str] = set()
    links: list[str] = []
    for raw_url in raw:
        if not isinstance(raw_url, str) or len(raw_url) > 2048:
            continue
        parsed = urlparse(raw_url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme != "https" or not host or host in BAD_HOSTS:
            continue
        domain = host.removeprefix("www.")
        if domain in hosts:
            continue
        hosts.add(domain)
        links.append(raw_url)
    return links


def normalize_title(s: str) -> set[str]:
    words = re.findall(r"\w+", s.casefold())
    stop = {"il", "la", "di", "e", "a", "in", "de", "și", "un", "una", "cu", "din", "pe"}
    return {w for w in words if len(w) >= 4 and w not in stop}


def eligible(item: dict, cutoff: dt.datetime) -> dict | None:
    if not isinstance(item, dict) or item.get("promotion") or item.get("approved_for_radio") is False:
        return None
    # Unreviewed AI geopolitical drafts are not verified reporting.
    if item.get("editorial_status") in {"ai_assisted_unreviewed", "unverified", "rejected"}:
        return None
    title = str(item.get("title") or "").strip()
    body = str(item.get("body") or "").strip()
    summary = str(item.get("summary") or "").strip()
    url = str(item.get("url") or "")
    if len(title) < 18 or len(body) < 1100 or len(summary) > 50000 or not url.startswith("https://"):
        return None
    sources = unique_sources(item)
    if len(sources) < 2:
        return None
    try:
        published = dt.datetime.fromisoformat(str(item.get("published") or "").replace("Z", "+00:00"))
        if published.tzinfo is None:
            return None
        local = published.astimezone(ROME)
    except (ValueError, TypeError):
        return None
    if not cutoff.replace(hour=0, minute=0) <= local <= cutoff:
        return None
    category = str(item.get("category") or "Primo piano")
    label, weight = CATEGORIES.get(category, ("Primo piano", 3))
    return {
        "id": str(item.get("id") or url),
        "category": category, "category_it": label,
        "title_original": title, "summary_original": summary[:1100],
        "source_text": body[:7000], "source_name": str(item.get("source") or "Fonte pubblica")[:90],
        "source_url": url, "source_urls": sources,
        "published": local.isoformat(),
        "weight": weight,
        # Publisher images are not automatically licensed for YouTube broadcast.
        "visual": (str(item.get("image")) if item.get("imageType") == "ai-editorial-photo"
                   else str(item.get("fallbackImage") or "")),
        "visual_notice": ("Immagine illustrativa generata con IA, non fotografia dell’evento" if item.get("imageType") == "ai-editorial-photo"
                          else "Grafica editoriale illustrativa, non ripresa dei fatti"),
    }


def select_stories(now: dt.datetime, items: list[dict]) -> list[dict]:
    cutoff = cutoff_for(now)
    found = [c for it in items if (c := eligible(it, cutoff))]
    found.sort(key=lambda c: (c["weight"], c["published"], len(c["source_urls"])), reverse=True)
    chosen: list[dict] = []
    represented: dict[str, int] = {}
    signatures: list[set[str]] = []
    for item in found:
        if represented.get(item["category"], 0) >= 3:
            continue
        words = normalize_title(item["title_original"])
        if not words or any(len(words & old) / max(1, len(words | old)) > 0.56 for old in signatures):
            continue
        chosen.append(item)
        signatures.append(words)
        represented[item["category"]] = represented.get(item["category"], 0) + 1
        if len(chosen) == MAX_STORIES:
            break
    # Licensed event clips first, then narrowly matched RDI-verified b-roll.
    # Candidate publisher embeds never enter the TG without recorded rights.
    for story, video in zip(chosen, resolve_for_stories(chosen)):
        story["video"] = video
    return chosen


def request_script(stories: list[dict], key: str) -> dict:
    if not key:
        raise RuntimeError("OPENAI_API_KEY assente: nessun TG generato.")
    evidence = [{
        "id": s["id"], "category": s["category_it"], "title": s["title_original"],
        "source_name": s["source_name"], "source_url": s["source_url"],
        "supporting_source_urls": s["source_urls"],
        "published": s["published"], "summary": s["summary_original"],
        "source_text": s["source_text"],
    } for s in stories]
    instructions = """Sei la redazione di Radio Românii din Italia: prepara UN VERO TELEGIORNALE italiano,
con notizie, spiegazioni e approfondimenti, non una lista di titoli.
Rispondi SOLO con JSON valido: {"language":"it","stories":[{"id":"...",
"title_it":"...","kicker":"...","fact":"...","context":"...",
"implications":"...","developments":"..."}]}. L'ordine e gli ID delle notizie
devono essere quelli dell'input, senza omissioni o nuove notizie.
Per ciascuna notizia scrivi circa 180-260 parole totali ripartite fra i quattro
paragrafi: FACT (chi, cosa, dove, quando), CONTEXT (precedenti rilevanti
documentati nell'input), IMPLICATIONS (conseguenze attribuite o chiaramente
qualificate, con attenzione alla diaspora), DEVELOPMENTS (cosa è previsto o
resta da chiarire, senza inventare sviluppi). Il contenuto deve essere fluido,
giornalistico, comprensibile in lettura a voce, con passaggi variati.
NON creare fatti, nessi causali, dichiarazioni, interviste, statistiche, cifre,
date, numeri, conferme o fonti non presenti nelle prove ricevute.
Se una conseguenza non è documentata, usa una formula prudente e spiega
soltanto perché il fatto può interessare il pubblico, senza dichiarare effetti certi.
Attribuisci le affermazioni controverse alle fonti e mantieni l'incertezza.
Non presentare articoli di terzi come reportage realizzati da RDI. Non riportare
lunghi brani letterali: parafrasa in modo originale. Mantieni integralmente
l'italiano in ogni campo parlato. Non inserire informazioni su eventi dopo
le 16:00 del giorno dell'edizione."""
    payload = {
        "model": MODEL, "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [{"role": "system", "content": instructions},
                     {"role": "user", "content": json.dumps(evidence, ensure_ascii=False)}],
        "max_completion_tokens": 8000,
    }
    req = urllib.request.Request(
        API_URL, data=json.dumps(payload).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + key,
                 "User-Agent": "RDI-TG-Sera/1.0"},
    )
    with urllib.request.urlopen(req, timeout=180) as response:
        result = json.loads(response.read())
    return json.loads(result["choices"][0]["message"]["content"])


def validate_script(raw: dict, selected: list[dict]) -> list[dict]:
    if not isinstance(raw, dict) or raw.get("language") != "it":
        raise ValueError("Lingua o struttura del TG non valida")
    generated = raw.get("stories")
    if not isinstance(generated, list) or len(generated) != len(selected):
        raise ValueError("Il TG non contiene tutte le notizie verificate selezionate")
    output = []
    for src, item in zip(selected, generated):
        if not isinstance(item, dict) or item.get("id") != src["id"]:
            raise ValueError("Ordine o identità delle notizie non coincidente")
        sections = [str(item.get(name) or "").strip() for name in
                    ("fact", "context", "implications", "developments")]
        title = str(item.get("title_it") or "").strip()
        kicker = str(item.get("kicker") or "").strip()
        words = sum(len(section.split()) for section in sections)
        if not (90 <= words <= 330) or not title or not kicker or any(len(p) < 25 for p in sections):
            raise ValueError("Approfondimento troppo breve, lungo o incompleto")
        if re.search(r"<[^>]+>|https?://", " ".join(sections + [title])):
            raise ValueError("Testo non adatto alla voce")
        output.append({
            "id": src["id"], "category": src["category_it"],
            "title": title, "kicker": kicker,
            "paragraphs": sections, "image": src["visual"],
            "image_notice": src["visual_notice"],
            "video": src.get("video"),
            "source_name": src["source_name"],
            "source_url": src["source_url"],
            "sources": src["source_urls"],
            "published": src["published"],
        })
    return output


def build(now: dt.datetime, items: list[dict], script: dict) -> dict:
    selected = select_stories(now, items)
    if len(selected) < MIN_STORIES:
        raise ValueError("Poche notizie approfondite con almeno due fonti indipendenti; TG non pubblicabile")
    stories = validate_script(script, selected)
    cutoff = cutoff_for(now)
    edition_id = cutoff.strftime("%Y%m%d")
    segments = [{"kind": "intro", "text": INTRO}]
    for i, item in enumerate(stories):
        speak = (("Passiamo ora a " if i else "In apertura, ") + item["category"] + ". " +
                 item["title"] + ". " + " ".join(item["paragraphs"]))
        segments.append({"kind": "story", "id": item["id"], "text": speak})
    segments.append({"kind": "outro", "text": OUTRO})
    return {
        "schema_version": 1, "language": "it", "edition_id": edition_id,
        "edition_date": cutoff.date().isoformat(),
        "cutoff_at": cutoff.isoformat(), "generated_at": now.astimezone(ROME).isoformat(),
        "track_title": "RDI-TG-SERA-IT-" + edition_id,
        "synthetic_voice": "it-IT-ElsaNeural",
        "story_count": len(stories), "articles": stories, "segments": segments,
        "editorial_notice": "Sintesi e approfondimenti assistiti da IA da fonti citate; non cronaca in prima persona.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="/tmp/rdi-tg-sera")
    parser.add_argument("--preview", action="store_true",
                        help="Prepara la selezione delle fonti senza consumare API")
    args = parser.parse_args()
    now = dt.datetime.now(ROME)
    cutoff = cutoff_for(now)
    if now < cutoff and not args.preview:
        print("La raccolta del giorno non è chiusa: non generare il TG prima delle 16.")
        return 2
    items = [article for path in SOURCE_FILES for article in read_items(path)]
    selected = select_stories(now, items)
    folder = Path(args.output)
    folder.mkdir(parents=True, exist_ok=True)
    if args.preview:
        safe = [{k: v for k, v in s.items() if k != "source_text"} for s in selected]
        (folder / "source-preview.json").write_text(json.dumps({
            "cutoff_at": cutoff.isoformat(), "candidates": safe,
            "publishable_count": len(safe),
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("TG preview: ", len(selected), "notizie con approfondimenti supportati da fonti.")
        return 0
    if len(selected) < MIN_STORIES:
        print("Nessuna edizione: mancano almeno quattro notizie con approfondimenti e fonti indipendenti.")
        return 2
    raw = request_script(selected, os.getenv("OPENAI_API_KEY", ""))
    edition = build(now, items, raw)
    manifest = folder / "manifest.json"
    manifest.write_text(json.dumps(edition, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    text = "\n\n".join(x["text"] for x in edition["segments"])
    (folder / "tg-script.txt").write_text(text + "\n", encoding="utf-8")
    print("TG SERATA:", edition["track_title"], "notizie:", edition["story_count"],
          "cutoff:", edition["cutoff_at"], "voce:", edition["synthetic_voice"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
