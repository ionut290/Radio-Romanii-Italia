#!/usr/bin/env python3
"""RDI Music DJ: safe, deterministic 24-hour SHADOW rotation simulator.

Works ONLY with the already-sanitized, read-only /api/report catalogue.
No AzuraCast API calls, no network, no media mutations, no playlist writes.
All start times use an explicitly assumed duration of 210 seconds: this is
a *playlist draft*, not an exact automation schedule. News, hourly bulletins,
commercials and jingles remain scheduled exclusively by AzuraCast.

The special YAMNet/GTZAN genre hypotheses are never used as trusted facts.
"""
from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import re

SECONDS_PER_TRACK_ESTIMATE = 210
MAX_TRACKS = 450
MIN_CONFIDENT_AUDIO = 20
# Seven uninterrupted blocks cover all 24h including the former 17-18 gap.
BLOCKS = (
    ("notte_00_07", 0, 420, "Notte / relax", ("tranquilla", "media")),
    ("mattino_07_10", 420, 600, "Risveglio / melodico", ("media", "tranquilla")),
    ("giorno_10_13", 600, 780, "Urban / pop leggero", ("media", "ritmata")),
    ("pomeriggio_13_18", 780, 1080, "Pomeriggio / energia", ("ritmata", "media")),
    ("sera_18_21", 1080, 1260, "Sera / melodico", ("media", "tranquilla")),
    ("notte_21_24", 1260, 1440, "Notte / lounge", ("tranquilla", "media")),
)

# This protects AzuraCast's real scheduled appointments; it does NOT assume
# their exact durations, which can change with the editorial calendar.
PROTECTED = (
    "Notiziari ed edizioni straordinarie (compreso il TG delle 18)",
    "Bollettini geopolitici programmati da AzuraCast",
    "Jingle, spot, comunicazioni e dirette editoriali",
)

def _title_key(name: str) -> str:
    """Collapse exported Mureka-style time suffixes to identify duplicates."""
    stem = re.sub(r"[_\s-]+(?:1[5-9]\d{8,}|20\d{7,})$", "", str(name or "").strip(), flags=re.I)
    normalized = re.sub(r"[^a-z0-9]+", " ", stem.casefold()).strip()
    return normalized

def _stable_hash(day: str, key: str, track_id: str) -> int:
    return int.from_bytes(
        hashlib.sha256((day + "|" + key + "|" + track_id).encode("utf-8")).digest()[:8],
        "big")

def _minutes(hhmm: str) -> int:
    hh, mm = map(int, hhmm.split(":"))
    return hh * 60 + mm

def _clock(total_seconds: int) -> str:
    minutes = total_seconds // 60
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

def _eligible(track: dict) -> bool:
    from rdi_music_dj import excluded
    if not isinstance(track, dict):
        return False
    title = str(track.get("title") or "").strip()
    ident = str(track.get("id") or "")
    if not title or not re.fullmatch(r"[a-f0-9]{16}", ident):
        return False
    if excluded(title) or excluded(track.get("artist") or ""):
        return False
    if track.get("energy_estimate") not in {"tranquilla", "media", "ritmata"}:
        return False
    try:
        bpm = float(track["bpm_candidate"])
        confidence = float(track["beat_confidence"])
        lufs = float(track["lufs"])
    except (KeyError, TypeError, ValueError):
        return False
    if not (45 <= bpm <= 205 and confidence >= .32 and -50 < lufs < -4):
        return False
    return True

def _genre(track: dict) -> str:
    # AI estimates MUST NOT be used as scheduling truth without validation.
    if track.get("genre_source") == "metadati_file":
        genre = str(track.get("genre") or "sconosciuto")
        if genre not in {"non_identificato", ""}:
            return genre
    return "sconosciuto"

def _pick(candidates: list[dict], used: set[str], titles: set[str],
          recent: list[dict], slot: str, day: str, priority: tuple[str, ...]):
    best = None
    best_key = None
    for tr in candidates:
        ident=tr["id"]
        tkey=_title_key(tr["title"])
        if ident in used or (tkey and tkey in titles):
            continue
        artist=str(tr.get("artist") or "").casefold().strip()
        # Never play the same known artist twice within 6 proposed songs.
        if artist and any(artist == str(last.get("artist") or "").casefold().strip()
                          for last in recent[-6:]):
            continue
        genre=_genre(tr)
        # Avoid three consecutive IDENTIFIED genres; unknown isn't a genre.
        if genre!="sconosciuto" and len(recent)>=2 and all(
            _genre(last)==genre for last in recent[-2:]):
            continue
        energy=tr["energy_estimate"]
        band=priority.index(energy) if energy in priority else 5
        # A little variation within a time block is preferable to a full
        # monotonous run of one energy group.
        if recent and recent[-1].get("energy_estimate")==energy:
            band+=1
        rank=_stable_hash(day, slot, ident)
        key=(band, rank)
        if best_key is None or key<best_key:
            best,best_key=tr,key
    return best

