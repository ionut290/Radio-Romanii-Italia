#!/usr/bin/env python3
"""Discover upcoming diaspora-related events from public news RSS; publish only dated leads."""
import datetime as dt, email.utils, html, json, pathlib, re, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from html.parser import HTMLParser
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/"events-auto.json"
TODAY=dt.datetime.now(dt.timezone.utc).date()
SEARCHES=[
 '"români" "Italia" "festival" "2026"',
 '"romeni" "Italia" "evento" "2026"',
 '"comunitatea românească" "Italia" eveniment',
 '"diaspora românească" "Italia" festival',
 '"Romania" "festival" "Italia" comunità',
 '"interculturale" "romeni" "Italia" evento',
 'site:icr.ro Italia evenimente 2026',
 'site:accademiadiromania.it eventi 2026',
 'site:ro.wikipedia.org festival românesc Italia 2026',
 'site:romania-actualitati.ro Italia diaspora eveniment 2026',
 'site:ambasada-romaniei.it evenimente culturale',
 '"romeni" "festa" "Roma" 2026',
 '"romeni" "festival" "Torino" 2026',
 '"români" "eveniment" "Milano" 2026',
 '"români" "eveniment" "Bologna" 2026',
 '"cultura romena" "Italia" "ottobre" 2026',
 '"cultura romena" "Italia" "novembre" 2026',
 '"Balkanika" festival 2026 Italia',
]

# Broad coverage by locality and event type, including multilingual searches.
SEARCHES += [
    f'"cultura romena" "{city}" eventi 2026'
    for city in ("Roma","Milano","Torino","Bologna","Firenze","Venezia","Napoli","Verona","Padova","Bari","Genova","Palermo","Brescia","Perugia")
]
SEARCHES += [
    f'"comunitatea romaneasca" "{city}" evenimente 2026'
    for city in ("Roma","Milano","Torino","Bologna","Firenze","Venezia","Napoli","Verona","Padova","Bari")
]
SEARCHES += [
    '"festival românesc" Italia 2026',
    '"festival romeno" Italia ottobre novembre dicembre 2026',
    '"concerto romeno" Italia 2026',
    '"teatro romeno" Italia 2026',
    '"cinema romeno" Italia 2026',
    '"mostra artisti romeni" Italia 2026',
    '"Ziua Nationala a Romaniei" Italia 2026 eveniment',
    '"1 decembrie" "români" "Italia" 2026',
    '"festival Propatria" Roma 2026 programma',
    '"Accademia di Romania" Roma eventi ottobre 2026',
    '"Istituto Romeno di Cultura" Venezia mostra 2026',
    'site:icr.ro/venetia/evenimente/ 2026',
    'site:icr.ro/roma/evenimente/ 2026',
    'site:accademiadiromania.it/ 2026 eventi',
    '"associazione romeni" "Italia" evento 2026',
    '"comunità moldava" Italia evento 2026',
    '"festival interculturale" "romena" Italia 2026',
]
CITIES={"roma":"Lazio","milano":"Lombardia","torino":"Piemonte","bologna":"Emilia-Romagna","firenze":"Toscana","napoli":"Campania","palermo":"Sicilia","catania":"Sicilia","verona":"Veneto","padova":"Veneto","venezia":"Veneto","brescia":"Lombardia","bergamo":"Lombardia","genova":"Liguria","parma":"Emilia-Romagna","modena":"Emilia-Romagna","rimini":"Emilia-Romagna","ravenna":"Emilia-Romagna","perugia":"Umbria","pisa":"Toscana","trento":"Trentino-Alto Adige","bolzano":"Trentino-Alto Adige","udine":"Friuli-Venezia Giulia","trieste":"Friuli-Venezia Giulia","bari":"Puglia","lecce":"Puglia","ancona":"Marche","pescara":"Abruzzo","alcamo":"Sicilia"}
MONTHS={"gennaio":1,"febbraio":2,"marzo":3,"aprile":4,"maggio":5,"giugno":6,"luglio":7,"agosto":8,"settembre":9,"ottobre":10,"novembre":11,"dicembre":12,"ianuarie":1,"februarie":2,"martie":3,"aprilie":4,"mai":5,"iunie":6,"iulie":7,"august":8,"septembrie":9,"octombrie":10,"noiembrie":11,"decembrie":12}
EVENT_WORDS=re.compile(r"festival|concert|spectacol|eveniment|expoziți|întâlnir|sărbăto|târg|conferin|manifestazion|spettacol|incontro|mostra|evento",re.I)
DIASPORA=re.compile(r"rom[aâ]n|romeni|romania|române|români|romanesc|românesc|romeno|romena|romeni|moldov",re.I)
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

