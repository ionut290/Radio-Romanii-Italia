#!/usr/bin/env python3
"""RDI branded news cards: link landscape and Facebook photograph portrait.
Generated previews are editorial artwork, not evidence of an event.
"""
import io
import re
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from PIL import Image, ImageDraw, ImageFont, ImageOps
import cairosvg
from social_subjects import identify_subject, normalized

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "share-images"
OUT.mkdir(exist_ok=True)
CACHE = {"source": None, "image": None}
FONT_BOLD = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
)
FONT_REGULAR = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
)


def font(size, bold=True):
    for name in FONT_BOLD if bold else FONT_REGULAR:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    return ImageFont.load_default()


def source_image(source):
    """Read only image URLs or local repo assets; cache current story for variants."""
    if source == CACHE["source"]:
        return CACHE["image"].copy() if CACHE["image"] else None
    img = None
    try:
        if source.startswith("https://"):
            host = urlsplit(source).hostname or ""
            if not host:
                raise ValueError("no host")
            # Some Romanian news CDNs reject generic server clients even
            # though the image loads in a mobile browser. Try browser-like
            # headers and the publisher referer before using artwork.
            attempts = (
                {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                 "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
                 "Referer": "https://www.digi24.ro/"},
                {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 Version/18.0 Safari/605.1.15",
                 "Accept": "image/jpeg,image/png,image/webp,image/*;q=0.8"},
            )
            last_error = None
            for attempt_number, headers in enumerate(attempts):
                try:
                    req = Request(source, headers=headers)
                    with urlopen(req, timeout=5 if attempt_number == 0 else 3) as response:
                        if not response.headers.get("Content-Type", "").lower().startswith("image/"):
                            raise ValueError("not an image")
                        payload = response.read(8_000_001)
                    if len(payload) > 8_000_000:
                        raise ValueError("image too large")
                    with Image.open(io.BytesIO(payload)) as candidate:
                        candidate.load()
                        if candidate.width < 200 or candidate.height < 200:
                            raise ValueError("image too small")
                        img = candidate.convert("RGB")
                    break
                except Exception as exc:
                    last_error = exc
            if img is None and last_error:
                raise last_error
        elif source and not source.startswith(("http:", "//")):
            path = (ROOT / source.lstrip("./")).resolve()
            if not path.is_relative_to(ROOT) or not path.is_file():
                raise ValueError("invalid local image")
            if path.suffix.lower() == ".svg":
                img = Image.open(io.BytesIO(cairosvg.svg2png(url=str(path)))).convert("RGB")
            elif path.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
                img = Image.open(path).convert("RGB")
    except Exception as exc:
        if source:
            print("Social image fallback:", str(exc)[:110])
    CACHE["source"], CACHE["image"] = source, img
    return img.copy() if img else None


def wrap_text(draw, headline, face, max_width):
    lines = []
    current = ""
    for word in headline.split():
        candidate = (current + " " + word).strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
                current = word
            else:
                # A very long URL/word must never push text beyond the safe area.
                partial = ""
                for char in word:
                    if partial and draw.textbbox((0, 0), partial + char, font=face)[2] > max_width:
                        lines.append(partial)
                        partial = char
                    else:
                        partial += char
                current = partial
    if current:
        lines.append(current)
    return lines


def title_lines(draw, title, max_width, max_lines, max_height, initial, minimum):
    title = " ".join(str(title or "Știri Radio Românii din Italia").split())[:240]
    for size in range(initial, minimum - 1, -2):
        f = font(size)
        lines = wrap_text(draw, title, f, max_width)
        line_h = int(size * 1.21)
        if len(lines) <= max_lines and len(lines) * line_h <= max_height:
            return f, lines, line_h
    f = font(minimum)
    lines = wrap_text(draw, title, f, max_width)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and draw.textbbox((0, 0), last + "…", font=f)[2] > max_width:
            last = last[:-1]
        lines[-1] = last.rstrip() + "…"
    return f, lines, int(minimum * 1.21)


def background_image(photo, size):
    w, h = size
    if photo is not None:
        try:
            return ImageOps.fit(photo, size, method=Image.Resampling.LANCZOS, centering=(.5, .42)).convert("RGB")
        except Exception:
            pass
    # Abstract studio background instead of a fabricated documentary photograph.
    base = Image.new("RGB", size)
    pix = base.load()
    for y in range(h):
        fraction = y / max(1, h - 1)
        col = (int(33 - 20 * fraction), int(79 - 42 * fraction), int(128 - 54 * fraction))
        ImageDraw.Draw(base).line((0, y, w, y), fill=col)
    d = ImageDraw.Draw(base, "RGBA")
    d.ellipse((int(w * .45), -int(h * .12), int(w * 1.18), int(h * .54)), fill=(54, 142, 210, 50))
    d.ellipse((-int(w * .2), int(h * .20), int(w * .56), int(h * .83)), fill=(13, 29, 67, 65))
    return base


def logo_asset():
    p = ROOT / "RADIO-LOGO.png"
    try:
        return Image.open(p).convert("RGBA")
    except Exception:
        return None


LOGO = logo_asset()


# A cached fallback can survive long after the source article has
# acquired a working photograph. Recognize our own deterministic blue
# background by comparing unobstructed pixels (not titles or logos).
_FALLBACK_PROBES = {}

