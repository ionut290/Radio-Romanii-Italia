#!/usr/bin/env python3
"""Discover upcoming diaspora-related events from public news RSS; publish only dated leads."""
import datetime as dt, email.utils, html, json, pathlib, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"events-auto.json"
TODAY=dt.datetime.now(dt.timezone.utc).date()
SEARCHES=[
 '"eveniment" "români" "Italia" concert festival',
 '"comunitatea românească" "Italia" eveniment',
 '"diaspora românească" "Italia" festival',
 '"Romania" "festival" "Italia" comunità',
 '"interculturale" "romeni" "Italia" evento',
]
CITIES={"roma":"Lazio","milano":"Lombardia","torino":"Piemonte","bologna":"Emilia-Romagna","firenze":"Toscana","napoli":"Campania","palermo":"Sicilia","catania":"Sicilia","verona":"Veneto","padova":"Veneto","venezia":"Veneto","brescia":"Lombardia","bergamo":"Lombardia","genova":"Liguria","parma":"Emilia-Romagna","modena":"Emilia-Romagna","rimini":"Emilia-Romagna","ravenna":"Emilia-Romagna","perugia":"Umbria","pisa":"Toscana","trento":"Trentino-Alto Adige","bolzano":"Trentino-Alto Adige","udine":"Friuli-Venezia Giulia","trieste":"Friuli-Venezia Giulia","bari":"Puglia","lecce":"Puglia","ancona":"Marche","pescara":"Abruzzo","alcomo":"Sicilia","alcamo":"Sicilia"}
MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12,"ianuarie":1,"februarie":2,"martie":3,"aprilie":4,"mai":5,"iunie":6,"iulie":7,"august":8,"septembrie":9,"octombrie":10,"noiembrie":11,"decembrie":12}
EVENT_WORDS=re.compile(r"festival|concert|spectacol|eveniment|expoziți|întâlnir|sărbăto|târg|conferin|manifestazion|spettacol|incontro|mostra|evento",re.I)
DIASPORA=re.compile(r"rom[aâ]n|romeni|romania|diaspora|intercultural|multicultural|balcan|moldov",re.I)
def event_date(text):
    candidates=[]
    for m in re.finditer(r"(?<!\d)([0-3]?\d)[ /.-]([01]?\d)[ /.-](20\d{2})(?!\d)",text):
        try:candidates.append(dt.date(int(m[3]),int(m[2]),int(m[1])))
        except ValueError:pass
    for m in re.finditer(r"(?<!\d)([0-3]?\d)\s+(?:"+ "|".join(MONTHS)+r")\s+20\d{2}",text,re.I):
        p=m.group().lower().split()
        try:candidates.append(dt.date(int(p[2]),MONTHS[p[1]],int(p[0])))
        except (ValueError,KeyError):pass
    valid=sorted(d for d in candidates if TODAY<=d<=TODAY+dt.timedelta(days=180))
    return valid[0].isoformat() if valid else None
def clean(s):return re.sub(r"\s+"," ",html.unescape(re.sub("<[^>]+>"," ",s or ""))).strip()
old=[]
if OUT.exists():
    try:old=json.loads(OUT.read_text(encoding="utf-8")).get("events",[])
    except (ValueError,OSError):pass
items={x["url"]:x for x in old if x.get("date","")>=TODAY.isoformat() and x.get("url")}
for query in SEARCHES:
    url="https://news.google.com/rss/search?"+urllib.parse.urlencode({"q":query,"hl":"it","gl":"IT","ceid":"IT:it"})
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; DiasporaEvents/1.0)"})
        with urllib.request.urlopen(req,timeout=20) as resp:root=ET.fromstring(resp.read(2_000_000))
    except Exception as exc:
        print("Source unavailable:",str(exc)[:150]);continue
    for item in root.findall(".//item"):
        title=clean(item.findtext("title"));description=clean(item.findtext("description"))
        text=title+" "+description
        link=(item.findtext("link") or "").strip()
        if not link.startswith("https://") or not EVENT_WORDS.search(text) or not DIASPORA.search(text):continue
        date=event_date(text)
        if not date:continue
        city=next((name.title() for name in CITIES if re.search(r"\b"+re.escape(name)+r"\b",text,re.I)),None)
        if not city:continue
        try:published=email.utils.parsedate_to_datetime(item.findtext("pubDate"))
        except (TypeError,ValueError):continue
        if (dt.datetime.now(dt.timezone.utc)-published.astimezone(dt.timezone.utc)).days>45:continue
        source=clean(item.findtext("source")) or "Sursă publică"
        items[link]={"title":title[:160],"date":date,"city":city,"region":CITIES[city.lower()],"source":source[:90],"url":link,"description":description[:450],"published":published.date().isoformat()}
events=sorted(items.values(),key=lambda x:(x["date"],x["city"],x["title"]))[:80]
OUT.write_text(json.dumps({"updated":TODAY.isoformat(),"events":events},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Upcoming event leads:",len(events))
