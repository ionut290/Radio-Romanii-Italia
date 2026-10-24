#!/usr/bin/env python3
"""Contextual country / institution / topic for RDI social-image headlines.

Keep site news sections unchanged. These labels only describe social cards.
Prefer what the HEADLINE is about to the country of the news publisher.
A validated editorial social_label can always override the heuristic.
"""
import re
import unicodedata

LABELS = {
    "eu": ("UNIONE EUROPEA", "UNIUNEA EUROPEANĂ"),
    "europe": ("EUROPA", "EUROPA"),
    "usa": ("AMERICA", "AMERICA"),
    "latin_america": ("AMERICA LATINA", "AMERICA LATINĂ"),
    "italy": ("ITALIA", "ITALIA"),
    "romania": ("ROMANIA", "ROMÂNIA"),
    "ukraine": ("UCRAINA", "UCRAINA"),
    "russia": ("RUSSIA", "RUSIA"),
    "france": ("FRANCIA", "FRANȚA"),
    "germany": ("GERMANIA", "GERMANIA"),
    "spain": ("SPAGNA", "SPANIA"),
    "uk": ("REGNO UNITO", "REGATUL UNIT"),
    "moldova": ("MOLDAVIA", "REPUBLICA MOLDOVA"),
    "china": ("CINA", "CHINA"),
    "japan": ("GIAPPONE", "JAPONIA"),
    "israel": ("ISRAELE", "ISRAEL"),
    "palestine": ("PALESTINA", "PALESTINA"),
    "turkey": ("TURCHIA", "TURCIA"),
    "iran": ("IRAN", "IRAN"),
    "india": ("INDIA", "INDIA"),
    "australia": ("AUSTRALIA", "AUSTRALIA"),
    "cuba": ("CUBA", "CUBA"),
    "world": ("MONDO", "MONDIAL"),
    "diaspora": ("DIASPORA", "DIASPORA"),
    "education": ("ISTRUZIONE", "EDUCAȚIE"),
    "health": ("SALUTE", "SĂNĂTATE"),
    "work": ("LAVORO", "MUNCĂ"),
    "economy": ("ECONOMIA", "ECONOMIE"),
    "technology": ("TECNOLOGIA", "TEHNOLOGIE"),
    "science": ("SCIENZA", "ȘTIINȚĂ"),
    "culture": ("CULTURA", "CULTURĂ"),
    "sport": ("SPORT", "SPORT"),
    "agriculture": ("AGRICOLTURA", "AGRICULTURĂ"),
    "environment": ("AMBIENTE", "MEDIU"),
    "weather": ("METEO", "METEO"),
    "transport": ("TRASPORTI", "TRANSPORTURI"),
    "justice": ("GIUSTIZIA", "JUSTIȚIE"),
    "events": ("EVENTI", "EVENIMENTE"),
    "politics": ("POLITICA", "POLITICĂ"),
    "news": ("NOTIZIE", "ȘTIRI"),
}

