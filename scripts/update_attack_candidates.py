#!/usr/bin/env python3
"""Daily, polite, non-publishing CSPII lead monitor for the RDI editorial desk.

This is NOT a terrorism classifier and NOT an automated fact checker.
Rows are leads only. No row is automatically put onto the public map,
counted in statistics, or published as a news article.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import urllib.request

SOURCE = "https://www.cspii.org/attacks"
OUTPUT = Path("data/attack-candidates.json")
DAYS = 35
MAX_ITEMS = 200

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

def decode_row(cells, today):
    try:
        when = dt.datetime.strptime(cells[0], "%B %d, %Y").date()
    except ValueError:
        return None
    # Source occasionally has future-dated listings. NEVER present them as historical attacks.
    if when > today or when < today - dt.timedelta(days=DAYS):
        return None
    country = cells[1].strip()[:100]
    if not country:
        return None
    # Descriptions can contain empty columns; preserve only uncontroversial lead metadata.
    description = cells[-1].strip()[:300]
    middle = cells[2:-1]
    city = middle[0][:100] if middle and not middle[0].isdigit() else ""
    if not description or description.lower() == "description":
        return None
    kind = "potential_plot" if re.search(r"\b(planned|plot|foiled|threat|arrested|attempted)\b",description,re.I) else "reported_incident"
    key = f"{when.isoformat()}|{country.casefold()}|{city.casefold()}|{description.casefold()}"
    item_id = "lead-" + hashlib.sha256(key.encode()).hexdigest()[:18]
    return {
        "id":item_id,"date":when.isoformat(),"country":country,
        "place":city,"description_en":description,
        "kind_hint":kind,"review_state":"pending",
        "attribution":"Source lead only; no independent check performed",
        "source_url":SOURCE,
    }

def download_html():
    req=urllib.request.Request(SOURCE,headers={
        "User-Agent":"RDI-EditorialMonitor/1.0 (+https://radioromanii.duckdns.org/; one request daily)",
        "Accept":"text/html",
        "Accept-Language":"en",
    })
    with urllib.request.urlopen(req, timeout=30) as res:
        content_type=res.headers.get("content-type","").lower()
        if "html" not in content_type:
            raise ValueError("Expected HTML: "+content_type)
        raw=res.read(2_000_001)
    if len(raw)>2_000_000:
        raise ValueError("HTML size exceeds safe limit")
    return raw.decode("utf-8","replace")

def process(html, old, today):
    parser=TableParser()
    parser.feed(html)
    if len(parser.rows)<3:
        raise ValueError("No readable HTML table found; do not publish any content")
    prior = {r["id"]:r for r in old.get("items",[]) if isinstance(r,dict) and r.get("id")}
    found = {}
    for cells in parser.rows[:120]:
        lead=decode_row(cells,today)
        if not lead:
            continue
        entry=prior.get(lead["id"],{})
        # Preserve human editorial assessments, never silently promote unverified leads.
        for field in ("review_state","editorial_notes","independent_sources","reviewed_by","reviewed_at"):
            if field in entry:
                lead[field]=entry[field]
        found[lead["id"]]=lead
    for key,old_item in prior.items():
        try:
            date=dt.date.fromisoformat(old_item["date"])
            if date >= today-dt.timedelta(days=DAYS) and key not in found:
                found[key]=old_item
        except (KeyError,TypeError,ValueError):
            pass
    items=sorted(found.values(),key=lambda v:(v["date"],v["id"]),reverse=True)[:MAX_ITEMS]
    if not items:
        raise ValueError("No valid non-future rows found; leaving previous data untouched")
    return items,len(parser.rows)

def main():
    today=dt.datetime.now(dt.timezone.utc).date()
    old=json.loads(OUTPUT.read_text(encoding="utf8")) if OUTPUT.exists() else {"items":[]}
    items,total=process(download_html(),old,today)
    out={
        "schema_version":1,
        "updated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
        "source":SOURCE,
        "state":"leads_pending_manual_verification",
        "notice":"These are unverified source leads. They are NOT on the public map and never auto-published as articles.",
        "raw_rows_read":total,
        "items":items
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print(f"Collected {len(items)} possible leads from {total} source rows; no public publication.")

if __name__=="__main__":
    main()
