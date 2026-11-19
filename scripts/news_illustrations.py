"""Assegna immagini RDI alle notizie e crea fallback editoriali unici.

Le foto illustrative provengono dalla libreria classificata in data/news-image-library.json.
Quando non è disponibile una foto fonte o una copertina libera e pertinente, genera un SVG
unico per l'articolo. Le immagini IA sono sempre dichiarate come illustrative.
"""
import hashlib
import html
import json
import re
import textwrap
from pathlib import Path

OUT = Path("editorial-images")
COLORS = {
    "italia": ("#183c69", "#2585a7", "#e1b55d"),
    "românia": ("#19396b", "#5870bf", "#f6c45a"),
    "diaspora": ("#183c67", "#835a9d", "#e9ad69"),
    "știri consulare": ("#153e64", "#427c9b", "#edc26b"),
    "drepturile muncitorilor": ("#183e5b", "#408c81", "#e9b957"),
    "conflict": ("#101f35", "#34415a", "#d5ad79"),
    "muzică": ("#56315f", "#a34a80", "#f1bbd1"),
    "cinema și seriale": ("#242b54", "#4e4b99", "#f3c77b"),
    "tehnologie": ("#17375e", "#307eb5", "#a7ddf7"),
    "inteligență artificială": ("#263165", "#6958bd", "#bfe8ff"),
    "educație": ("#345069", "#408c91", "#f2cf7b"),
    "știință": ("#163d65", "#3b78ad", "#b8e5ff"),
    "sănătate": ("#265867", "#35a094", "#e4f1ff"),
    "mediu și climă": ("#224a41", "#4e9767", "#d5e99d"),
    "sport": ("#284966", "#3782ae", "#f4d58b"),
    "cultură și cărți": ("#54405e", "#945f8b", "#efc8ad"),
    "călătorii": ("#1e5064", "#51a1ad", "#f0c97b"),
    "economie și consumatori": ("#315143", "#589a73", "#e4c76c"),
}
TOPICS = [
    (("meteo", "ploi", "ploaie", "vreme", "tempo", "allerta"), "weather"),
    (("ambiente", "ambient", "clima", "climate", "rifiut", "riciclo", "forest", "inquin", "ecolog"), "environment"),
    (("sanit", "medic", "spital", "salute", "ospedal"), "health"),
    (("sport", "calcio", "serie a", "football", "partita", "squadra", "campionato", "coppa", "champions league", "scudetto"), "sports"),
    (("tecnolog", "technology", "digit", "intelligenza artificiale", "intelligenţa artificială", "software", "cyber", "anthropic", "microsoft"), "technology"),
    (("scuol", "școal", "scoal", "student", "universit", "educa"), "education"),
    (("aeroport", "volo", "zbor", "viagg", "calator", "călător", "tren", "ferov", "scioper", "strike", "transport"), "travel"),
    (("econom", "fisc", "tax", "preț", "pret", "ban", "euro", "stipend", "pensi"), "finance"),
    (("lavor", "worker", "muncitor", "muncă", "munca", "sindac", "angaja", "salari"), "workers"),
    (("poliz", "carabin", "incident", "arest", "poliț", "bodycam", "tribunal", "giudice", "condann", "omicid", "aggression", "aggressione"), "justice"),
    (("consulat", "ambasad", "document", "passaport", "pașaport"), "institution"),
    (("elezion", "election", "parlament", "govern", "guvern", "ministro", "minister", "politic", "israel", "brasile", "brazil", "knesset"), "institution"),
    (("famil", "diaspor", "român", "român", "comunit", "migrant"), "community"),
]

def is_armed_conflict(item):
    """Detect armed violence without classifying ordinary political/economic 'attacks' as war."""
    combined = " ".join(str(item.get(key) or "") for key in ("title", "summary", "category")).casefold()
    explicit = r"ambuscad|ambush|emboscad|bombard|război|razboi|guerra|guerre|\bwar\b|jihad|teroris|terroris|masacr|massacr|conflict armat|armed conflict"
    attacks = r"atac|attacc|attack|assalt|raid"
    victims = r"militar|solda|civili|civilian|ucis|morț|morti|killed|\bdead\b|armată|armata|armed|bomba|exploz|explosi|jihad|teroris|terroris"
    return bool(re.search(explicit, combined) or (
        re.search(attacks, combined) and re.search(victims, combined)
    ))


