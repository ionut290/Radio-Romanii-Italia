#!/usr/bin/env python3
"""Official institutional bulletins for RDI, with verified publisher provenance.

Keep institutional press releases clearly separate from independent journalism.
Only link to announcements; never treat statements as independently verified facts.
"""
import datetime as dt
import email.utils
import html
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

# RSS addresses are provided by the institutions, not third-party RSS mirrors.
OFFICIAL_RSS = (
    ("Unione europea", "Commissione europea",
     "https://ec.europa.eu/commission/presscorner/api/rss?language=it", ("europa.eu",)),
    ("Unione europea", "Parlamento europeo",
     "https://www.europarl.europa.eu/rss/doc/press-releases/it.xml", ("europarl.europa.eu",)),
    ("Unione europea", "Consiglio dell'UE",
     "https://www.consilium.europa.eu/it/rss/pressreleases.ashx", ("consilium.europa.eu",)),
)

# Some institutions do not provide a working public RSS endpoint. Search only
# publisher-verified Google News records, never articles ABOUT those institutions.
OFFICIAL_SEARCH = (
    ("NATO e sicurezza", "NATO", "site:nato.int NATO when:5d", "en", "US", ("nato.int",)),
    ("Istituzioni", "ONU", "site:news.un.org/it ONU when:5d", "it", "IT", ("news.un.org",)),
    ("Istituzioni", "INPS", "site:inps.it INPS pensioni lavoro when:5d", "it", "IT", ("inps.it",)),
    ("Istituzioni", "Ministero degli Esteri", "site:esteri.it comunicati italiani estero when:5d", "it", "IT", ("esteri.it",)),
)

def official_host(url, domains):
    """Only accept actual institutional hosts, not lookalike domains."""
    try:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        return parsed.scheme == "https" and any(
            host == domain or host.endswith("." + domain) for domain in domains
        )
    except (ValueError, AttributeError):
        return False

def tag_text(element, local_name):
    for child in list(element):
        if child.tag.split("}")[-1].lower() == local_name.lower():
            return (child.text or "").strip()
    return ""

def safe_date(raw):
    if not raw:
        return None
    try:
        date = email.utils.parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        try:
            date = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    if date.tzinfo is None:
        date = date.replace(tzinfo=dt.timezone.utc)
    return date.astimezone(dt.timezone.utc)

def plain_text(raw):
    return " ".join(html.unescape(re.sub(r"<[^>]*>", " ", raw or "")).split())[:360]

def valid_fresh(published, now):
    age = now - published
    return dt.timedelta(hours=-1) <= age <= dt.timedelta(hours=48)

def rss_items(root):
    """Supports ordinary RSS and Atom, including namespace-prefixed feeds."""
    return [elem for elem in root.iter() if elem.tag.split("}")[-1] in ("item", "entry")]

def rss_link(entry):
    for child in list(entry):
        if child.tag.split("}")[-1] != "link":
            continue
        link = (child.attrib.get("href") or child.text or "").strip()
        if link.startswith("https://") and child.attrib.get("rel", "alternate") == "alternate":
            return link
    return ""

def get_official_items(now, known_urls, headers):
    output = []
    for category, publisher, feed_url, allowed_hosts in OFFICIAL_RSS:
        try:
            req = urllib.request.Request(feed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=7) as response:
                root = ET.fromstring(response.read(2_000_000))
            count = 0
            for entry in rss_items(root)[:35]:
                title = html.unescape(tag_text(entry, "title"))
                url = rss_link(entry)
                published = safe_date(tag_text(entry, "pubDate")
                                      or tag_text(entry, "published")
                                      or tag_text(entry, "updated"))
                if not title or not url or not official_host(url, allowed_hosts):
                    continue
                if not published or not valid_fresh(published, now) or url in known_urls:
                    continue
                summary = plain_text(tag_text(entry, "description")
                                     or tag_text(entry, "summary"))
                output.append({
                    "category": category, "title": title[:240], "url": url,
                    "source": publisher, "published": published.isoformat(),
                    "summary": summary, "image": "", "source_type": "comunicato_istituzionale",
                    "source_tier": "official"
                })
                known_urls.add(url)
                count += 1
                if count >= 8:
                    break
            print(f"Fonte istituzionale {publisher}: {count} comunicati")
        except Exception as exc:
            print(f"Feed istituzionale {publisher} non disponibile: {exc}")

    for category, publisher, query, lang, country, allowed_hosts in OFFICIAL_SEARCH:
        params = urllib.parse.urlencode({
            "q": query, "hl": f"{lang}-{country}", "gl": country,
            "ceid": f"{country}:{lang}"
        })
        try:
            req = urllib.request.Request(
                "https://news.google.com/rss/search?" + params, headers=headers
            )
            with urllib.request.urlopen(req, timeout=7) as response:
                root = ET.fromstring(response.read(2_000_000))
            count = 0
            for entry in root.findall("./channel/item")[:45]:
                source = entry.find("source")
                source_url = (source.attrib.get("url", "") if source is not None else "")
                if not official_host(source_url, allowed_hosts):
                    continue
                title = html.unescape((entry.findtext("title") or "").strip())
                link = (entry.findtext("link") or "").strip()
                published = safe_date(entry.findtext("pubDate"))
                if (not title or not link.startswith("https://")
                        or not published or not valid_fresh(published, now)
                        or link in known_urls):
                    continue
                summary = plain_text(entry.findtext("description") or "")
                output.append({
                    "category": category, "title": title[:240], "url": link,
                    "source": publisher, "published": published.isoformat(),
                    "summary": summary, "image": "", "source_type": "comunicato_istituzionale",
                    "source_tier": "official"
                })
                known_urls.add(link)
                count += 1
                if count >= 6:
                    break
            print(f"Notiziario istituzionale {publisher}: {count} avvisi")
        except Exception as exc:
            print(f"Ricerca istituzionale {publisher} non disponibile: {exc}")
    return output
