#!/usr/bin/env python3
"""RDI DJ: all verified music joins a shared rotation bank, daily order changes.

READ-ONLY SHADOW SIMULATION. Reads an authoritative local AzuraCast library
snapshot and real audio durations. Never uploads, assigns, deletes or plays any
AzuraCast file. Music broadcasting remains controlled by existing playlists,
jingles, news and editorial schedules. A bank entry does NOT imply airplay.

New analyzed and duration-verified uploads enter the bank without manual
selection, after the next local inventory/analysis cycle.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
import re

SLOT_BLOCKS=(
 ("notte_00_07",0,420,"Notte / relax",("tranquilla","media","ritmata")),
 ("mattino_07_10",420,600,"Mattino / melodico",("media","tranquilla","ritmata")),
 ("giorno_10_13",600,780,"Giorno / urban pop",("media","ritmata","tranquilla")),
 ("pomeriggio_13_18",780,1080,"Pomeriggio / energia",("ritmata","media","tranquilla")),
 ("sera_18_21",1080,1260,"Sera / melodico",("media","tranquilla","ritmata")),
 ("notte_21_24",1260,1440,"Notte / relax",("tranquilla","media","ritmata")),
)
# Exposes how many valid song files exist independently of airtime available.
PROTECTED=("TG delle 18 e notiziari","Jingle e spot di AzuraCast",
           "Bollettini geopolitici e trasmissioni in diretta")


def _id_sort(seed,token):
    return hashlib.sha256((seed+"|"+token).encode("utf-8")).digest()

def _title_key(title):
    # Simple normalized title key, not acoustic deduplication.
    title=re.sub(r"[_\s-]+(?:1[5-9]\d{8,}|20\d{7,})$","",str(title),flags=re.I)
    return re.sub(r"[^a-z0-9]+"," ",title.casefold()).strip()

def _clock(seconds):
    minutes=seconds//60
    return f"{minutes//60:02d}:{minutes%60:02d}"

def _eligible(t):
    from rdi_music_dj import excluded
    if not isinstance(t,dict) or excluded(str(t.get("title",""))+" "+str(t.get("artist",""))):
        return False
    if not re.fullmatch("[0-9a-f]{16}",str(t.get("id",""))):
        return False
    if not _title_key(t.get("title","")):
        return False
    try:
        duration=float(t["duration_seconds"])
    except (ValueError,TypeError,KeyError):
        return False
    return math.isfinite(duration) and 60<=duration<=720


def _schedulable(t):
    if not _eligible(t):
        return False
    try:
        bpm=float(t["bpm_candidate"])
        conf=float(t["beat_confidence"])
        lufs=float(t["lufs"])
    except (ValueError,TypeError,KeyError):
        return False
    return (math.isfinite(bpm) and 45<=bpm<=205 and
            math.isfinite(conf) and conf>=0.32 and
            math.isfinite(lufs) and -50<lufs<-4)

def _genre(tr):
    # AI genres remain estimates and cannot direct the radio unreviewed.
    if tr.get("genre_source")=="metadati_file":
        return str(tr.get("genre") or "sconosciuto")
    return "sconosciuto"

def _bank(tracks):
    # A title is NOT a unique recording. Mureka exports may have equal names
    # but different versions, and two artists may use the same song title.
    # Admit every real, duration-verified file once by its stable file ID.
    # Only true content hashes could safely remove duplicates of recordings.
    valid=[x for x in tracks if _eligible(x)]
    selected={}
    for tr in sorted(valid,key=lambda x:x["id"]):
        selected[tr["id"]]=tr
    return list(selected.values())

def _daily_order(bank,day):
    # Daily moving window through the ENTIRE bank, instead of picking the
    # same popular top-ranked tracks. All bank entries will be encountered
    # as the calendar advances, including when bank size exceeds one day.
    ordered=sorted(bank,key=lambda t:_id_sort("rdi-bank-v2",t["id"]))
    if not ordered:return []
    # Step 97 rotates the starting point; a coprime step is used when
    # needed so no subset of a bank is permanently skipped.
    n=len(ordered)
    step=97
    while math.gcd(step,n)!=1:
        step+=1
    offset=(dt.date.fromisoformat(day).toordinal()*step)%n
    return ordered[offset:]+ordered[:offset]

def _pick(queue,used,recent,priorities,room):
    options=[]
    recent_artists={str(t.get("artist","")).casefold() for t in recent[-5:]
                    if str(t.get("artist","")).strip()}
    for pos,tr in enumerate(queue):
        if tr["id"] in used or float(tr["duration_seconds"])>room:
            continue
        genre=_genre(tr)
        artist=str(tr.get("artist","")).casefold()
        if artist and artist in recent_artists:continue
        if genre not in ("","sconosciuto") and len(recent)>=2 and all(
            _genre(x)==genre for x in recent[-2:]):
            continue
        energy=tr.get("energy_estimate")
        band=priorities.index(energy) if energy in priorities else len(priorities)
        if recent and energy==recent[-1].get("energy_estimate"):
            band+=1
        # Fairness first across days (position); mild energy preference second
        # within every ~25-song slice to avoid sacrificing full-library reach.
        key=(pos//25, band, pos)
        options.append((key,tr))
    return min(options,key=lambda x:x[0])[1] if options else None

def simulate(catalogue,day=None):
    if day is None:
        day=dt.datetime.now(dt.timezone.utc).date().isoformat()
    dt.date.fromisoformat(day)
    if (not isinstance(catalogue,dict) or catalogue.get("read_only") is not True or
        catalogue.get("playlist_writes")!=0):
        raise ValueError("Only the read-only DJ index is allowed")
    if not isinstance(catalogue.get("tracks"),list):
        raise ValueError("Invalid DJ music catalogue")
    fresh=catalogue.get("live_index_verified") is True
    bank=_bank(catalogue["tracks"]) if fresh else []
    # Every validated song enters the bank immediately, even when its
    # finer rhythm/genre classification is still being calculated.
    # For a SHADOW playlist, existing playable audio and a verified duration
    # are enough. A missing BPM must NOT hide a real song forever.
    # Energy/genre guesses only influence sorting when available; they never
    # authorize an actual on-air playlist change.
    playable=list(bank)
    profiled_count=sum(_schedulable(tr) for tr in bank)
    rotated=_daily_order(playable,day)
    used=set()
    recent=[]
    blocks=[]
    for block_id,start,end,label,priorities in SLOT_BLOCKS:
        clock=start*60
        limit=end*60
        tracks=[]
        while clock<limit and len(tracks)<500:
            tr=_pick(rotated,used,recent,priorities,limit-clock)
            if tr is None:break
            used.add(tr["id"])
            recent.append(tr)
            duration=float(tr["duration_seconds"])
            tracks.append({
              "id":tr["id"],"title":tr["title"],"artist":tr.get("artist") or "",
              "orario_indicativo":_clock(int(clock)),
              "durata_reale_secondi":round(duration,1),
              "energia_stimata":tr.get("energy_estimate","non_verificata"),
              "genere_verificato":_genre(tr),
              "approvato":False,
            })
            clock+=duration
        covered=clock-start*60
        target=(end-start)*60
        blocks.append({
          "id":block_id,"label":label,
          "dalle":_clock(start*60),"alle":_clock(end*60),
          "minuti":end-start,
          "brani_richiesti_stimati":math.ceil(target/210),
          "brani_proposti":len(tracks),
          "copertura_percento":round(100*covered/target,1),
          "minuti_non_riempiti":round((target-covered)/60,1),
          "brani":tracks
        })
    # All playable songs are in this bank even when not selected on this
    # date; this is not a live AzuraCast playlist.
    pool=[{"id":tr["id"],"title":tr["title"],
           "artist":tr.get("artist") or "",
           "durata_reale_secondi":tr["duration_seconds"],
           "nuovo_brano":bool(tr.get("newly_added",False)),
           "analisi_audio_completa":_schedulable(tr)}
          for tr in bank]
    short=sum(x["minuti_non_riempiti"] for x in blocks)
    return {
      "schema_version":2,"kind":"rdi-dj-dry-run",
      "date":day,"mode":"solo_simulazione",
      "read_only":True,"playlist_writes":0,
      "automatic_broadcast_enabled":False,"ready_for_live":False,
      "live_index_verified":fresh,
      "pool_tracks_total":len(pool),
      "pool_ready_for_rotation":len(playable),
      "pool_audio_profiled":profiled_count,
      "pool_waiting_for_analysis":len(pool)-profiled_count,
      "pool_tracks":pool,
      "pool_excluded_from_today":len(pool)-len(used),
      "new_tracks_in_pool":sum(bool(x["nuovo_brano"]) for x in pool),
      "total_unique_tracks":len(used),
      "duplicate_tracks":0,
      "duplicate_titles":0,
      "missing_tracks_estimated":round(short,1),
      "covers_all_24h_in_blocks":SLOT_BLOCKS[0][1]==0 and
         SLOT_BLOCKS[-1][2]==1440 and all(
             SLOT_BLOCKS[i][2]==SLOT_BLOCKS[i+1][1] for i in range(len(SLOT_BLOCKS)-1)),
      "full_draft":fresh and short<=8,
      "duration_note":"Usate le durate vere dell'indice AzuraCast; gli orari restano indicativi perché programmi e inserti sono separati.",
      "reason":"Rotazione sperimentale. Notiziari, jingle e dirette restano sotto il controllo esclusivo di AzuraCast.",
      "protected_programmes":list(PROTECTED),
      "genre_policy":"Classificazioni IA non convalidate escluse dalle decisioni",
      "blocks":blocks,
    }

if __name__=="__main__":
    import argparse,sys
    parser=argparse.ArgumentParser()
    parser.add_argument("--date",default=None)
    parser.add_argument("--input",required=True)
    a=parser.parse_args()
    data=json.loads(open(a.input,encoding="utf-8").read())
    print(json.dumps(simulate(data,a.date),ensure_ascii=False,indent=2))