CATEGORY_TOPICS = {
    "muzică": "music",
    "cinema și seriale": "cinema",
    "tehnologie": "technology",
    "inteligență artificială": "artificial_intelligence",
    "educație": "education",
    "știință": "science",
    "sănătate": "health",
    "mediu și climă": "environment",
    "sport": "sports",
    "cultură și cărți": "culture",
    "călătorii": "travel",
    "economie și consumatori": "finance",
}

def topic_for(item):
    if is_armed_conflict(item):
        return "conflict"
    explicit_topic = CATEGORY_TOPICS.get(str(item.get("category") or "").casefold())
    if explicit_topic:
        return explicit_topic
    combined = " ".join(str(item.get(key) or "") for key in ("title", "summary", "category")).casefold()
    if re.search(r"\b(?:milan|juventus|inter|lazio|napoli|fiorentina|atalanta)\b", combined):
        return "sports"
    for needles, topic in TOPICS:
        if any(needle in combined for needle in needles):
            return topic
    return "general"

def drawing(topic, accent):
    # Vector illustrations deliberately symbolic: never represent a real event or person.
    if topic == "conflict":
        return '<g transform="translate(784 300)"><path d="M0-125 113 89H-113Z" fill="#d5ad79"/><path d="M0-45v67" stroke="#17283f" stroke-width="19" stroke-linecap="round"/><circle cy="54" r="11" fill="#17283f"/></g><circle cx="784" cy="300" r="202" fill="none" stroke="#fff" stroke-opacity=".2" stroke-width="6"/>'
    if topic == "finance":
        return '<g fill="#f5cf75"><rect x="600" y="340" width="85" height="160" rx="8"/><rect x="710" y="283" width="85" height="217" rx="8"/><rect x="820" y="208" width="85" height="292" rx="8"/></g><path d="M615 260 735 205 790 220 910 118" fill="none" stroke="#fff" stroke-width="15" stroke-linecap="round"/>'
    if topic == "weather":
        return '<circle cx="785" cy="190" r="100" fill="#f5ce67"/><g fill="#e9f2fc"><ellipse cx="690" cy="332" rx="135" ry="70"/><ellipse cx="790" cy="320" rx="118" ry="76"/><ellipse cx="865" cy="352" rx="90" ry="52"/></g><g stroke="#a3d3ff" stroke-width="13"><path d="M690 423l-26 45m112-45-26 45m112-45-26 45"/></g>'
    if topic == "health":
        return '<rect x="640" y="120" width="220" height="320" rx="28" fill="#e9f2fc"/><rect x="725" y="171" width="51" height="210" rx="8" fill="#db5360"/><rect x="648" y="250" width="205" height="52" rx="8" fill="#db5360"/>'
    if topic == "education":
        return '<path d="M565 260 775 154 986 260 775 363Z" fill="#e7c170"/><path d="M645 323v120q128 92 260 0V323" fill="#edf3fd"/><path d="M971 270v146" stroke="#eac474" stroke-width="13"/>'
    if topic == "travel":
        return '<path d="M600 338 972 165 815 355 794 490 730 386Z" fill="#edf4fe"/><path d="m750 355-90 105" stroke="#e7c477" stroke-width="18" stroke-linecap="round"/>'
    if topic in ("justice", "institution"):
        return '<path d="M600 245 780 137 960 245Z" fill="#f0cb7e"/><rect x="630" y="257" width="300" height="24" fill="#edf2f9"/><g stroke="#e9eff9" stroke-width="38"><path d="M680 291v155m100-155v155m100-155v155"/></g><rect x="610" y="450" width="340" height="24" fill="#f0cb7e"/>'
    if topic == "community":
        return '<g fill="#e9f3fc"><circle cx="690" cy="252" r="56"/><circle cx="853" cy="252" r="56"/><circle cx="771" cy="297" r="43"/><path d="M587 472q0-146 103-146t103 146Zm164 0q0-146 103-146t103 146Z"/></g>'
    if topic == "music":
        return '<g fill="#f6dfed"><circle cx="700" cy="405" r="50"/><circle cx="865" cy="367" r="50"/><path d="M742 390V190l165-42v205h-35V195l-95 25v169Z"/></g>'
    if topic == "cinema":
        return '<rect x="616" y="240" width="340" height="235" rx="18" fill="#e8e5fd"/><path d="M616 240h340v65H616Z" fill="#292f68"/><path d="m645 245 55 58m55-58 55 58m55-58 55 58" stroke="#ead28b" stroke-width="23"/><path d="m630 220 300-92 24 80-300 92Z" fill="#ead28b"/>'
    if topic == "technology":
        return '<rect x="654" y="178" width="254" height="254" rx="28" fill="#e4f2ff"/><rect x="708" y="232" width="146" height="146" rx="16" fill="#3976a8"/><g stroke="#e4f2ff" stroke-width="14"><path d="M685 147v31m80-31v31m80-31v31m80 75h-17m17 80h-17M685 432v30m80-30v30m80-30v30M654 250h-35m35 80h-35"/></g>'
    if topic == "artificial_intelligence":
        return '<g stroke="#c7e6ff" stroke-width="12" fill="none"><path d="M660 226 793 155 908 237 880 395 743 455 625 348 660 226M660 226l220 169M793 155 743 455M625 348l283-111"/></g><g fill="#f0d08b"><circle cx="660" cy="226" r="26"/><circle cx="793" cy="155" r="26"/><circle cx="908" cy="237" r="26"/><circle cx="880" cy="395" r="26"/><circle cx="743" cy="455" r="26"/><circle cx="625" cy="348" r="26"/></g>'
    if topic == "science":
        return '<g fill="none" stroke="#def3ff" stroke-width="12"><ellipse cx="778" cy="306" rx="210" ry="82"/><ellipse cx="778" cy="306" rx="210" ry="82" transform="rotate(60 778 306)"/><ellipse cx="778" cy="306" rx="210" ry="82" transform="rotate(-60 778 306)"/></g><circle cx="778" cy="306" r="40" fill="#f3d17f"/>'
    if topic == "environment":
        return '<path d="M946 160Q652 150 612 365q65 185 245 87 115-69 89-292Z" fill="#d0e7b2"/><path d="M632 461q108-145 274-233" fill="none" stroke="#326a55" stroke-width="20" stroke-linecap="round"/>'
    if topic == "sports":
        return '<circle cx="780" cy="310" r="181" fill="#f0f4fc"/><path d="m780 242-60 50 25 72h77l30-72Z" fill="#395a76"/><path d="m650 235 70 57m130 0 65-64m-94 135 35 100m-113-99-47 100" stroke="#395a76" stroke-width="16" fill="none"/>'
    if topic == "culture":
        return '<path d="M588 195q110-45 190 16 98-61 194-16v264q-97-42-194 16-98-57-190-16Z" fill="#f3e6f2"/><path d="M778 211v264" stroke="#ac7fa1" stroke-width="13"/><path d="M622 255q55-16 111 8m-111 42q55-16 111 8m90-50q54-23 113-8m-113 58q54-23 113-8" stroke="#92708e" stroke-width="9" fill="none"/>'
    return '<g fill="none" stroke="#eef4fd" stroke-width="15"><circle cx="775" cy="297" r="156"/><ellipse cx="775" cy="297" rx="73" ry="156"/><path d="M621 297h308m-290-75h272m-272 150h272"/></g>'

