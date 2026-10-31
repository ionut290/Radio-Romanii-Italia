#!/usr/bin/env python3
"""Create one original daily reflection and its shareable RDI artwork."""
import base64
import datetime as dt
import html
import json
import os
import textwrap
import urllib.request
import urllib.error
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "daily-thought.json"
ART_DIR = ROOT / "editorial-images" / "daily-thought"
TZ = ZoneInfo("Europe/Rome")
MODEL = os.environ.get("OPENAI_THOUGHT_MODEL", "gpt-4.1-mini")
API_KEY = os.environ.get("OPENAI_API_KEY", "").strip()

ACTIONS = [
    "ascoltare prima di rispondere",
    "ricominciare senza cancellare ciò che abbiamo imparato",
    "chiedere aiuto quando ne abbiamo bisogno",
    "dire la verità con rispetto",
    "lasciare andare il bisogno di controllare tutto",
    "fare spazio al silenzio",
    "guardare l'errore come un maestro",
    "procedere con ciò che abbiamo, non con ciò che manca",
    "proteggere il nostro tempo senza chiuderci agli altri",
    "riconoscere il bene che già ci accompagna",
    "cambiare idea quando incontriamo ragioni migliori",
    "accogliere il riposo senza sentirci in colpa",
    "scegliere la gentilezza anche nei giorni difficili",
    "costruire ponti invece di vincere discussioni",
    "avere cura delle parole che lasciamo agli altri",
    "distinguere ciò che possiamo cambiare da ciò che dobbiamo accettare",
    "restare curiosi davanti alle differenze",
    "perdonare senza dimenticare ciò che abbiamo imparato",
    "fare un passo piccolo ma sincero",
    "cominciare prima di sentirci pronti",
    "ascoltare il bisogno dietro la rabbia",
    "condividere il merito e la fatica",
    "non misurare la nostra vita con quella altrui",
    "trattare noi stessi con la stessa pazienza",
    "dire no a ciò che ci allontana da ciò che conta",
    "trasformare l'attesa in un tempo abitabile",
    "concederci un nuovo inizio",
    "restare presenti mentre il futuro si chiarisce",
    "chiedere scusa senza cercare alibi",
    "accettare che crescere richieda tempo",
    "scegliere una risposta invece di una reazione",
    "custodire la speranza senza negare la realtà",
]
OBSTACLES = [
    "la risposta non arriva subito", "la strada non è ancora chiara",
    "il risultato dipende anche da altri", "il dubbio cammina accanto a noi",
    "la fretta ci chiede di correre", "non tutti comprendono la nostra scelta",
    "il passato prova a trattenerci", "le giornate non vanno secondo i piani",
    "la meta sembra lontana", "la paura non è ancora scomparsa",
    "ci restano molte domande aperte", "il cambiamento procede lentamente",
    "non possiamo sapere come finirà", "le nostre energie non sono infinite",
    "il silenzio pesa più delle parole", "il confronto ci fa perdere il nostro ritmo",
    "l'errore ci ricorda che stiamo imparando", "la stanchezza chiede ascolto",
    "non abbiamo tutte le risorse che vorremmo", "la pazienza viene messa alla prova",
    "ci sono cose che non dipendono da noi", "il giudizio altrui ci fa esitare",
    "il prossimo passo è ancora piccolo", "la vita ci sorprende con deviazioni",
    "non riusciamo a controllare ogni dettaglio", "la nostalgia ci porta altrove",
    "la fiducia ha bisogno di tempo", "le parole giuste tardano ad arrivare",
    "la luce arriva a piccoli tratti", "la solitudine si fa sentire",
    "la perfezione ci invita a rimandare", "la nostra storia non assomiglia a quella degli altri",
]

def load_data():
    if not DATA.exists():
        return {"description": "Pensieri originali quotidiani della rubrica RDI.", "items": []}
    value = json.loads(DATA.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("items", []), list):
        raise SystemExit("Archivio daily-thought.json non valido")
    return value