def simulate(catalogue: dict, day: str = "2026-10-30") -> dict:
    dt.date.fromisoformat(day)
    if not isinstance(catalogue, dict) or catalogue.get("read_only") is not True or catalogue.get("playlist_writes")!=0:
        raise ValueError("Only verified read-only DJ catalogues can be simulated")
    if not isinstance(catalogue.get("tracks"),list):
        raise ValueError("Missing local DJ audio catalogue")
    all_tracks=[tr for tr in catalogue["tracks"] if _eligible(tr)]
    # The original station media inventory can contain deleted/moved files;
    # this is a draft and must be validated before any future on-air use.
    used: set[str] = set()
    used_titles: set[str] = set()
    recent: list[dict] = []
    blocks=[]
    for name,start_min,end_min,label,priorities in BLOCKS:
        span_seconds=(end_min-start_min)*60
        required=(span_seconds + SECONDS_PER_TRACK_ESTIMATE-1)//SECONDS_PER_TRACK_ESTIMATE
        count=0
        tracks=[]
        for i in range(min(required,MAX_TRACKS)):
            # Preserve the chosen energy intent per band; fallback energy
            # classes are allowed only when needed.
            candidate=_pick(
                [tr for tr in all_tracks if tr["energy_estimate"] in priorities],
                used,used_titles,recent,name,day,priorities)
            if candidate is None:
                break
            used.add(candidate["id"])
            tkey=_title_key(candidate["title"])
            if tkey:
                used_titles.add(tkey)
            recent.append(candidate)
            estimate=start_min*60+i*SECONDS_PER_TRACK_ESTIMATE
            # Do not suggest a song starting outside this music block.
            if estimate>=end_min*60:
                break
            tracks.append({
                "id":candidate["id"],"title":candidate["title"],
                "artist":candidate.get("artist") or "",
                "energy":candidate["energy_estimate"],
                "genre_verificato":_genre(candidate),
                "orario_indicativo":_clock(estimate),
                "durata_assunta_secondi":SECONDS_PER_TRACK_ESTIMATE,
                "approvato":False
            })
            count+=1
        blocks.append({
            "id":name,"label":label,
            "dalle":_clock(start_min*60),
            "alle":_clock(end_min*60),
            "minuti":end_min-start_min,
            "brani_richiesti_stimati":required,
            "brani_proposti":count,
            "copertura_percento":round(count/required*100,1) if required else 100,
            "brani":tracks,
        })
    total=sum(b["brani_proposti"] for b in blocks)
    short=sum(b["brani_richiesti_stimati"]-b["brani_proposti"] for b in blocks)
    # This intentionally never returns an approval to modify live broadcast.
    return {
        "schema_version":1,
        "kind":"rdi-dj-dry-run",
        "date":day,
        "mode":"sola_simulazione",
        "read_only":True,
        "playlist_writes":0,
        "automatic_broadcast_enabled":False,
        "ready_for_live":False,
        "reason":"Durate ipotetiche, inventario non convalidato, generi AI da ascoltare e palinsesto AzuraCast protetto.",
        "duration_note":"Ogni brano è stimato a 3 minuti e 30 secondi: NON sono gli orari reali di trasmissione.",
        "protected_programmes":list(PROTECTED),
        "available_analyzed_tracks":len(all_tracks),
        "total_unique_tracks":total,
        "duplicate_tracks":total-len(used),
        "duplicate_titles":total-len(used_titles),
        "missing_tracks_estimated":short,
        "covers_all_24h_in_blocks":BLOCKS[0][1]==0 and BLOCKS[-1][2]==1440 and all(
            BLOCKS[i][2]==BLOCKS[i+1][1] for i in range(len(BLOCKS)-1)),
        "full_draft":short==0 and len(all_tracks)>=MIN_CONFIDENT_AUDIO,
        "genre_policy":"solo tag dichiarati; classificazioni IA non verificate escluse dalle decisioni",
        "blocks":blocks
    }

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--date",default=dt.datetime.now().date().isoformat())
    p.add_argument("--input",required=True)
    a=p.parse_args()
    catalogue=json.loads(open(a.input,encoding="utf-8").read())
    plan=simulate(catalogue,a.date)
    print(json.dumps(plan,ensure_ascii=False,indent=2))