def make_svg(item):
    category = str(item.get("category") or "Actualitate")[:48]
    title = re.sub(r"\\s+", " ", str(item.get("title") or "")).strip()
    theme = COLORS.get(category.casefold(), ("#183b64", "#476aa3", "#f0c06b"))
    topic = topic_for(item)
    # Headlines are displayed separately in the HTML news panel.
    headline = ""
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="675" viewBox="0 0 1200 675" role="img" aria-label="Illustrazione editoriale RDI">
<defs><linearGradient id="bg" x2="1" y2="1"><stop stop-color="{theme[0]}"/><stop offset="1" stop-color="{theme[1]}"/></linearGradient><linearGradient id="shade"><stop stop-color="#0b223a" stop-opacity=".65"/><stop offset="1" stop-color="#0b223a" stop-opacity="0"/></linearGradient></defs>
<rect width="1200" height="675" fill="url(#bg)"/><circle cx="940" cy="320" r="295" fill="#fff" opacity=".065"/><circle cx="1130" cy="80" r="170" fill="{theme[2]}" opacity=".13"/>
<g>{drawing(topic,theme[2])}</g><rect x="0" y="0" width="670" height="675" fill="url(#shade)"/>
<rect x="45" y="40" width="265" height="94" rx="12" fill="#09264a" opacity=".97"/>
<text x="65" y="99" font-family="Arial,sans-serif" font-size="53" font-weight="900" fill="white">RDI</text>
<text x="177" y="83" font-family="Arial,sans-serif" font-size="15" font-weight="800" fill="white">RADIO ROMÂNII</text><text x="177" y="105" font-family="Arial,sans-serif" font-size="15" font-weight="800" fill="white">DIN ITALIA</text>
<rect x="292" y="43" width="6" height="29" fill="#009246"/><rect x="298" y="43" width="6" height="29" fill="#fff"/><rect x="304" y="43" width="6" height="29" fill="#ce2b37"/>
<rect x="65" y="234" width="260" height="36" rx="8" fill="{theme[2]}"/><text x="80" y="259" font-family="Arial,sans-serif" font-size="{13 if len(category) > 20 else 16}" font-weight="800" fill="#16233b">{html.escape(category.upper())}</text>
<rect y="610" width="1200" height="65" fill="#0b1b32" opacity=".88"/><text x="65" y="649" font-family="Arial,sans-serif" font-size="20" fill="#d6e5f7">RADIO ROMÂNII DIN ITALIA · ILUSTRAȚIE EDITORIALĂ</text>
</svg>'''

def fill_missing_images(items):
    """Use a real publisher image or a subject-matched local photo.

    No random category photo, no inherited stale assignment, no stock photo
    presented as the photograph of a fatal or breaking-news event.
    """
    from news_image_matching import choose_relevant_photo

    OUT.mkdir(parents=True, exist_ok=True)
    assignment_file = Path(__file__).resolve().parents[1] / "data" / "news-cover-assignments.json"
    library_file = Path(__file__).resolve().parents[1] / "data" / "news-image-library.json"
    try:
        library = json.loads(library_file.read_text(encoding="utf-8")).get("categories", {})
    except (OSError, json.JSONDecodeError, AttributeError):
        library = {}

    library_by_path = {
        entry.get("image"): entry
        for entries in library.values() if isinstance(entries, list)
        for entry in entries if isinstance(entry, dict) and entry.get("image")
    }
    used_photos = set()
    used_svgs = set()
    assignments = {}
    generated = 0
    selected_photos = 0
    source_photos = 0

    for item in items:
        identity = str(item.get("url") or item.get("title") or "")
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        svg_path = OUT / f"rdi-auto-v2-{digest}.svg"
        svg_content = make_svg(item)
        if not svg_path.exists() or svg_path.read_text(encoding="utf-8") != svg_content:
            svg_path.write_text(svg_content, encoding="utf-8")
            generated += 1
        used_svgs.add(svg_path.name)
        svg_fallback = "./" + svg_path.as_posix()

        existing = str(item.get("image") or "")
        # Editorial AI photos may survive in imported, verified stories. They
        # must be re-evaluated, not mistaken for true publisher imagery.
        machine_assigned = (
            item.get("imageType") in ("ai-editorial-photo", "editorial-illustration")
            or existing in library_by_path
            or existing.startswith("./editorial-images/ai-")
            or existing.startswith("./editorial-images/news-covers/")
            or existing.startswith("./editorial-images/rdi-auto-")
            or existing == "./editorial-images/rdi-conflict-editorial.svg"
        )
        item["fallbackImage"] = svg_fallback
        if existing and not machine_assigned:
            # The publisher's own image (or a separately curated editorial
            # image) has precedence over any generic stock photography.
            source_photos += 1
            continue

        for key in ("image_credit", "imageAttribution", "imageType"):
            item.pop(key, None)
        selected = choose_relevant_photo(item, library, used_photos)
        if selected is not None:
            photo = selected["image"]
            used_photos.add(photo)
            selected_photos += 1
            item["image"] = photo
            item["imageType"] = "ai-editorial-photo"
            credit = selected.get(
                "credit",
                "Copertina fotorealistica generata con IA; immagine di contesto, non la fotografia dell'evento.",
            )
            item["image_credit"] = credit
            item["imageAttribution"] = credit
            if item.get("url"):
                assignments[item["url"]] = {
                    "image": photo,
                    "credit": credit,
                    "matched_description": selected.get("description", ""),
                    "selection": "subject-matched-v3",
                }
        else:
            item["image"] = svg_fallback
            item["imageType"] = "editorial-illustration"
            item["imageAttribution"] = (
                "Illustrazione editoriale RDI, non fotografia dell'evento."
            )

    # Rebuild cache only from checked subjects: the old hash-derived mappings
    # may contain off-topic pairings and must never influence future runs.
    assignment_file.write_text(
        json.dumps(assignments, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for svg_path in OUT.glob("rdi-auto-*.svg"):
        if svg_path.name not in used_svgs:
            svg_path.unlink()
    print(
        f"Immagini RDI: {source_photos} da fonte, "
        f"{selected_photos} foto di contesto pertinenti, "
        f"{len(items) - source_photos - selected_photos} copertine neutrali; "
        f"{generated} SVG aggiornati."
    )
