#!/usr/bin/env python3
"""RDI Europa: limited technical sample from an official EU video+IT-audio pair.

Never starts a broadcast, changes playout configuration, or approves rights.
Private editorial 12-second preview only; rights/voice must still be reviewed.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/europa-real-av-staging.json"
REVIEWS = ROOT / "data/europa-video-rights-review.json"
SECONDS = 12

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def verify_record(id: str):
    data = load(SOURCE)
    records = [x for x in data.get("items", []) if x.get("id") == id]
    if len(records) != 1:
        raise ValueError("Record ufficiale unico non presente")
    x = records[0]
    if x.get("publish_approved") is not False:
        raise ValueError("Questo processo è solo per materiale NON in onda")
    if x.get("review_status") != "RIGHTS_AND_SYNC_PENDING":
        raise ValueError("Video non in stato revisione per prova tecnica")
    if x.get("third_party_exception_noted") is not False:
        raise ValueError("Eccezioni diritti di terzi: prova bloccata")
    if x.get("source_url") != "https://audiovisual.ec.europa.eu/en/media/video/" + id:
        raise ValueError("Sorgente istituzionale non corrispondente")
    if x.get("expected_duration_seconds",0) > 1800:
        raise ValueError("Durata eccessiva")
    for key in ("original_video_url", "italian_audio_url"):
        u = urlparse(x[key])
        if (u.scheme != "https" or u.hostname != "vod.prd.commavservices.eu"
                or f"/294336/" not in u.path or not u.path.endswith(".mp4")):
            raise ValueError("URL non appartenente al CDN AV UE verificato")
    if "/ita.mp4" not in urlparse(x["italian_audio_url"]).path:
        raise ValueError("Traccia audio italiana non esplicita")
    reviews = load(REVIEWS).get("items",[])
    matches = [r for r in reviews if r.get("source_url") == x["source_url"]]
    if len(matches) != 1 or matches[0].get("status_for_live") != "NOT_APPROVED":
        raise ValueError("Verifica diritti mancante o diversa da NOT_APPROVED")
    if matches[0].get("third_party_warning") is not False:
        raise ValueError("Diritti di terzi segnalati: prova bloccata")
    return x

def probe(path: Path):
    out = subprocess.run(["ffprobe", "-hide_banner", "-v", "error", "-show_entries",
                          "format=duration:stream=index,codec_name,codec_type:stream_tags=language",
                          "-of", "json", str(path)], check=True, capture_output=True, text=True, timeout=35)
    return json.loads(out.stdout)

def command(record: dict, output: Path):
    # -map excludes the original video's audio and uses only the IT track.
    return [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "warning",
        "-rw_timeout", "20000000", "-t", str(SECONDS), "-i", record["original_video_url"],
        "-rw_timeout", "20000000", "-t", str(SECONDS), "-i", record["italian_audio_url"],
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", "scale=960:-2",
        "-t", str(SECONDS), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "27", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-metadata:s:a:0", "language=ita",
        "-movflags", "+faststart", "-shortest", "-y", str(output)
    ]

def main():
    parser = argparse.ArgumentParser(description="Solo preview tecnica RDI Europa; NO LIVE")
    parser.add_argument("--id", default="I-294336")
    parser.add_argument("--output", type=Path, default=Path("/tmp/rdi-europa-it-anteprima.mp4"))
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.id != "I-294336":
        parser.error("Solo il caso I-294336 è stato verificato per questa prova")
    record = verify_record(args.id)
    out = args.output.resolve()
    if out.exists() or out.suffix.lower() != ".mp4":
        parser.error("L'output deve essere un nuovo file MP4")
    if not args.execute:
        print(json.dumps({
            "status": "DRY_RUN", "seconds": SECONDS, "source": record["source_url"],
            "language": "Italiano", "rights": "NOT_APPROVED",
            "av_command": "FFmpeg mappa soltanto 0:v:0 e 1:a:0; radio live non modificata",
        }, ensure_ascii=False))
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(command(record, out), check=True, capture_output=True,
                              text=True, timeout=240)
        details = probe(out)
        streams = details.get("streams", [])
        videos = [s for s in streams if s.get("codec_type") == "video"]
        audios = [s for s in streams if s.get("codec_type") == "audio"]
        seconds = float(details.get("format", {}).get("duration",0))
        if len(videos) != 1 or len(audios) != 1 or not 8 <= seconds <= 13:
            raise ValueError(f"Preview AV non valida: video={len(videos)}, audio={len(audios)}, sec={seconds}")
        if audios[0].get("tags",{}).get("language") != "ita":
            raise ValueError("La traccia di output non è marcata come italiana")
        stats = {"status":"PREVIEW_CREATED_NOT_BROADCAST","video_id":args.id,
                 "duration_seconds":round(seconds,2),"video_codec":videos[0].get("codec_name"),
                 "audio_codec":audios[0].get("codec_name"),"audio_language_tag":"ita",
                 "audio_from":"IT CDN file option (content must still be listened to)",
                 "original_video_audio_excluded": True,
                 "rights":"NOT_APPROVED","live_enabled":False,
                 "tested_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                 "credit":record["credit"],"output_bytes":out.stat().st_size}
        report = out.with_suffix(".json")
        report.write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        print(json.dumps(stats,ensure_ascii=False))
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError, OSError) as err:
        if out.exists():
            out.unlink()
        raise SystemExit(f"Preview non generata: {err}") from err

if __name__ == "__main__":
    main()
