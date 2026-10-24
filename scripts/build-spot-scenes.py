#!/usr/bin/env python3
"""Create nine branded spot images whenever AzuraCast gets a new audio advertisement.

No paid image API and no changes to the broadcast audio. Existing curated images
are never overwritten. Run via the hourly GitHub Actions spot catalog workflow.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/spot-audio-catalog.json'
CAMPAIGNS = ROOT / 'data/spot-campaigns.json'
OUT = ROOT / 'spot-images/auto'
W, H = 1440, 720
PHOTOS = [
    'ghid-restaurant.webp', 'ghid-grocery.webp', 'ghid-salon.webp',
    'ghid-garage.webp', 'ghid-cafe.webp', 'ghid-home.webp',
    'ghid-community.webp', 'podcast-journey.webp', 'podcast-studio.webp',
]
MESSAGES = [
    'DESCOPERĂ MAI MULT', 'POVEȘTI CARE NE APROPIE',
    'O COMUNITATE CONECTATĂ', 'ALĂTURI DE TINE',
    'ÎN ROMÂNĂ ȘI ÎN ITALIANĂ', 'PENTRU OAMENII DE AICI',
    'ACASĂ, ORIUNDE AI FI', 'OAMENI • IDEI • SERVICII',
    'RADIO ROMÂNII DIN ITALIA',
]
COLORS = [
    (235, 180, 99), (117, 207, 213), (233, 129, 159),
    (181, 170, 245), (156, 219, 150), (247, 176, 140),
    (120, 197, 241), (244, 216, 121), (208, 167, 241),
]
FONT_DIR = '/usr/share/fonts/truetype/dejavu/'

def fnt(size, bold=True):
    return ImageFont.truetype(FONT_DIR + ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'), size)

def norm(text):
    return re.sub(r'\s+', ' ', re.sub(r'[_-]+', ' ', str(text or ''))).casefold().strip()

def display_title(item):
    value = item.get('title') or Path(item.get('file_name') or '').stem or 'Spot RDI'
    value = re.sub(r'(?i)\.(mp3|wav|ogg|m4a|flac)$', '', value)
    return re.sub(r'\s+', ' ', re.sub(r'[_-]+', ' ', value)).strip()[:95] or 'Spot RDI'

def is_curated(item, curated):
    identity = norm(' '.join((item.get('title') or '', item.get('file_name') or '')))
    return any(norm(term) in identity for c in curated for term in c.get('matchAny', []) if norm(term))

def wrapped_lines(draw, title, face, max_width, limit=3):
    result, current = [], ''
    for word in title.split():
        candidate = (current + ' ' + word).strip()
        if current and draw.textbbox((0, 0), candidate, font=face)[2] > max_width:
            result.append(current)
            current = word
        else:
            current = candidate
    if current:
        result.append(current)
    if len(result) > limit:
        result = result[:limit]
        while len(result[-1]) > 1 and draw.textbbox((0, 0), result[-1] + '…', font=face)[2] > max_width:
            result[-1] = result[-1][:-1]
        result[-1] += '…'
    return result

def generate_image(item, key, index, target):
    seed = int(hashlib.sha256(f'{key}:{index}'.encode()).hexdigest()[:8], 16)
    photo = ROOT / 'spot-images' / PHOTOS[(index + seed % 3) % len(PHOTOS)]
    with Image.open(photo) as original:
        original = original.convert('RGB')
        image = ImageOps.fit(original, (W, H), Image.Resampling.LANCZOS,
                             centering=(0.4 + (seed % 21) / 100, 0.5))
    image = ImageEnhance.Color(image).enhance(0.85 + (index % 3) * 0.13).convert('RGBA')
    overlay = Image.new('RGBA', (W, H))
    layer = ImageDraw.Draw(overlay)
    for x in range(W):
        layer.line([(x, 0), (x, H)], fill=(3, 17, 37, min(252, int(246 * (1 - x / W) ** 1.65 + 22))))
    image = Image.alpha_composite(image, overlay)
    draw = ImageDraw.Draw(image)
    accent = COLORS[(seed + index) % len(COLORS)]
    draw.rounded_rectangle((57, 51, 220, 109), radius=13, fill=(5, 22, 40, 217), outline=accent, width=3)
    draw.text((80, 57), 'RDI', font=fnt(35), fill='white')
    draw.rounded_rectangle((60, 155, 425, 190), radius=9, fill=(*accent, 220))
    draw.text((76, 159), 'PUBLICITATE  •  RADIO', font=fnt(17), fill=(8, 21, 37))
    title = display_title(item)
    face = fnt(57 if len(title) < 36 else 47 if len(title) < 58 else 38)
    y = 250
    for line in wrapped_lines(draw, title, face, 750):
        draw.text((63, y), line, font=face, fill='white', stroke_width=1, stroke_fill=(8, 27, 42))
        y += face.size + 17
    draw.rounded_rectangle((61, 571, 748, 579), radius=3, fill=(*accent, 255))
    draw.text((62, 602), MESSAGES[index], font=fnt(24), fill=accent)
    draw.text((62, 651), 'RADIOROMANII.DUCKDNS.ORG', font=fnt(20, False), fill=(230, 239, 247))
    for i in range(9):
        sx = 1090 + i * 31
        draw.rounded_rectangle((sx, 659, sx + 22, 666), radius=3,
                               fill=(*accent, 255) if i == index else (215, 225, 235, 90))
    target.parent.mkdir(parents=True, exist_ok=True)
    image.convert('RGB').save(target, 'WEBP', quality=79, method=5)

def main():
    if not CATALOG.exists() or not CAMPAIGNS.exists():
        raise SystemExit('Missing catalog/configuration')
    items = json.loads(CATALOG.read_text(encoding='utf-8')).get('items', [])
    if not items:
        raise SystemExit('Empty catalog: keep existing campaigns')
    config = json.loads(CAMPAIGNS.read_text(encoding='utf-8'))
    curated = [c for c in config.get('campaigns', []) if not c.get('generated')]
    old = {c.get('sourceKey'): c for c in config.get('campaigns', []) if c.get('generated')}
    generated = []
    for item in items:
        if is_curated(item, curated):
            continue
        key = item.get('key')
        if not isinstance(key, str) or not re.fullmatch(r'[a-f0-9]{12,64}', key):
            continue
        title = display_title(item)
        cid = 'auto-' + key[:12]
        scenes = []
        for index in range(9):
            output = OUT / cid / f'{index + 1:02d}.webp'
            if not output.exists() or key not in old or title != old[key].get('title'):
                generate_image(item, key, index, output)
            scenes.append({'image': './' + output.relative_to(ROOT).as_posix(),
                           'title': title, 'text': MESSAGES[index], 'poster': True})
        generated.append({
            'id': cid, 'generated': True, 'sourceKey': key,
            'title': title,
            'matchAny': [title, Path(item.get('file_name') or '').stem.replace('_', ' ')],
            'sceneSeconds': max(1, round(float(item.get('duration') or 45) / 9, 3)),
            'footer': 'Radio Românii din Italia',
            'website': 'radioromanii.duckdns.org', 'scenes': scenes,
        })
    config['campaigns'] = curated + generated
    next_value = json.dumps(config, ensure_ascii=False, indent=2) + '\n'
    if CAMPAIGNS.read_text(encoding='utf-8') != next_value:
        CAMPAIGNS.write_text(next_value, encoding='utf-8')
    print(f'Curated campaigns: {len(curated)}. Automatically generated: {len(generated)} ({len(generated) * 9} images).')

if __name__ == '__main__':
    main()