# Not publisher URLs: only the *content* determines the geographical label.
COUNTRIES = (
    ("latin_america", r"\b(?:america latina|america de sud|america del sud|america de sur)\b"),
    ("usa", r"\b(?:stati uniti|statelor unite|statele unite|statele unite ale americii|sua|usa|america|american[aoie]|americani|pentagon(?:ul)?|washington|new york|cia|fbi)\b"),
    ("romania", r"\b(?:romania|romaniei|romanesc(?:a|i|e)?|romane(?:sc|sti|asca)|romanilor|romanii|roman[ai]|bucuresti|cluj|iasi|timisoara|constanta|brasov)\b"),
    ("italy", r"\b(?:italia|italiei|italian[aoie]|italien[ioe]|italieni|roma|milano|napoli|torino|bologna|padova|sicilia|calabria|toscana|lombardia|piemonte|veneto|puglia|sardegna|firenz[ea]|genova|venezia|palermo|cassano all.ionio)\b"),
    ("ukraine", r"\b(?:ucraina|ucrain[eoia]|ucrainen[io]|ukraine|ukrain[ae]|kyiv|kiev|zelensk[yi]|oles[h]?ky)\b"),
    ("russia", r"\b(?:russia|russ[ioea]|rusesti|ruseasca|rusiei|rusia|ruse|rusi|moscova|mosca|kremlin(?:ul)?)\b"),
    ("france", r"\b(?:francia|frantei|franta|francez[ioae]|francezi|paris|parigi|parizieni|parisien[is])\b"),
    ("germany", r"\b(?:germania|germaniei|tedesc[aoih]|germani|german[ae]|baviera|bavarez[aei]|berlino|berlin)\b"),
    ("spain", r"\b(?:spagna|spania|spaniol[aei]|spagnol[aei]|madrid|barcellona|barcelona)\b"),
    ("uk", r"\b(?:regno unito|regatul unit|gran bretagna|marea britanie|britannic[aoie]|britanic[aoie]|londra|london|anglia|inghilterra)\b"),
    ("moldova", r"\b(?:republica moldova|moldova|moldove[ai]|chisinau)\b"),
    ("china", r"\b(?:cina|chinei|china|cinese|cinesi|chinez[aei]|pechino|beijing|xi jinping)\b"),
    ("japan", r"\b(?:giappone|japonia|japoniei|japonez[aei]|giappones[ei]|tokyo|tokio)\b"),
    ("israel", r"\b(?:israel|israelian[oi]|israelien[ei]|tel aviv|idf)\b"),
    ("palestine", r"\b(?:palestina|palestinei|palestines[ei]|palestinian[oi]|cisgiordania|west bank|gaza)\b"),
    ("turkey", r"\b(?:turchia|turcia|turciei|turc[hi]|erdogan|ankara|istanbul)\b"),
    ("iran", r"\b(?:iran|iranian[oi]|teheran|tehran)\b"),
    ("india", r"\b(?:india|indiei|indian[oi]|new delhi|mumbai)\b"),
    ("australia", r"\b(?:australia|australian[oi]|sydney|melbourne)\b"),
    ("cuba", r"\b(?:cuba|cubani|cubanez[ioae]|havana)\b"),
)
# EU institutions, not every mention of the European continent or a non-EU
# government's negotiations with the EU.
EU_INSTITUTIONS = (
    r"\b(?:unione europea|uniunea europeana|uniunii europene|european union)\b",
    r"\b(?:comisia europeana|comisiei europene|commissione europea|commissione ue|european commission)\b",
    r"\b(?:parlamentul european|parlamentului european|parlamento europeo|consiglio europeo|consiliul european)\b",
    r"\b(?:diplomatia europeana|diplomatiei europene|diplomaz(?:ia|ie) europe[ao]|diplomazia ue|politica externa a ue)\b",
    r"\b(?:banca centrala europeana|bce|ecb|presedinta comisiei|presedintele comisiei|europarlamentar[ie])\b",
)
EU_LEAD = re.compile(r"^(?:l[’']?|la |il |a |in |din )?(?:ue|eu)\b", re.I)
TOPICS = (
    ("education", r"\b(?:scoala|scoli|scolile|scolara|scolar|elevi|elevii|studenti|studentii|studentes[se]|scuol[ae]|istruzione|educatie|educatia|educazione|invatamant|universita|universitate|universitati|profesor[ei]|professori)\b"),
    ("health", r"\b(?:sanatate|sanatatii|sanita|salute|spital[eiul]*|ospedal[ei]|medic[io]|cancer|pacient[ei]|vaccin[oi]|vaccinur[ei]|farmaci[ei]|malattia|boala|epidemia)\b"),
    ("work", r"\b(?:lavoro|lavoratori|lavoratore|lavorativ[oaie]|munca|muncii|muncitor[io]|stipendi[oi]|salari[ouil]|contract de munca|sindacat[oi]|scioper[oi]|greva|greve|occupazione)\b"),
    ("economy", r"\b(?:economia|economiei|economic[oaie]|inflazione|inflatia|prezz[oi]|pretur[ei]|tass[ae]|impozit[ei]|bilancio|buget|finanz[ae]|finant[ae]|investi[tz]|bors[ae]|pension[ei]|pensii|euro|benzina|diesel)\b"),
    ("technology", r"\b(?:tecnologia|tehnologie|intelligenza artificiale|inteligenta artificiala|\bai\b|informatica|informatic[ae]|software|robot[uii]|cyber|cibernetic|telefon[oi]|smartphone|internet|spazio|satellit[ei])\b"),
    ("science", r"\b(?:scienza|stiinta|stiintific[ae]|scientific[oi]|ricerca|cercetare|astronom[ioi]|cosmic[oi]|universo|galax|galaxia|galassia)\b"),
    ("culture", r"\b(?:cultura|culturale|cultural[ae]|concert[oi]|muzic[aa]|musica|film|teatro|teatrul|opera|festival|actor[ie]|attric[ei]|artist[ai]|artisti|letteratura|scrittur[ae]|cart[ei]|libro|libr[oi])\b"),
    ("sport", r"\b(?:sport|fotbal|calcio|champions|mondial[ei]|grand prix|formula 1|\bf1\b|motogp|moto gp|basket|tenis|tennis|olimpiad[ae]|maraton[ae]|gol|partita)\b"),
    ("agriculture", r"\b(?:agricoltura|agricultura|agricol[ae]|fermier[oi]|ferma|coltivazion[ei]|recolta|ortofrutta|grano|grau|campi|culturilor|pac)\b"),
    ("environment", r"\b(?:ambiente|mediul|ecologi[ae]|climatic[aohe]|clima|incalzirea globala|riscaldamento globale|inquinament[oi]|poluare|emission[ei]|emisii)\b"),
    ("weather", r"\b(?:meteo|ceata|nebbia|temporale|uragan[oi]|furtun[ai]|allert[ae] meteorologic[ae]|precipitatii|ninsoar[ei]|nevicat[ae]|canicula|ondata di calore|caldura)\b"),
    ("transport", r"\b(?:transport[oi]|trasport[oi]|tren[oi]|treni|ferrov[ai]|autostrada|autostrada|autostraz[ai]|aeroport[oi]|zborur[ei]|vol[oi]|traffico|trafic|circolazione)\b"),
    ("justice", r"\b(?:giustizia|justitie|tribunal[eiul]*|judecator[ei]|magistrat[oi]|procura|arrestat[oi]|condamnat[oi]|condamnare|prison|carcer[ei])\b"),
    ("politics", r"\b(?:politica|politic[ae]|elezion[ei]|aleger[ei]|parlamentar[ie]|govern[oi]|guvern[ul]*|ministr[oiu]|president[ei]|presedint[ei]|partit[oiul]*)\b"),
)
EU_REGEX = [re.compile(expr, re.I) for expr in EU_INSTITUTIONS]
COUNTRY_REGEX = [(k, re.compile(expr, re.I)) for k, expr in COUNTRIES]
TOPIC_REGEX = [(k, re.compile(expr, re.I)) for k, expr in TOPICS]

