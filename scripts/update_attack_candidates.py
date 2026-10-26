#!/usr/bin/env python3
"""RDI worldwide conflict/attack lead discovery. Not an automatic news publisher.

Sources: CSPII listing, GDELT article search, and multilingual Google News RSS.
ALL rows are editorial leads only. Never publish them to the map or as news.
Publication dates from news aggregators must not be mistaken for event dates.
"""
from __future__ import annotations

import datetime as dt
import email.utils
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUTPUT = Path("data/attack-candidates.json")
SOURCE = "https://www.cspii.org/attacks"
DAYS = 35
MAX_ITEMS = 240
TIMEOUT = 24
USER_AGENT = "RDI-EditorialMonitor/1.1 (+https://radioromanii.duckdns.org/; daily non-commercial research)"

GOOGLE_QUERIES = [
    ("en", "US", "US:en", '"terror attack" OR "bomb attack" OR "militant attack" when:2d'),
    ("it", "IT", "IT:it", 'attentato OR "attacco armato" OR "attacco terroristico" when:2d'),
    ("es", "ES", "ES:es", 'atentado OR "ataque armado" OR "ataque terrorista" when:2d'),
    ("fr", "FR", "FR:fr", 'attentat OR "attaque armée" OR "attaque terroriste" when:2d'),
]
GDELT_QUERIES = [
    '"terrorist attack" OR "bomb attack" OR "militant attack"',
    '"armed assault" OR "suicide bombing" OR "terror plot"',
]

class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.table_depth = 0
        self.in_row = False
        self.in_cell = False
        self.cells = []
        self.chunk = []
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.table_depth += 1
        elif self.table_depth and tag == "tr":
            self.in_row = True
            self.cells = []
        elif self.table_depth and self.in_row and tag in ("td", "th"):
            self.in_cell = True
            self.chunk = []

    def handle_data(self, value):
        if self.in_cell:
            self.chunk.append(value)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.in_cell:
            self.cells.append(" ".join(" ".join(self.chunk).split()))
            self.in_cell = False
            self.chunk = []
        elif tag == "tr" and self.in_row:
            if len(self.cells) >= 3:
                self.rows.append(self.cells[:])
            self.in_row = False
        elif tag == "table":
            self.table_depth = max(0, self.table_depth - 1)

def read_url(url, accept="application/json, application/rss+xml, text/html"):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {
        "www.cspii.org", "news.google.com", "api.gdeltproject.org", "feeds.bbci.co.uk"
    }:
        raise ValueError("Disallowed feed host")
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
        "Accept-Language": "en",
    })
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("Feed exceeds size limit")
        return raw.decode("utf-8", "replace")

def get_iso(value):
    try:
        stamp = email.utils.parsedate_to_datetime(value)
        if stamp is not None:
            return stamp.date().isoformat()
    except (TypeError, ValueError, OverflowError):
        pass
    try:
        return dt.datetime.fromisoformat(str(value).replace("Z","+00:00")).date().isoformat()
    except (TypeError, ValueError, OverflowError):
        return None

def plausible_date(value, today):
    if not value:
        return False
    try:
        parsed = dt.date.fromisoformat(value)
        return today - dt.timedelta(days=DAYS) <= parsed <= today
    except (ValueError, TypeError):
        return False

def lead_id(key):
    return "lead-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:18]

def kind_hint(description):
    # Automated detection is only an editorial clue; it is NOT classification.
    return "potential_plot" if re.search(r"\b(planned|plot|foiled|threat|arrested|attempted|sventato|complot|menace|frustrado)\b", description, re.I) else "reported_incident"

def cspii_leads(today):
    parser = TableParser()
    parser.feed(read_url(SOURCE, "text/html"))
    if len(parser.rows) < 3:
        raise ValueError("CSPII table missing/empty")
    leads = []
    for cells in parser.rows[:130]:
        try:
            when = dt.datetime.strptime(cells[0], "%B %d, %Y").date().isoformat()
        except (ValueError, IndexError):
            continue
        if not plausible_date(when,today) or len(cells)<3:
            continue
        country = cells[1].strip()[:100]
        description = cells[-1].strip()[:350]
        mid = cells[2:-1]
        place = mid[0][:100] if mid and not mid[0].isdigit() else ""
        if not country or not description or description.lower()=="description":
            continue
        key=f"{when}|{country.casefold()}|{place.casefold()}|{description.casefold()}"
        leads.append({
            "id":lead_id(key), "date":when,"date_kind":"source_claimed_incident_date",
            "country":country,"place":place,"description_en":description,
            "kind_hint":kind_hint(description),"review_state":"pending",
            "attribution":"Single source claim. No independent verification.",
            "source_id":"cspii","source_name":"CSPII / TheReligionOfPeace",
            "source_url":SOURCE, "event_date_confirmed":False
        })
    return leads

def google_news_leads(today):
    result=[]
    for lang,geo,ceid,query in GOOGLE_QUERIES:
        url = "https://news.google.com/rss/search?" + urllib.parse.urlencode({
            "q":query, "hl":lang,"gl":geo,"ceid":ceid
        })
        xml = ET.fromstring(read_url(url,"application/rss+xml"))
        for item in xml.findall(".//channel/item")[:35]:
            title = (item.findtext("title") or "").strip()[:300]
            article_url = (item.findtext("link") or "").strip()
            observed = get_iso(item.findtext("pubDate") or "")
            if not title or not article_url.startswith("https://") or not plausible_date(observed,today):
                continue
            publisher = (item.findtext("source") or "").strip()[:120]
            item_id = lead_id("google|" + article_url.split("?")[0])
            result.append({
                "id":item_id,"date":observed,
                "date_kind":"article_publication_date_NOT_event_date",
                "country":"","place":"","description_en":title,
                "kind_hint":"unclassified_news_lead","review_state":"pending",
                "attribution":"Search discovery only. Incident, date, actors and motives unverified.",
                "source_id":"google_news_"+lang, "source_name":"Google News search / "+lang,
                "publisher":publisher,"source_url":article_url,
                "event_date_confirmed":False
            })
    return result

