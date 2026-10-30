"""Conservative, reproducible matching of RDI stock photos to news stories.

A broad category (Italia, lavoro, politica, economia) is not enough to assign
a photorealistic stock scene. We need a concrete subject shared by the headline
and the human-written photo description. No invented event photography.
"""
import re
import unicodedata
from pathlib import PurePosixPath


def fold(value):
    value = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(c for c in value if not unicodedata.combining(c))


# (article title/short summary, library photo description).
# Scene-specific concepts; intentionally no generic "economy / politics / Italy".
SCENES = {
    "football": (r"\b(calcio|fotbal|football|serie a|fiorentina|atalanta|juventus|napoli|inter milan|ac milan|lazio|scudetto)\b", r"\bcalcio\b"),
    "volleyball": (r"\b(pallavolo|volei|volleyball)\b", r"\bpallavolo\b"),
    "cycling": (r"\b(ciclismo|ciclisti|ciclista|ciclism|ciclist)\b", r"\b(ciclisti|ciclismo)\b"),
    "running": (r"\b(maratona|maraton|corsa podistica|alergare|atletica)\b", r"\bcorsa\b"),
    "consulate": (r"\b(consolat|consular|ambasad|pasaport|passaport|econsulat)\w*", r"\b(consol|ambasciat)\w*"),
    "parliament": (r"\b(parlament|parlamento|camera dei deputati|senato|senat|seduta parlamentare)\w*", r"\b(parlament|aula parlamentare)\w*"),
    "civic_service": (r"\b(comune|municipio|primaria|sportello comunale|anagrafe|servizi comunali)\b", r"\b(comunal|municipio|sportello pubblico)\w*"),
    "community_event": (r"\b(festa di quartiere|festival comunit|evento associativ|asociati|associazion|intalnire comunit)\w*", r"\b(evento|festa|associativ|associazion|incontro)\w*"),
    "volunteering": (r"\b(volontari|volontarie|volontariato|voluntariat|voluntari|voluntarii|voluntarilor|volunteering)\w*", r"\b(volontari|solidale|donazioni)\w*"),
    "food_aid": (r"\b(pacchi alimentar|banco alimentar|dispensa solidale|aiuti alimentar|donazioni alimentari)\w*", r"\b(pacchi alimentari|dispensa solidale|generi alimentari)\b"),
    "language_school": (r"\b(corso di italiano|corsi di lingua|lingua italiana|invata italiana|cursuri de italiana|cursuri de limba)\b", r"\b(lingua italiana|italiano|corso di lingua)\b"),
    "university": (r"\b(universit|facultat|ateneo|studenti universitari)\w*", r"\b(universitar|universit)\w*"),
    "school": (r"\b(scuola|scoala|scuole|insegnant|profesor|liceo|scoli)\w*", r"\b(scuola|insegnante|aula|lezione)\w*"),
    "job_training": (r"\b(formazion professionale|corsi professional|calificare profesional|formare profesional)\w*", r"\b(formazione professionale|laboratorio professionale)\b"),
    "health_doctor": (r"\b(medico di base|medic de familie|medici di famiglia|visita medica)\b", r"\b(medico di base|medico|ambulatorio)\b"),
    "pharmacy": (r"\b(farmaci|farmacie|farmacia|farmacii|farmacist|medicinali)\w*", r"\b(farmacist|farmacia)\w*"),
    "hospital": (r"\b(ospedal|spital|ricover|sanitar|infermier|asistent medical)\w*", r"\b(ospedal|infermier|personale sanitario)\w*"),
    "physiotherapy": (r"\b(fisioterap|riabilitaz|recuperare medicala)\w*", r"\b(fisioterap)\w*"),
    "elder_care": (r"\b(asistenta batrani|assistenza domiciliare|assistenza agli anziani|cura degli anziani|badant|ingrijire la domiciliu)\w*", r"\b(anziano|anziana|assistenza domiciliare)\w*"),
    "train": (r"\b(treno|treni|feroviar|ferrovi|trenurile|trenul|trenuri|stazione ferroviaria)\w*", r"\b(treno|ferroviar|banchina ferroviaria|stazione ferroviaria)\w*"),
    "bus": (r"\b(autobus|bus urbano|trasporto pubblico locale|autobuz|autobuze)\b", r"\b(autobus|autobuz)\w*"),
    "airport": (r"\b(aeroporto|aeroport|terminal aeroportual|aeroportuar)\w*", r"\b(aeroport|terminal aeroportuale)\w*"),
    "ferry": (r"\b(traghetto|traghetti|feribot|vapor de pasageri)\b", r"\b(traghetto|porto adriatico)\b"),
    "taxi": (r"\b(taxi|tassisti|tassista)\b", r"\b(taxi|tassista)\b"),
    "roadworks": (r"\b(lavori stradali|manutenzione stradale|strada chiusa per lavori|santiere stradale)\b", r"\b(manutenzione stradale|strada di montagna)\b"),
    "rain": (r"\b(pioggia|piogge|ploaie|precipitazion|allerta meteo per pioggia)\w*", r"\b(pioggia|meteorologiche)\b"),
    "drought": (r"\b(siccita|seceta|lipsa apei|carenza idrica)\b", r"\b(siccita)\b"),
    "recycling": (r"\b(ricicl|raccolta differenziata|colectare selectiva|rifiuti|deseuri)\w*", r"\b(rifiuti|raccolta differenziata)\w*"),
    "river": (r"\b(fiume|fluvio|raul|inquinamento delle acque)\b", r"\b(fiume)\b"),
    "green_care": (r"\b(potatura|potature|giardiniere|parchi pubblici|verde urbano|alberi in parco|ingrijire arbori)\b", r"\b(parco|giardiniera|alberi)\b"),
    "work_construction": (r"\b(cantiere edile|edilizia|edili|costruzioni|muncitori in constructii|sicurezza in cantiere)\b", r"\b(edile|cantiere)\b"),
    "warehouse": (r"\b(magazzin|logistic|depozit|merci in magazzino)\w*", r"\b(magazzin|logistic|scorte)\w*"),
    "courier": (r"\b(corriere|corrieri|consegna pacchi|curier|curieri)\b", r"\b(corriere|consegna)\b"),
    "farm": (r"\b(agricolt|raccolta ortaggi|serra|fermieri|campi coltivati)\w*", r"\b(serra|agricolt|ortaggi)\w*"),
    "bakery": (r"\b(panetter|panific|fornai|brutarii)\w*", r"\b(panetter|panific)\w*"),
    "restaurant": (r"\b(ristorant|cucina professionale|cuochi|bucatar|ristorazion)\w*", r"\b(ristorante|cucina)\b"),
    "market_prices": (r"\b(prezzi alimentari|prezzi al mercato|caro spesa|preturi alimentare|inflazione alimentare)\b", r"\b(prezzi al mercato|confrontano i prezzi)\b"),
    "family_budget": (r"\b(bilancio familiare|spese domestiche|bugetul familiei|economia domestica)\b", r"\b(spese domestiche|conti di famiglia)\b"),
    "lawyer": (r"\b(avvocat|avocat|consulenza legale|assistenza legale)\w*", r"\b(avvocat|legale)\w*"),
    "court": (r"\b(tribunal|giudice|judecator|sentenza|processo giudiziario)\w*", r"\b(tribunale|giudice)\w*"),
    "police": (r"\b(polizia|politie|carabinieri|agenti di polizia)\b", r"\b(polizia|agenti)\b"),
    "cybersecurity": (r"\b(cyber|hacker|informatica|sicurezza informatica|attacchi informatici)\w*", r"\b(sicurezza informatica|sistemi informatici)\b"),
    "robotics": (r"\b(robot|robotica|robotici|automatizari industriale)\w*", r"\b(robot)\w*"),
    "smartphone": (r"\b(smartphone|telefono cellulare|telefon mobil|aplicazione per anziani)\b", r"\b(smartphone)\b"),
}