def fallback_thought(day):
    # This first entry matches the sample presented for the launch date.
    if day.isoformat() == "2026-10-30":
        return {
            "title": "Il passo di oggi",
            "quote": "Non serve avere tutta la strada davanti: basta fare con cura il passo di oggi.",
            "reflection": "A volte la direzione si chiarisce mentre camminiamo. Oggi basta scegliere il prossimo passo con attenzione.",
        }
    offset = day.toordinal() - 1
    action = ACTIONS[offset % len(ACTIONS)]
    obstacle = OBSTACLES[(offset // len(ACTIONS)) % len(OBSTACLES)]
    forms = (
        "La serenità cresce quando scegliamo di {action}, anche se {obstacle}.",
        "A volte il passo più saggio è {action}; anche se {obstacle}, possiamo restare presenti.",
        "Possiamo {action}, anche se {obstacle}: la fretta non decide il nostro valore.",
        "Ogni giorno ci invita a {action}, persino quando {obstacle}; il cammino resta nostro.",
    )
    quote = forms[offset % len(forms)].format(action=action, obstacle=obstacle)
    reflection = (
        "Oggi proviamo a fare spazio a questa scelta, senza pretendere che tutto si risolva subito. "
        "Anche un gesto piccolo può dare una direzione alla giornata."
    )
    return {"title": "Un passo alla volta", "quote": quote, "reflection": reflection}

def api_thought(day, history):
    if not API_KEY:
        return None
    instructions = (
        "Scrivi per Radio Românii din Italia un pensiero filosofico quotidiano completamente originale, "
        "in italiano, breve, umano e concreto. Non citare né imitare autori, non attribuire la frase a nessuno, "
        "non usare religione o politica. Evita frasi presenti nell'elenco delle ultime pubblicazioni. "
        "Restituisci solo JSON valido con title (2-6 parole), quote (una frase di 10-22 parole), "
        "reflection (una riflessione di 20-45 parole)."
    )
    payload = {
        "model": MODEL,
        "temperature": 0.9,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": instructions},
            {"role": "user", "content": json.dumps({
                "date": day.isoformat(),
                "recent_quotes": history[-45:],
            }, ensure_ascii=False)},
        ],
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + API_KEY},
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            content = json.loads(response.read())["choices"][0]["message"]["content"]
        result = json.loads(content)
        title = " ".join(str(result.get("title", "")).split())[:90]
        quote = " ".join(str(result.get("quote", "")).split())[:300]
        reflection = " ".join(str(result.get("reflection", "")).split())[:600]
        if not title or len(quote.split()) < 8 or not reflection:
            return None
        if quote.casefold() in {str(x).casefold() for x in history}:
            return None
        return {"title": title, "quote": quote, "reflection": reflection}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Generazione API non disponibile; uso la composizione locale:", str(exc)[:140])
        return None

def svg_card(day, quote, title):
    lines = textwrap.wrap(quote, width=39, break_long_words=False, break_on_hyphens=False) or [quote]
    if len(lines) > 5:
        lines = textwrap.wrap(quote, width=48, break_long_words=False, break_on_hyphens=False)[:5]
    font_size = 47 if len(lines) <= 3 else 40
    line_height = int(font_size * 1.27)
    start_y = 250 - (len(lines) - 1) * line_height // 2
    tspans = "".join(
        '<tspan x="82" y="' + str(start_y + i * line_height) + '">' + html.escape(line) + '</tspan>'
        for i, line in enumerate(lines)
    )
    safe_title = html.escape(title)
    date = day.strftime("%d %B %Y").upper()
    months = {
        "JANUARY":"GENNAIO","FEBRUARY":"FEBBRAIO","MARCH":"MARZO","APRIL":"APRILE",
        "MAY":"MAGGIO","JUNE":"GIUGNO","JULY":"LUGLIO","AUGUST":"AGOSTO",
        "SEPTEMBER":"SETTEMBRE","OCTOBER":"OTTOBRE","NOVEMBER":"NOVEMBRE","DECEMBER":"DICEMBRE",
    }
    for en, it in months.items():
        date = date.replace(en, it)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-label="{html.escape(quote, quote=True)}">
<defs>
 <linearGradient id="sky" x2="0" y2="1"><stop stop-color="#08172c"/><stop offset=".58" stop-color="#243c57"/><stop offset="1" stop-color="#b96c43"/></linearGradient>
 <linearGradient id="shade" x2="1"><stop stop-color="#071426" stop-opacity=".98"/><stop offset=".72" stop-color="#071426" stop-opacity=".72"/><stop offset="1" stop-color="#071426" stop-opacity=".12"/></linearGradient>
 <linearGradient id="road" x2="0" y2="1"><stop stop-color="#d99a5a"/><stop offset="1" stop-color="#523a37"/></linearGradient>
</defs>
<rect width="1200" height="630" fill="url(#sky)"/>
<circle cx="1000" cy="250" r="92" fill="#ffcf7a" opacity=".9"/>
<path d="M0 365 Q180 250 360 355 T760 335 T1200 360 V630 H0Z" fill="#314c4a"/>
<path d="M0 418 Q240 330 470 425 T890 390 T1200 430 V630 H0Z" fill="#1c393b"/>
<path d="M560 630 Q635 505 650 408 Q682 500 805 630Z" fill="url(#road)" opacity=".9"/>
<path d="M0 0 H1200 V630 H0Z" fill="url(#shade)"/>
<path d="M1040 0 Q1020 140 1120 190 M1100 0 Q1080 100 1180 145" fill="none" stroke="#c68c52" stroke-width="8" opacity=".55"/>
<text x="82" y="92" fill="#f3c66b" font-family="Arial,sans-serif" font-size="19" font-weight="700" letter-spacing="5">PENSIERO DEL GIORNO · {date}</text>
<path d="M82 124 H690" stroke="#f3c66b" stroke-width="2" opacity=".8"/>
<text fill="#fffaf1" font-family="Georgia,serif" font-size="{font_size}" font-weight="bold">{tspans}</text>
<text x="82" y="555" fill="#f3c66b" font-family="Arial,sans-serif" font-size="20" font-weight="700" letter-spacing="4">RADIO ROMÂNII DIN ITALIA</text>
<text x="1118" y="92" fill="#fff" fill-opacity=".72" text-anchor="end" font-family="Arial,sans-serif" font-size="13" letter-spacing="2">{safe_title.upper()}</text>
</svg>
'''


def api_photo(day, quote):
    if not API_KEY:
        print("OPENAI_API_KEY non configurata: uso la grafica illustrata di riserva.")
        return None
    prompt = (
        "Create one original, photorealistic editorial photograph for a thoughtful Italian-Romanian community radio. "
        "Translate the meaning of this short philosophical reflection into a visually clear, human scene: "
        + quote
        + ". Natural candid moment, authentic people and setting, thoughtful but not sentimental, "
        "cinematic natural light, documentary photography, realistic anatomy and details. "
        "Wide horizontal composition suitable for a 16:9 broadcast crop. "
        "No words, lettering, captions, signs, logos, watermarks, borders, or graphic overlays."
    )
    payload = {
        "model": os.environ.get("OPENAI_IMAGE_MODEL", "gpt-image-2"),
        "prompt": prompt,
        "size": "1536x1024",
        "quality": "medium",
        "output_format": "jpeg",
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + API_KEY},
    )
    try:
        with urllib.request.urlopen(request, timeout=240) as response:
            result = json.loads(response.read())
        image = base64.b64decode(result["data"][0]["b64_json"], validate=True)
        if len(image) < 10000 or not image.startswith(bytes.fromhex("ffd8ff")):
            raise ValueError("Il risultato non è un JPEG valido")
        return image
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print("Foto realistica non disponibile; uso la grafica illustrata:", str(exc)[:180])
        return None


def curated_photo(day, quote, entries):
    """Create a fresh daily JPEG from RDI's own realistic picture library.

    This is a photo composition (not a newly AI-generated photograph).
    Photographs are rotated without repeating any in the last 90 entries.
    """
    import hashlib
    import io
    import re
    import unicodedata
    from PIL import Image, ImageEnhance, ImageOps

    gallery = ROOT / "editorial-images" / "news-covers"
    photos = sorted(gallery.glob("rdi-biblioteca-*.jpg"))
    if len(photos) < 15:
        raise RuntimeError("Fototeca RDI insufficiente: pubblicazione della foto annullata")
    theme_groups = {
        "ascolt": ["incontro", "genitori", "associazione", "aiuto-smartphone"],
        "calma": ["ciclismo", "corsa-parco", "cura-parco", "biblioteca-incontro"],
        "pazien": ["giardiniera", "raccolta-serra", "cura-parco"],
        "cresc": ["giardiniera", "raccolta-serra", "formazione-professionale"],
        "tempo": ["ciclismo", "corsa-parco", "corsa", "stazione"],
        "gentil": ["volontari", "donazioni", "amici-al-parco", "aiuto"],
        "aiuto": ["volontari", "aiuto-smartphone", "incontro", "donazioni"],
        "comunit": ["festa-quartiere", "incontro-associazione", "riunione"],
        "incontr": ["incontro", "amici-al-parco", "mercato-incontro"],
        "ricomin": ["corsa-parco", "formazione-professionale", "giardiniera"],
        "radic": ["giardiniera", "raccolta-serra", "cura-parco"],
        "famigli": ["pranzo-famiglia", "incontro-genitori", "amici-al-parco"],
        "libert": ["ciclismo", "treno-regionale", "viaggio-aeroporto"],
        "coragg": ["sicurezza-cantiere", "volontari", "sport"],
        "silenz": ["biblioteca-incontro", "studio-universitario", "cura-parco"],
        "speranz": ["volontari", "giardiniera", "formazione"],
        "scelt": ["viaggiatori-mappa-binari", "formazione", "giardiniera"],
        "parol": ["corso-lingua-adulti", "insegnante-italiano", "incontro"],
        "domand": ["lezione-scientifica", "studio-universitario", "biblioteca"],
        "luce": ["giardiniera", "ciclismo-collina", "cura-parco"],
        "strad": ["manutenzione-stradale", "ciclismo-collina", "pista-ciclabile"],
        "amore": ["pranzo-famiglia", "amici-al-parco", "incontro-genitori"],
    }
    normalized = unicodedata.normalize("NFKD", quote.lower())
    normalized = "".join(c for c in normalized if not unicodedata.combining(c))
    desired = []
    for key, names in theme_groups.items():
        if key in normalized:
            desired.extend(names)
    used = set()
    for entry in entries[:90]:
        source = str(entry.get("photo_source", ""))
        if source:
            used.add(source)

    def rank(path):
        rel = path.relative_to(ROOT).as_posix()
        name = path.stem.lower()
        thematic = sum(14 for word in desired if word in name)
        # Deterministic tie breaker, but a different photo is selected every day.
        seed = hashlib.sha256((day.isoformat() + ":" + rel).encode("utf-8")).digest()
        variety = int.from_bytes(seed[:4], "big") / (2 ** 32)
        return (rel not in used, thematic, variety)

    source = max(photos, key=rank)
    try:
        with Image.open(source) as src:
            photo = ImageOps.fit(src.convert("RGB"), (1920, 1080), method=Image.Resampling.LANCZOS)
        photo = ImageEnhance.Color(photo).enhance(0.96)
        photo = ImageEnhance.Contrast(photo).enhance(0.96)
        photo = ImageEnhance.Brightness(photo).enhance(1.03)
        output = io.BytesIO()
        photo.save(output, "JPEG", quality=88, optimize=True, progressive=True)
        data = output.getvalue()
        if len(data) < 10000:
            raise RuntimeError("Fotografia composta troppo piccola")
        rel = source.relative_to(ROOT).as_posix()
        print("Fotografia RDI selezionata, non ripetuta:", rel)
        return data, rel
    except Exception as exc:
        raise RuntimeError("Impossibile creare la fotografia RDI: " + str(exc)) from exc


def planned_thought(day):
    """Use the curated RDI philosophical calendar where a quote is already approved."""
    path = ROOT / "data" / "calendario-filosofico-2026.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        entry = next((x for x in data.get("days", []) if x.get("date") == day.isoformat()), None)
        quote = str(entry.get("quote", "")).strip() if entry else ""
        if not quote:
            return None
        return {
            "title": "Pensiero del giorno",
            "quote": quote,
            "reflection": (
                "Ogni giornata offre un'occasione per trasformare questa riflessione in un gesto reale. "
                "Non occorre cambiare tutto in una volta: possiamo cominciare da una scelta concreta, "
                "osservando come influisce su di noi e sulle persone che incontriamo."
            ),
        }
    except (ValueError, OSError, TypeError):
        return None


def main():
    now = dt.datetime.now(TZ)
    today = now.date()
    data = load_data()
    items = data.get("items", [])
    for item in items:
        if item.get("date") == today.isoformat():
            existing_image = ROOT / str(item.get("image", "")).removeprefix("./")
            if existing_image.suffix.lower() in (".jpg", ".jpeg", ".png") and existing_image.is_file() and existing_image.stat().st_size > 10000:
                print("Pensiero e fotografia del giorno già pubblicati:", today.isoformat())
                return
    history = [str(x.get("quote", "")) for x in items if x.get("quote")]
    thought = api_thought(today, history) or planned_thought(today) or fallback_thought(today)
    published = now.replace(hour=1, minute=0, second=0, microsecond=0)
    ident = "pensiero-" + today.strftime("%Y%m%d")
    # Non eseguire chiamate immagini a pagamento senza consenso esplicito.
    use_ai_images = os.environ.get("RDI_THOUGHT_USE_AI_IMAGES", "0") == "1"
    image_bytes = api_photo(today, thought["quote"]) if use_ai_images else None
    photo_source = ""
    if not image_bytes:
        image_bytes, photo_source = curated_photo(today, thought["quote"], items)
    image = Path("editorial-images/daily-thought") / (today.isoformat() + ".jpg")
    item = {
        "id": ident,
        "daily_thought": True,
        "category": "Pensiero del giorno",
        "title": thought["title"],
        "summary": thought["quote"],
        "body": thought["quote"] + "\n\n" + thought["reflection"],
        "extended_summary": True,
        "published": published.isoformat(),
        "source": "Pensiero originale RDI",
        "byline": "Rubrica quotidiana · Radio Românii din Italia",
        "image": "./" + image.as_posix(),
        "imageType": "photorealistic-ai-generated" if not photo_source else "rdi-archive-photo-composition",
        "photo_source": photo_source,
        "image_credit": "Fotografia generata con IA per RDI" if not photo_source else "Composizione fotografica realizzata con immagini della fototeca RDI",
        "date": today.isoformat(),
    }
    items = [item] + [x for x in items if x.get("date") != today.isoformat()]
    data["items"] = items[:90]
    data["updated_at"] = now.isoformat()
    DATA.parent.mkdir(parents=True, exist_ok=True)
    ART_DIR.mkdir(parents=True, exist_ok=True)
    (ROOT / image).write_bytes(image_bytes)
    # Preserve assets still used by the 90-day news archive or the approved 2026 calendar.
    # Otherwise future readers and calendar integrity tests would see broken images.
    protected = {ROOT / image}
    for archived in items:
        referenced = str(archived.get("image", "")).removeprefix("./").lstrip("/")
        if referenced:
            protected.add(ROOT / referenced)
    calendar_path = DATA.parent / "calendario-filosofico-2026.json"
    if calendar_path.is_file():
        try:
            calendar = json.loads(calendar_path.read_text(encoding="utf-8"))
            for entry in calendar.get("days", []):
                referenced = str(entry.get("image", "")).removeprefix("./").lstrip("/")
                if referenced:
                    protected.add(ROOT / referenced)
        except (OSError, ValueError, TypeError):
            pass
    for old_image in ART_DIR.iterdir():
        if old_image.is_file() and old_image not in protected:
            old_image.unlink()
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pointer = DATA.parent / "calendario-filosofico-oggi.json"
    pointer.write_text(json.dumps({
        "date": item["date"],
        "quote": item["summary"],
        "image": "/" + image.as_posix(),
        "reflection": thought["reflection"],
        "status": "published",
        "image_source": item["image_credit"],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Pensiero quotidiano pronto:", today.isoformat(), "|", thought["quote"])

if __name__ == "__main__":
    main()