def bbc_leads(today):
    """Original editorial headlines for cross-checking, not event classification."""
    url = "https://feeds.bbci.co.uk/news/world/rss.xml"
    root = ET.fromstring(read_url(url, "application/rss+xml, text/xml"))
    results = []
    keyword = re.compile(r"\b(attack|attacks|bomb|bombing|explosion|gunmen|shooting|militant|terror|hostages)\b",re.I)
    for item in root.findall(".//channel/item")[:100]:
        title = (item.findtext("title") or "").strip()[:300]
        observed = get_iso(item.findtext("pubDate") or "")
        article_url = (item.findtext("link") or "").strip()
        if not keyword.search(title) or not plausible_date(observed,today):
            continue
        if not article_url.startswith("https://www.bbc.") and not article_url.startswith("https://bbc."):
            continue
        results.append({
            "id":lead_id("bbc|" + article_url.split("?")[0]),
            "date":observed,"date_kind":"article_publication_date_NOT_event_date",
            "country":"","place":"","description_en":title,
            "kind_hint":"unclassified_news_lead","review_state":"pending",
            "attribution":"News headline to verify; no incident facts inferred.",
            "source_id":"bbc_world","source_name":"BBC World RSS",
            "publisher":"BBC News","source_url":article_url,
            "event_date_confirmed":False
        })
    return results

def gdelt_leads(today):
    result=[]
    for query in GDELT_QUERIES:
        url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode({
            "query":query,"mode":"artlist","format":"json","maxrecords":60,
            "timespan":"2d","sort":"datedesc"
        })
        document=json.loads(read_url(url,"application/json"))
        for art in document.get("articles", [])[:60]:
            if not isinstance(art,dict):
                continue
            article_url=str(art.get("url") or "")[:1200]
            title=str(art.get("title") or "").strip()[:300]
            seen=str(art.get("seendate") or "").strip()
            try:
                stamp=dt.datetime.strptime(seen[:14],"%Y%m%d%H%M%S").date().isoformat()
            except ValueError:
                stamp=get_iso(seen)
            if not article_url.startswith("https://") or not title or not plausible_date(stamp,today):
                continue
            result.append({
                "id":lead_id("gdelt|" + article_url.split("?")[0]),
                "date":stamp,"date_kind":"article_observed_date_NOT_event_date",
                "country":"","place":"","description_en":title,
                "kind_hint":"unclassified_news_lead","review_state":"pending",
                "attribution":"News index lead; do not infer confirmed incident or motive.",
                "source_id":"gdelt","source_name":"GDELT DOC 2.0",
                "publisher":str(art.get("domain") or "")[:120],
                "source_url":article_url,"event_date_confirmed":False
            })
    return result

def merge_candidates(new, old, today):
    preserved={}
    for item in old.get("items",[]):
        if isinstance(item,dict) and item.get("id") and plausible_date(item.get("date"),today):
            preserved[item["id"]]=item
    for item in new:
        prior=preserved.get(item["id"],{})
        if prior:
            for field in ("review_state","editorial_notes","independent_sources","reviewed_by","reviewed_at"):
                if field in prior:
                    item[field]=prior[field]
        preserved[item["id"]]=item
    # Preserve reviewed entries preferentially even when many feed results arrive.
    result=sorted(preserved.values(),key=lambda v:(
        v.get("review_state") not in ("verified","rejected","needs_followup"),
        v.get("date",""),v.get("id","")
    ),reverse=True)
    # Date-prioritization of unreviewed entries, with retained reviewed entries.
    reviewed=[x for x in result if x.get("review_state") not in ("pending",None)]
    pending=sorted((x for x in result if x.get("review_state") in ("pending",None)),
                   key=lambda v:(v.get("date",""),v.get("id","")),reverse=True)
    return (reviewed[:60] + pending)[:MAX_ITEMS]

def main():
    today=dt.datetime.now(dt.timezone.utc).date()
    old=json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"items":[]}
    new=[]
    status={}
    for name,loader in (
        ("cspii",cspii_leads),
        ("google_news",google_news_leads),
        ("bbc_world",bbc_leads),
        ("gdelt",gdelt_leads),
    ):
        try:
            found=loader(today)
            new.extend(found)
            status[name]={"status":"ok","new_leads":len(found)}
            print(f"{name}: {len(found)} possible leads")
        except Exception as exc:
            status[name]={"status":"error","error_type":type(exc).__name__}
            print(f"{name}: unavailable ({type(exc).__name__}); preserving prior leads")
    if not any(v["status"]=="ok" for v in status.values()):
        raise SystemExit("All feeds unavailable; keeping last published candidates JSON untouched")
    items=merge_candidates(new,old,today)
    output={
        "schema_version":2,
        "updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "state":"leads_pending_manual_verification",
        "notice":"Not verified. Publication/observation date is NOT incident date for press aggregators. NEVER auto-publish to attack-monitor.json or editorial.json.",
        "sources":{
            "cspii":"https://www.cspii.org/attacks",
            "gdelt":"https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/",
            "google_news":"https://news.google.com/",
            "bbc_world":"https://feeds.bbci.co.uk/news/world/rss.xml"
        },
        "source_status":status,
        "items":items
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Editorial queue: {len(items)} leads, 0 automatically published.")

if __name__=="__main__":
    main()
