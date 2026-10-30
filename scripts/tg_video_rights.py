#!/usr/bin/env python3
"""Select properly licensed TV-news video clips, never arbitrary embedded news videos.

Exact-event footage must have a matching article URL and an explicit broadcast
permission record. Contextual b-roll is selected only for specific topics
with reviewed license metadata from RDI's existing video library.
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
REGISTRY_PATH = ROOT / "data/tg-video-licenses.json"
LANDSCAPE_PATH = ROOT / "data/youtube-landscapes.json"

# Do not make an unrelated generic stock clip appear to depict an actual death,
# accident, crime, war, medical emergency, or other serious incident.
SENSITIVE = re.compile(
    r"\b(?:mort[eoia]|deces|decedat|ucis|ucidere|omor|omicid|crim[aăe]|"
    r"accident|traged|incend|explozi|explos|violent|atac|ranit|r[aă]ni|"
    r"spitalizat|deced|r[aă]zboi|razboi|bombard|r[aă]pire|rapire|"
    r"stupr|violenz|femminicid|cadaver|disparut|disparit)\w*",
    flags=re.IGNORECASE
)
SILENT_VIDEO_MAX_SECONDS = 18
SILENT_VIDEO_MIN_SECONDS = 5


def fold(value: object) -> str:
    s = unicodedata.normalize("NFKD", str(value or "").casefold())
    return "".join(c for c in s if not unicodedata.combining(c))


def safe_media_url(value: object) -> bool:
    """HTTPS direct .mp4 or .webm only, public host, no YouTube/watch/embed URLs."""
    if not isinstance(value, str) or len(value) > 1500:
        return False
    try:
        u = urlparse(value)
        host = (u.hostname or "").lower()
        if u.scheme != "https" or not host or u.username or u.password or u.fragment:
            return False
        if host in {"localhost", "news.google.com", "youtube.com", "www.youtube.com",
                    "youtu.be", "player.vimeo.com", "vimeo.com"}:
            return False
        if not re.fullmatch(r"[a-z0-9.-]+", host) or "." not in host:
            return False
        if host.endswith((".local", ".internal", ".localhost")):
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return bool(re.search(r"\.(?:mp4|webm)$", u.path, re.IGNORECASE))
    except ValueError:
        return False


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def approved_context(record: dict) -> bool:
    return (record.get("kind") == "video" and record.get("rights_reviewed") is True and
            record.get("audio_muted") is True and record.get("editorial_visual") is True and
            str(record.get("source_url", "")).startswith("https://www.pexels.com/video/") and
            str(record.get("license_url", "")).startswith("https://www.pexels.com/") and
            safe_media_url(record.get("src")) and
            urlparse(record["src"]).hostname == "videos.pexels.com" and
            bool(record.get("credit")) and bool(record.get("reviewed_on")))


def match_terms(title: str, groups: object) -> bool:
    if not isinstance(groups, list) or not 1 <= len(groups) <= 4:
        return False
    title = fold(title)
    return all(
        isinstance(group, list) and group and any(
            len(str(word)) >= 4 and re.search(
                r"(?<![a-z])" + re.escape(fold(word)), title
            ) for word in group if isinstance(word, str)
        ) for group in groups
    )


def safe_duration(value: object) -> int:
    try:
        duration = int(value)
    except (TypeError, ValueError):
        return 12
    return max(SILENT_VIDEO_MIN_SECONDS, min(SILENT_VIDEO_MAX_SECONDS, duration))


def exact_event_clip(story: dict, clips: object) -> dict | None:
    if not isinstance(clips, list):
        return None
    for record in clips:
        if not isinstance(record, dict) or record.get("article_url") != story.get("source_url"):
            continue
        if record.get("youtube_live_authorized") is not True or record.get("rights_reviewed") is not True:
            continue
        if record.get("audio_muted") is not True:
            continue
        if not (safe_media_url(record.get("src")) and str(record.get("license_reference", "")).startswith("https://")
                and len(str(record.get("permission_reference") or "")) >= 18
                and record.get("reviewed_on") and record.get("credit")):
            continue
        # No video references claiming to be the event without matching source URL.
        return {
            "src": record["src"], "kind": "event", "video_id": str(record.get("id") or ""),
            "seconds": safe_duration(record.get("max_seconds")), "audio_muted": True,
            "notice": "VIDEO DELL'EVENTO · " + str(record["credit"])[:100],
            "credit": record["credit"], "source_url": record["license_reference"],
        }
    return None


def select_video(story: dict, registry: dict | None = None, landscapes: dict | None = None) -> dict | None:
    if not isinstance(story, dict):
        return None
    registry = registry if registry is not None else load_json(REGISTRY_PATH)
    landscapes = landscapes if landscapes is not None else load_json(LANDSCAPE_PATH)
    if registry.get("schema_version") != 1:
        return None
    # This is the ONLY route for original publisher-supplied news-event footage.
    event = exact_event_clip(story, registry.get("event_clips"))
    if event:
        return event
    headline = str(story.get("title_original") or story.get("title") or "")
    if SENSITIVE.search(fold(headline)):
        return None
    records = {x["id"]: x for x in landscapes.get("items", [])
               if isinstance(x, dict) and isinstance(x.get("id"), str)}
    for rule in registry.get("repertory_clips", []):
        if not isinstance(rule, dict) or not match_terms(headline, rule.get("all_terms")):
            continue
        media = records.get(rule.get("landscape_id"))
        if not media or not approved_context(media):
            continue
        return {
            "src": media["src"], "kind": "repertory", "video_id": rule.get("id", ""),
            "seconds": safe_duration(rule.get("max_seconds")), "audio_muted": True,
            "notice": "IMMAGINI DI REPERTORIO · " + str(media["credit"])[:100],
            "credit": media["credit"], "source_url": media["source_url"],
            "license_url": media["license_url"],
            "poster": (media.get("poster") if isinstance(media.get("poster"), str)
                       and media["poster"].startswith("https://images.pexels.com/videos/")
                       else ""),
        }
    return None


def resolve_for_stories(stories: list[dict],
                        registry: dict | None = None,
                        landscapes: dict | None = None) -> list[dict]:
    """Avoid the same stock clip being repeated under several news items."""
    used = set()
    result = []
    for story in stories:
        match = select_video(story, registry=registry, landscapes=landscapes)
        if match and (match["src"] in used):
            match = None
        if match:
            used.add(match["src"])
        result.append(match)
    return result