class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts=[]
        self.skip=0
    def handle_starttag(self,tag,attrs):
        if tag in ("script","style"):self.skip+=1
        if tag in ("p","h1","h2","h3","li","time","br"):self.parts.append(" ")
    def handle_endtag(self,tag):
        if tag in ("script","style") and self.skip:self.skip-=1
    def handle_data(self,data):
        if not self.skip:self.parts.append(data)
def page_details(url):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!="https" or not parsed.hostname or parsed.hostname in ("news.google.com","www.google.com","google.com"):return ""
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; DiasporaEvents/1.1)"})
        with urllib.request.urlopen(req,timeout=8) as resp:
            if "text/html" not in resp.headers.get("Content-Type",""):return ""
            body=resp.read(350_000).decode("utf-8","replace")
        parser=PageText();parser.feed(body)
        return clean(" ".join(parser.parts))[:18000]
    except Exception as exc:
        print("Page unavailable:",parsed.hostname,str(exc)[:70])
        return ""

class PreviewImage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image=""
    def handle_starttag(self,tag,attrs):
        if tag!="meta" or self.image:return
        a=dict(attrs)
        if a.get("property","").lower() in ("og:image","og:image:url") or a.get("name","").lower()=="twitter:image":
            u=html.unescape(a.get("content",""))
            if u.startswith("https://"):self.image=u

def image_from_rss(item):
    for node in item.iter():
        local=node.tag.split("}")[-1].lower()
        url=node.attrib.get("url","")
        kind=node.attrib.get("type","")
        if local in ("thumbnail","content","enclosure") and url.startswith("https://"):
            if local=="thumbnail" or kind.startswith("image/") or re.search(r"\.(?:jpg|jpeg|png|webp)(?:[?#]|$)",url,re.I):
                return url
    raw=item.findtext("description") or ""
    match=re.search(r'<img[^>]+src=["\\\'](https://[^"\\\']+)',raw,re.I)
    return html.unescape(match.group(1)) if match else ""

def image_from_page(url):
    parsed=urllib.parse.urlparse(url)
    if parsed.scheme!="https" or parsed.hostname in ("news.google.com","www.google.com","google.com"):
        return ""
    try:
        req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; RadioRomaniiEvents/1.0)"})
        with urllib.request.urlopen(req,timeout=7) as resp:
            if "text/html" not in resp.headers.get("Content-Type",""):return ""
            page=resp.read(180_000).decode("utf-8","replace")
        parser=PreviewImage();parser.feed(page)
        return parser.image
    except Exception as exc:
        print("Event preview unavailable:",parsed.hostname,str(exc)[:70])
        return ""

old=[]
if OUT.exists():
    try:old=json.loads(OUT.read_text(encoding="utf-8")).get("events",[])
    except (ValueError,OSError):pass
items={x["url"]:x for x in old if x.get("endDate",x.get("date",""))>=TODAY.isoformat() and x.get("url")}
seen_count=0
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
        details=""
        date=event_date(text)
        city=next((name.title() for name in CITIES if re.search(r"\b"+re.escape(name)+r"\b",text,re.I)),None)
        if not date or not city:
            details=page_details(link)
            if details and EVENT_WORDS.search(details) and DIASPORA.search(details):
                date=date or event_date(details)
                city=city or next((name.title() for name in CITIES if re.search(r"\b"+re.escape(name)+r"\b",details,re.I)),None)
        if not date or not city:continue
        if not DIASPORA.search(text+" "+(details if "details" in locals() else "")):continue
        try:published=email.utils.parsedate_to_datetime(item.findtext("pubDate"))
        except (TypeError,ValueError):continue
        if (dt.datetime.now(dt.timezone.utc)-published.astimezone(dt.timezone.utc)).days>120:continue
        source=clean(item.findtext("source")) or "Sursă publică"
        seen_count+=1
        items[link]={"image":image_from_rss(item) or items.get(link,{}).get("image",""),"title":title[:160],"date":date,"city":city,"region":CITIES[city.lower()],"source":source[:90],"url":link,"description":description[:450],"published":published.date().isoformat()}

# Official cultural institution calendars. Only structured Event entries with explicit
# dates and an Italian city are accepted; an inaccessible site is simply skipped.
OFFICIAL_PAGES=[
    ("ICR Veneția – evenimente","https://www.icr.ro/venetia/evenimente"),
    ("ICR Roma – evenimente","https://www.icr.ro/roma/evenimente"),
    ("Institutul Cultural Român – Roma","https://www.icr.ro/roma"),
    ("Institutul Cultural Român – Veneția","https://www.icr.ro/venetia"),
    ("Accademia di Romania in Roma","https://www.accademiadiromania.it/"),
]
class EventHTML(HTMLParser):
    def __init__(self):
        super().__init__();self.scripts=[];self.links=[];self.in_json=False;self.buffer=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if tag=="script" and "ld+json" in attrs.get("type","").lower():
            self.in_json=True;self.buffer=[]
        if tag=="a" and attrs.get("href"):self.links.append(attrs["href"])
    def handle_data(self,data):
        if self.in_json:self.buffer.append(data)
    def handle_endtag(self,tag):
        if tag=="script" and self.in_json:
            self.scripts.append("".join(self.buffer));self.in_json=False
