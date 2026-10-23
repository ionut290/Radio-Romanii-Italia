"""Genera illustrazioni editoriali SVG RDI per le notizie senza immagini.

Nessuna API a pagamento. Non sono fotografie né immagini prodotte da un modello IA.
"""
import hashlib
import html
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
}
TOPICS = [
    (("meteo", "ploi", "ploaie", "vreme", "tempo", "allerta"), "weather"),
    (("sanit", "medic", "spital", "salute", "ospedal"), "health"),
    (("scuol", "școal", "scoal", "student", "universit", "educa"), "education"),
    (("aeroport", "volo", "zbor", "viagg", "calator", "călător"), "travel"),
    (("econom", "fisc", "tax", "preț", "pret", "ban", "euro", "stipend", "pensi"), "finance"),
    (("poliz", "carabin", "incident", "arest", "poliț", "polit"), "justice"),
    (("consulat", "ambasad", "document", "passaport", "pașaport"), "institution"),
    (("famil", "diaspor", "român", "român", "comunit", "migrant"), "community"),
]

def topic_for(item):
    combined = (item.get("title", "") + " " + item.get("category", "")).casefold()
    for needles, topic in TOPICS:
        if any(needle in combined for needle in needles):
            return topic
    return "general"

def drawing(topic, accent):
    # Vector illustrations deliberately symbolic: never represent a real event or person.
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
<rect x="65" y="234" width="260" height="36" rx="8" fill="{theme[2]}"/><text x="80" y="259" font-family="Arial,sans-serif" font-size="17" font-weight="800" fill="#16233b">{html.escape(category.upper())}</text>
<rect y="610" width="1200" height="65" fill="#0b1b32" opacity=".88"/><text x="65" y="649" font-family="Arial,sans-serif" font-size="20" fill="#d6e5f7">RADIO ROMÂNII DIN ITALIA · ILUSTRAȚIE EDITORIALĂ</text>
</svg>'''

def fill_missing_images(items):
    OUT.mkdir(parents=True, exist_ok=True)
    used = set()
    count = 0
    for item in items:
        if item.get("image"):
            continue
        identity = str(item.get("url") or item.get("title") or "")
        digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]
        path = OUT / f"rdi-auto-{digest}.svg"
        rendered = make_svg(item)
        if not path.exists() or path.read_text(encoding="utf-8") != rendered:
            path.write_text(rendered, encoding="utf-8")
            count += 1
        used.add(path.name)
        item["image"] = "./" + path.as_posix()
        item["imageType"] = "editorial-illustration"
        item["imageAttribution"] = "Ilustrație editorială RDI (nu este fotografie a evenimentului)"
    for path in OUT.glob("rdi-auto-*.svg"):
        if path.name not in used:
            path.unlink()
    print(f"Ilustrații RDI noi: {count}; active: {len(used)}")