def _is_fallback_card(path, size):
    try:
        if size not in _FALLBACK_PROBES:
            backdrop = background_image(None, size)
            w, h = size
            portrait = h > w
            points = [(7, 7), (w - 8, 7), (w - 8, h // 6)]
            probes = []
            for x, y in points:
                ratio = y / h
                opacity = int(10 + 235 * min(1, max(0, (ratio - .37) / .60))) if portrait else int(15 + 230 * min(1, max(0, (ratio - .20) / .75)))
                rgb = backdrop.getpixel((x, y))
                probes.append(tuple(round(v * (255 - opacity) / 255 + overlay * opacity / 255) for v, overlay in zip(rgb, (4, 14, 33))))
            _FALLBACK_PROBES[size] = (points, probes)
        with Image.open(path) as existing:
            if existing.size != size:
                return False
            existing = existing.convert("RGB")
            points, probes = _FALLBACK_PROBES[size]
            return all(max(abs(a - b) for a, b in zip(existing.getpixel(point), expected)) < 16
                       for point, expected in zip(points, probes))
    except (OSError, ValueError):
        return False


def generate_card(item, ident, portrait=False, title=None, refresh=False, lang=None):
    """Social previews describe the news subject, not the publisher section."""
    suffix = "-facebook.jpg" if portrait else "-social.jpg"
    dest = OUT / (ident + suffix)
    src = str(item.get("image") or "")
    size = (1080, 1350) if portrait else (1200, 630)
    width, height = size
    headline = str(title or item.get("title") or "")
    subject = identify_subject(item, headline, lang)
    fingerprint = "rdi-subject-v1:" + hashlib.sha256(
        (headline + "\\n" + subject + "\\n" + src).encode("utf-8")
    ).hexdigest()[:20]
    # Every JPEG remembers the subject/headline used to render it. Regenerate
    # previously published cards if their old category was too generic, but
    # don't re-download hundreds of unchanged images on every scheduled run.
    if dest.exists() and not refresh and not src.lower().split("?")[0].endswith(".svg"):
        try:
            with Image.open(dest) as saved:
                previous = saved.getexif().get(270, "")
        except (OSError, ValueError):
            previous = ""
        legacy_unchanged = not previous and normalized(subject) == normalized(item.get("category") or "ȘTIRI")
        if previous == fingerprint or legacy_unchanged:
            if not src.startswith("https://") or not _is_fallback_card(dest, size):
                return dest
            photo = source_image(src)
            if photo is None:
                return dest
            print("Recovered article photograph for social preview:", ident)
        else:
            photo = source_image(src)
            print("Updated contextual social label:", ident, "=>", subject)
    else:
        photo = source_image(src)
    card = background_image(photo, size).convert("RGBA")
    tint = Image.new("RGBA", size)
    tint_pixels = ImageDraw.Draw(tint, "RGBA")
    for y in range(height):
        ratio = y / height
        if portrait:
            opacity = int(10 + 235 * min(1, max(0, (ratio - .37) / .60)))
        else:
            opacity = int(15 + 230 * min(1, max(0, (ratio - .20) / .75)))
        tint_pixels.line((0, y, width, y), fill=(4, 14, 33, opacity))
    card = Image.alpha_composite(card, tint)
    draw = ImageDraw.Draw(card)
    margin = 66 if portrait else 53
    # Brand appears once, at top, with an actual RDI logo when available.
    if LOGO:
        lg = LOGO.copy()
        lg.thumbnail((104 if portrait else 86, 104 if portrait else 86), Image.Resampling.LANCZOS)
        card.alpha_composite(lg, (margin, 49 if portrait else 29))
        brand_x = margin + (119 if portrait else 105)
    else:
        brand_x = margin
    draw.text((brand_x, 75 if portrait else 52),
              "RADIO ROMÂNII DIN ITALIA", font=font(30 if portrait else 27),
              fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(8, 22, 43, 255))

    max_width = width - 2 * margin
    available_height = 615 if portrait else 303
    face, lines, line_height = title_lines(
        draw, headline, max_width, 7 if portrait else 4,
        available_height, 82 if portrait else 59, 48 if portrait else 39
    )
    text_height = len(lines) * line_height
    bottom = height - (105 if portrait else 65)
    top = max(int(height * (.43 if portrait else .38)), bottom - text_height)
    category = subject
    if len(category) > 34:
        category = category[:31] + "…"
    tag_font = font(23 if portrait else 17)
    draw.text((margin, max(int(height * (.38 if portrait else .32)), top - 42)),
              category, font=tag_font, fill=(255, 213, 105, 255))
    for i, line in enumerate(lines):
        draw.text((margin, top + i * line_height), line,
                  font=face, fill=(255, 255, 255, 255),
                  stroke_width=1, stroke_fill=(17, 26, 42, 255))
    line_y = height - (62 if portrait else 36)
    draw.rounded_rectangle((margin, line_y, width - margin, line_y + 5),
                           radius=2, fill=(241, 198, 107, 255))
    metadata = Image.Exif()
    metadata[270] = fingerprint
    card.convert("RGB").save(dest, "JPEG", quality=86, optimize=True, subsampling=0, exif=metadata)
    return dest