def normalized(s):
    s = unicodedata.normalize("NFKD", str(s or "").replace("’", "'")).lower()
    return "".join(ch for ch in s if not unicodedata.combining(ch))

def language_for(item, headline, lang=None):
    if lang in ("ro", "it"):
        return lang
    raw = str(headline or "")
    if re.search(r"[ăâîșțĂÂÎȘȚ]", raw):
        return "ro"
    if re.search(r"\b(?:della|degli|dell'|l'|sul|nel|nella|dopo|italiana|italiano|italia|con|per)\b", raw, re.I):
        return "it"
    return "ro" if normalized(item.get("category")) in ("romania", "diaspora", "stiri din redactie") else "it"

def _mentions(patterns, text):
    matches = [(match.start(), key) for key, pattern in patterns for match in pattern.finditer(text)]
    matches.sort(key=lambda x: x[0])
    return matches

def identify_subject(item, headline=None, lang=None):
    headline = str(headline or item.get("title") or "")
    language = language_for(item, headline, lang)
    explicit = str(item.get("social_label") or item.get("social_category") or "").strip()
    if explicit:
        return explicit[:36].upper()
    title = normalized(headline)
    brief = normalized(str(item.get("summary") or item.get("description") or "")[:400])
    section = normalized(item.get("category"))
    def result(key):
        return LABELS[key][0 if language == "it" else 1]
    if not title:
        return result("news")
    if item.get("date") and item.get("city"):
        return result("events")

    # EU is the institution acting, not just an incidental destination of
    # another country's policy. e.g. "Șefa diplomației europene ..." -> EU.
    if EU_LEAD.search(title) or any(p.search(title) for p in EU_REGEX):
        return result("eu")

    title_countries = _mentions(COUNTRY_REGEX, title)
    if title_countries:
        countries = {key for _, key in title_countries}
        if section == "diaspora" and {"italy", "romania"}.issubset(countries):
            return result("diaspora")
        return result(title_countries[0][1])

    # European region != European Union. The latter requires institution.
    if re.search(r"\b(?:europa|europe[ao]|europen[ei]|europei|european[ae])\b", title):
        return result("europe")

    title_topics = _mentions(TOPIC_REGEX, title)
    if title_topics:
        # First clear subject in the headline. Avoid the generic fall-back
        # category (often simply the publisher's country).
        return result(title_topics[0][1])

    # Headline may omit the location, which is then explained in the summary
    # ("Alpi Bavaresi ... Germania"). Avoid guessing from the publisher name.
    summary_places = _mentions(COUNTRY_REGEX, brief)
    if summary_places:
        return result(summary_places[0][1])
    if any(p.search(brief) for p in EU_REGEX) and not summary_places:
        return result("eu")
    if section in ("italia", "italy"):
        return result("italy")
    if section in ("romania", "romania"):
        return result("romania")
    if section == "diaspora":
        return result("diaspora")
    if section in ("evenimente", "eventi"):
        return result("events")
    if section in ("sti ri din redactie", "stiri din redactie"):
        return result("news")
    return result("news")
