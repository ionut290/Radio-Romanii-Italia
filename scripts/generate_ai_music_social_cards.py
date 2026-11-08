#!/usr/bin/env python3
"""Produce static, crawler-visible social share pages for RDI AI Music tracks."""
import html
import io
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

API = "https://radio-romanii-italia.duckdns.org/api/ai-music/spotlight"
SITE = "https://radioromanii.duckdns.org"
OUT = Path("ai-music-share")
OUT.mkdir(exist_ok=True)

def get_page(page):
    url = API + "?" + urllib.parse.urlencode({"page": page})
    req = urllib.request.Request(url, headers={"User-Agent": "RDI-Social-Cards/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=35) as response:
        import json
        return json.load(response)

def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for base in ("/usr/share/fonts/truetype/dejavu/", "/usr/share/fonts/"):
        try:
            return ImageFont.truetype(base + name, size)
        except OSError:
            pass
    return ImageFont.load_default()

def fit(draw, value, max_width, size, min_size=28):
    value = str(value or "").strip()
    while size >= min_size:
        f = font(size, True)
        if draw.textbbox((0, 0), value, font=f)[2] <= max_width:
            return value, f
        size -= 2
    f = font(min_size, True)
    while value and draw.textbbox((0, 0), value + "…", font=f)[2] > max_width:
        value = value[:-1]
    return value + "…", f

def image_for_song(title, artist, position, destination):
    im = Image.new("RGB", (1200, 630), "#0c111b")
    d = ImageDraw.Draw(im)
    for y in range(630):
        d.line((0, y, 1200, y), fill=(10 + y // 100, 17 + y // 90, 28 + y // 40))
    d.ellipse((795, -270, 1450, 385), fill="#122f3d")
    d.ellipse((930, 165, 1310, 545), outline="#28d9e3", width=5)
    d.ellipse((955, 190, 1285, 520), outline="#205d6b", width=3)
    d.ellipse((1020, 255, 1220, 455), fill="#193b4a")
    d.text((1100, 350), "♫", anchor="mm", font=font(105, True), fill="#4ce8ed")
    d.rounded_rectangle((65, 52, 660, 107), radius=20, fill="#14323a", outline="#2c9fa9", width=2)
    d.text((89, 61), "RDI  •  RADIO ROMÂNII DIN ITALIA", font=font(24, True), fill="#92f1f2")
    d.text((65, 151), "CLASSIFICA AI MUSIC", font=font(36, True), fill="#f4f7fa")
    d.rounded_rectangle((65, 221, 380, 357), radius=24, fill="#29d7e1")
    d.text((93, 240), "POSIZIONE", font=font(20, True), fill="#083037")
    d.text((90, 256), f"#{position}", font=font(79, True), fill="#08222a")
    display_title, title_font = fit(d, title, 1030, 58, 30)
    d.text((65, 402), display_title, font=title_font, fill="#ffffff")
    display_artist, artist_font = fit(d, artist, 1015, 31, 22)
    d.text((65, 489), display_artist, font=artist_font, fill="#b9d2d6")
    d.rectangle((0, 575, 1200, 630), fill="#102b32")
    d.text((65, 589), "🎵 ASCOLTA GRATIS • VOTA • CONDIVIDI".replace("🎵 ", ""), font=font(22, True), fill="#68e4e9")
    im.save(destination, "PNG", optimize=True)

def escape(s):
    return html.escape(str(s), quote=True)

def build():
    # Never wipe old cards if the API is temporarily unavailable.
    all_tracks = []
    first = get_page(1)
    pages = min(1000, max(1, int(first.get("total_pages") or 1)))
    for page in range(1, pages + 1):
        data = first if page == 1 else get_page(page)
        tracks = data.get("tracks") or []
        if not isinstance(tracks, list):
            raise ValueError("Invalid tracks response")
        for index, track in enumerate(tracks):
            if track.get("id") is not None:
                all_tracks.append((page, (page - 1) * 20 + index + 1, track))
    if not all_tracks:
        raise RuntimeError("No tracks: refusing to remove social cards")
    generated = set()
    for page, rank, track in all_tracks:
        raw_id = str(track["id"])
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", raw_id)
        if not safe_id:
            continue
        title = str(track.get("title") or "Brano AI Music")
        artist = str(track.get("artist") or "RDI AI Music")
        link = SITE + "/spotlight-ai.html?" + urllib.parse.urlencode({"song": raw_id, "page": page})
        card_url = SITE + "/ai-music-share/" + urllib.parse.quote(safe_id) + ".html"
        image_url = SITE + "/ai-music-share/" + urllib.parse.quote(safe_id) + ".png"
        og_title = f"#{rank} • {title} — {artist} | RDI AI Music"
        description = f"Posizione #{rank} nella classifica RDI AI Music. Ascolta gratis {title} di {artist}, vota e condividi!"
        image_for_song(title, artist, rank, OUT / (safe_id + ".png"))
        page_html = f"""<!doctype html>
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(og_title)}</title>
<meta name="description" content="{escape(description)}">
<meta property="og:type" content="music.song">
<meta property="og:site_name" content="Radio Românii din Italia">
<meta property="og:title" content="{escape(og_title)}">
<meta property="og:description" content="{escape(description)}">
<meta property="og:url" content="{escape(card_url)}">
<meta property="og:image" content="{escape(image_url)}">
<meta property="og:image:secure_url" content="{escape(image_url)}">
<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{escape(og_title)}">
<meta name="twitter:description" content="{escape(description)}">
<meta name="twitter:image" content="{escape(image_url)}">
<link rel="canonical" href="{escape(card_url)}">
<meta http-equiv="refresh" content="0;url={escape(link)}">
<style>body{{font:18px system-ui;background:#0c111b;color:white;text-align:center;padding:50px 15px}}a{{color:#46e1e9}}</style>
</head><body><h1>{escape(og_title)}</h1><p>{escape(description)}</p>
<p><a href="{escape(link)}">▶ Ascolta la canzone su RDI AI Music</a></p>
<script>location.replace({__import__("json").dumps(link)});</script>
</body></html>"""
        (OUT / (safe_id + ".html")).write_text(page_html, encoding="utf-8")
        generated.add(safe_id)
    # Retain previous pages when tracks disappear so already shared links remain resolvable.
    print(f"Generated {len(generated)} song-specific social cards across {pages} pages")

if __name__ == "__main__":
    for attempt in range(3):
        try:
            build()
            break
        except Exception as ex:
            print(f"Attempt {attempt + 1} failed: {ex}", file=sys.stderr)
            if attempt == 2:
                raise
            time.sleep(12)