def download_html(url):
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; RadioRomaniiEvents/1.0)"})
    with urllib.request.urlopen(req,timeout=10) as response:
        if "text/html" not in response.headers.get("Content-Type",""):return ""
        return response.read(600_000).decode("utf-8","replace")
def json_events(value):
    if isinstance(value,list):
        for item in value:yield from json_events(item)
    elif isinstance(value,dict):
        typ=value.get("@type",[])
        if isinstance(typ,str):typ=[typ]
        if any(str(t).lower().endswith("event") for t in typ):yield value
        for key in ("@graph","mainEntity","itemListElement"):
            if key in value:yield from json_events(value[key])
def official_events():
    count=0
    for source,homepage in OFFICIAL_PAGES:
        try:
            page=download_html(homepage)
            parser=EventHTML();parser.feed(page)
            base=urllib.parse.urlparse(homepage)
            candidates=[(homepage,parser)]
            # Inspect a small number of same-host event links, without spidering entire sites.
            urls=[]
            for href in parser.links:
                u=urllib.parse.urljoin(homepage,href);p=urllib.parse.urlparse(u)
                if p.scheme=="https" and p.hostname==base.hostname and re.search(r"eveniment|event|calendar|program|festival|concert|spectacol|manifestazion",p.path,re.I) and u not in urls:urls.append(u)
            for url in urls[:8]:
                try:
                    sub=EventHTML();sub.feed(download_html(url));candidates.append((url,sub))
                except Exception as exc:print("Official subpage unavailable:",str(exc)[:80])
            for page_url,parsed in candidates:
                for raw in parsed.scripts:
                    try:objects=list(json_events(json.loads(raw)))
                    except (ValueError,TypeError):continue
                    for event in objects:
                        name=clean(str(event.get("name","")))
                        start=str(event.get("startDate",""))[:10]
                        try:event_day=dt.date.fromisoformat(start)
                        except ValueError:continue
                        if not TODAY<=event_day<=TODAY+dt.timedelta(days=180):continue
                        location=event.get("location",{})
                        if isinstance(location,list):location=location[0] if location else {}
                        if isinstance(location,str):location={"name":location}
                        if not isinstance(location,dict):continue
                        address=location.get("address",{})
                        if isinstance(address,str):address={"streetAddress":address}
                        if not isinstance(address,dict):address={}
                        place=" ".join(str(x or "") for x in (location.get("name"),address.get("addressLocality"),address.get("streetAddress")))
                        city=next((c.title() for c in CITIES if re.search(r"\b"+re.escape(c)+r"\b",place,re.I)),None)
                        if not city or not name:continue
                        link=event.get("url") or page_url
                        if not isinstance(link,str) or not link.startswith("https://"):link=page_url
                        description=clean(str(event.get("description","")))[:450]
                        if not DIASPORA.search(name+" "+description+" "+source):continue
                        items[link]={"image":event.get("image") if isinstance(event.get("image"),str) and event["image"].startswith("https://") else items.get(link,{}).get("image",""),"title":name[:160],"date":start,"city":city,"region":CITIES[city.lower()],"source":source,"url":link,"description":description,"published":TODAY.isoformat()}
                        count+=1
        except Exception as exc:print("Official source unavailable:",source,str(exc)[:130])
    print("Official structured events:",count)

official_events()
events=sorted(items.values(),key=lambda x:(x["date"],x["city"],x["title"]))
verified=[x for x in events if x.get("verified")]
events=verified+ [x for x in events if not x.get("verified")][:max(0,80-len(verified))]
# Complete missing pictures from the publisher's Open Graph preview, with a
# bounded number of requests so the hourly workflow remains manageable.
image_checks=0
for event in events:
    if event.get("image") or image_checks>=12:continue
    url=event.get("url","")
    if not url.startswith("https://") or "news.google.com/" in url:continue
    image_checks+=1
    event["image"]=image_from_page(url)
print("Event image preview checks:",image_checks,"events with images:",sum(bool(e.get("image")) for e in events))
OUT.write_text(json.dumps({"updated":TODAY.isoformat(),"events":events},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print("Eligible RSS entries:",seen_count,"Upcoming event leads:",len(events))
