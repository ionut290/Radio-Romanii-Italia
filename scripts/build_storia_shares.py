#!/usr/bin/env python3
"""Build one Facebook-previewable, source-attributed HTML page per RDI STORIA event."""
from __future__ import annotations
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "storia-eventi"
SITE = "https://radioromanii.duckdns.org"

def esc(text):
    return html.escape(str(text or ""), quote=True)

def trusted(url):
    try:
        p = urlsplit(str(url or ""))
        return p.scheme == "https" and p.hostname in {
            "commons.wikimedia.org", "upload.wikimedia.org", "thumb.wikimedia.org",
        }
    except ValueError:
        return False

def build(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    date = str(data.get("date", ""))
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
        raise ValueError("Invalid history date")
    folder = OUT / date
    folder.mkdir(parents=True, exist_ok=True)
    events = data.get("events") or []
    for index, e in enumerate(events, 1):
        if not e.get("title_it") or not e.get("source"):
            continue
        title = str(e["title_it"])
        description = str(e.get("text_it") or "")
        year = str(e.get("year") or "")
        photo = str(e.get("image") or "") if trusted(e.get("image")) else ""
        image = photo or SITE + "/RADIO-COVER.jpg"
        url = f"{SITE}/storia-eventi/{date}/{index}.html"
        source = str(e.get("source") or "")
        source_link = (f'<a href="{esc(source)}" target="_blank" rel="noopener noreferrer">Leggi la fonte originale</a>'
                       if source.startswith("https://") else "")
        photo_html = (f'<figure><img src="{esc(photo)}" alt="{esc(title)}" loading="lazy"><figcaption>'
                      f'{esc(e.get("image_credit") or "Wikimedia Commons")} · '
                      f'{esc(e.get("image_license") or "")}</figcaption></figure>') if photo else ""
        page = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(year)} · {esc(title)} | RDI STORIA</title>
<meta name="description" content="{esc(description[:220])}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="article"><meta property="og:site_name" content="Radio Românii din Italia">
<meta property="og:locale" content="it_IT"><meta property="og:url" content="{esc(url)}">
<meta property="og:title" content="{esc(year)} · {esc(title)}">
<meta property="og:description" content="{esc(description[:270])}">
<meta property="og:image" content="{esc(image)}"><meta property="og:image:alt" content="{esc(title)}">
<meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(description[:220])}"><meta name="twitter:image" content="{esc(image)}">
<style>
*{{box-sizing:border-box}}body{{margin:0;font:17px/1.7 system-ui,Arial,sans-serif;background:#f8f3e9;color:#1a2e42}}
header{{background:#14263e;padding:16px 5%;color:white}}header a{{color:white;text-decoration:none;font-weight:800}}
main{{max-width:900px;margin:32px auto;padding:30px;background:#fffdf9;border-radius:18px;box-shadow:0 12px 35px #241b1212}}
small{{text-transform:uppercase;letter-spacing:2px;color:#98763e;font-weight:800}}h1{{font:700 clamp(29px,5vw,52px)/1.15 Georgia,serif;margin:15px 0 24px}}
figure{{margin:0 0 25px}}img{{max-width:100%;border-radius:12px;max-height:490px;object-fit:contain}}figcaption{{font-size:12px;color:#526477}}
p{{font-size:19px}}.actions{{display:flex;gap:12px;flex-wrap:wrap;margin:24px 0}}.btn{{padding:12px 16px;background:#21496e;color:#fff;border-radius:9px;text-decoration:none;font-weight:700}}
.btn.fb{{background:#1877f2}}footer{{padding-top:20px;border-top:1px solid #e8decc;color:#546171}}
@media(max-width:700px){{main{{margin:0;padding:20px;border-radius:0}}}}
</style></head><body>
<header><a href="{SITE}/">🇷🇴 🇮🇹 RADIO ROMÂNII DIN ITALIA</a></header>
<main><small>RDI STORIA · {esc(date)} · {esc(e.get("country") or "Mondo")}</small>
<h1>{esc(year)} — {esc(title)}</h1>{photo_html}
<p>{esc(description)}</p>
<div class="actions"><a class="btn fb" target="_blank" rel="noopener noreferrer" href="https://www.facebook.com/sharer/sharer.php?u={esc(url)}">Condividi su Facebook</a>
<a class="btn" href="{SITE}/storia.html?date={esc(date)}&amp;lang=it">Tutti gli eventi del giorno</a></div>
<footer>{source_link}<p>RDI STORIA · Radio Românii din Italia. Fonti e crediti fotografici indicati.</p></footer></main></body></html>
"""
        (folder / f"{index}.html").write_text(page, encoding="utf-8")
    print(f"RDI STORIA social: {date}, {len(events)} pagine individuali")

def main():
    build(ROOT / "data/storia-oggi.json")

if __name__ == "__main__":
    main()