# A staged portrait/photo is especially misleading in reports of actual harm.
SENSITIVE = re.compile(
    r"\b(mort[ioe]|morti|decedat\w*|ucis\w*|killed|dead|"
    r"accident\w*|inciden\w* grave|precipitat\w*|prabusit\w*|"
    r"elicopter\w*|elicotter\w*|esplos\w*|exploz\w*|"
    r"bombard\w*|atac\w* armat\w*|attacc\w* armat\w*|"
    r"guerra|razboi|armed conflict|sparator\w*|teroris\w*|"
    r"arrestat\w*|arestat\w*|omicid\w*|assassinat\w*|"
    r"disastr\w*|strage|masacr\w*|deces\w*|murit|a murit|stins din viata|"
    r"incendi\w*|retinut\w*|retinuta|arestat\w*|furt\w*|furto|scompar\w*|"
    r"abus\w*|aggress\w*|violenz\w*)\b"
)


def choose_relevant_photo(item, library, already_used):
    """Return photo metadata only for an explicitly supported concrete subject.

    Do not use a category alone, a hash/random pick, or previous unreviewed
    assignments. A sourced publisher image is handled by the caller.
    """
    title = fold(item.get("title"))
    summary = fold(item.get("summary"))[:350]
    if not title or SENSITIVE.search(title + " " + summary):
        return None
    # A generic university/office scene is not a depiction of AI avatars.
    if re.search(r"\b(avatar\w*|intelligenza artificiale|inteligenta artificiala|artificial intelligence|chatgpt)\b", title):
        return None

    title_subjects = {
        key for key, (story, _photo) in SCENES.items()
        if re.search(story, title)
    }
    # Require headline evidence; long article bodies often mention incidental subjects.
    if not title_subjects:
        return None
    summary_subjects = {
        key for key, (story, _photo) in SCENES.items()
        if re.search(story, summary)
    }
    options = []
    for category, entries in library.items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("reusable") is False:
                continue
            path = str(entry.get("image") or "")
            if not path or path in already_used:
                continue
            filename = PurePosixPath(path).name
            # Generic category covers hide subject mismatches; prefer an honest SVG.
            if filename.startswith("ai-"):
                continue
            description = fold(entry.get("description"))
            photo_subjects = {
                key for key, (_story, photo) in SCENES.items()
                if re.search(photo, description)
            }
            shared = title_subjects & photo_subjects
            if not shared:
                continue
            # Don't portray a story about one sport with photography of another.
            if category == "sports" and not (shared & {"football", "volleyball", "cycling", "running"}):
                continue
            # Description-specific ranking; deterministic, not random or category-only.
            score = sum(5 + (2 if tag in summary_subjects else 0) for tag in shared)
            # Prefer scenes with few competing unrelated subjects.
            score -= len(photo_subjects - title_subjects)
            if "football" in shared and re.search(r"\b(partita|partida|match|gol|serie a|campionato)\b", title):
                score += 3 if "partita" in description else -2 if "allenamento" in description else 0
            options.append((score, filename, entry))
    if not options:
        return None
    options.sort(key=lambda pair: (-pair[0], pair[1]))
    return options[0][2]
