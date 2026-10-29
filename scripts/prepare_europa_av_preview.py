#!/usr/bin/env python3
"""Produce SOLO una copia MP4 locale di prova: mai stream, upload o download.

Usa file video/audio procurati lecitamente e un record approvato da RDI.
La traccia italiana separata sostituisce COMPLETAMENTE la voce originale.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys

from update_europa_videos import eligible_video

def probe(path: Path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams",
         "-of", "json", str(path)], capture_output=True, text=True, check=True,
        timeout=40
    )
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    duration = float(info.get("format", {}).get("duration") or 0)
    if duration <= 0 or duration > 1800:
        raise ValueError(f"Durata file non valida: {path.name}")
    return duration, streams

def build_command(item, video: Path, audio: Path | None, output: Path, lengths):
    """Crea command args senza shell; input e output SOLO percorsi locali."""
    video_duration, video_streams, audio_duration, audio_streams = lengths
    if not any(x.get("codec_type") == "video" for x in video_streams):
        raise ValueError("Il file principale non contiene video")
    if not output.suffix.lower() == ".mp4":
        raise ValueError("L'anteprima deve avere estensione .mp4")
    if item["audio_mode"] == "separate_it":
        if audio is None or not any(x.get("codec_type") == "audio" for x in audio_streams):
            raise ValueError("Traccia audio italiana separata obbligatoria")
        offset = item["audio_offset_ms"] / 1000
        if abs(video_duration - audio_duration) > max(3.0, abs(offset) + 2):
            raise ValueError("Durate video/audio non allineate: verifica manualmente la sincronizzazione")
        input_args = ["-i", str(video), "-itsoffset", str(offset), "-i", str(audio)]
        map_args = ["-map", "0:v:0", "-map", "1:a:0"]
        # -af applicato solo alla traccia italiana selezionata; l'audio
        # originale del video non viene mai mappato nell'output.
        filter_args = ["-af", "aresample=async=1:first_pts=0,apad"]
    elif item["audio_mode"] == "embedded_it":
        track = item["audio_stream_index"]
        avs = [s for s in video_streams if s.get("codec_type") == "audio"]
        if track >= len(avs):
            raise ValueError("La traccia italiana indicata non esiste nel video")
        input_args = ["-i", str(video)]
        map_args = ["-map", "0:v:0", "-map", f"0:a:{track}"]
        filter_args = ["-af", "aresample=async=1:first_pts=0"]
    else:
        raise ValueError("Modalità audio non autorizzata")
    return (["ffmpeg", "-hide_banner", "-nostdin", "-n", "-loglevel", "error"]
            + input_args + map_args
            + ["-t", str(video_duration), "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k"]
            + filter_args + ["-movflags", "+faststart", str(output)])

def main(argv=None):
    parser = argparse.ArgumentParser(description="RDI Europa: anteprima AV locale, mai in diretta")
    parser.add_argument("--approved", type=Path, default=Path(__file__).resolve().parents[1] / "data/europa-video-approved.json")
    parser.add_argument("--id", required=True, help="ID del contenuto già autorizzato")
    parser.add_argument("--video", type=Path, required=True, help="MP4 locale originale, già ottenuto legalmente")
    parser.add_argument("--audio", type=Path, help="File italiano separato AAC/MP3/WAV, necessario per separate_it")
    parser.add_argument("--output", type=Path, required=True, help="Percorso locale nuovo file .mp4")
    parser.add_argument("--execute", action="store_true", help="Senza questa opzione esegue solo verifica e dry run")
    args = parser.parse_args(argv)
    manifest = json.loads(args.approved.read_text(encoding="utf-8"))
    matches = [x for x in manifest.get("items", []) if x.get("id") == args.id]
    if len(matches) != 1:
        parser.error("Record approvato unico non trovato")
    item = matches[0]
    if not eligible_video(item, dt.datetime.now(dt.timezone.utc)):
        parser.error("La verifica lingua, sincronizzazione, copyright o scadenza è incompleta")
    video = args.video.expanduser().resolve(strict=True)
    audio = args.audio.expanduser().resolve(strict=True) if args.audio else None
    output = args.output.expanduser().resolve()
    if not video.is_file() or (audio and not audio.is_file()):
        parser.error("File di ingresso non valido")
    if output.exists() or output in (video, audio):
        parser.error("L'output deve essere nuovo e diverso dai file di origine")
    if item["audio_mode"] == "separate_it" and not audio:
        parser.error("Serve il file audio italiano separato")
    if item["audio_mode"] == "embedded_it" and audio:
        parser.error("Per audio incorporato NON fornire un file audio aggiuntivo")
    try:
        vd, vs = probe(video)
        ad, ass = probe(audio) if audio else (0.0, [])
        cmd = build_command(item, video, audio, output, (vd, vs, ad, ass))
        print(json.dumps({
            "status": "STAGING_ONLY",
            "video_id": item["id"], "audio_mode": item["audio_mode"],
            "original_audio_excluded": item["audio_mode"] == "separate_it",
            "video_seconds": vd, "audio_seconds": ad,
            "action": "CREA_FILE_LOCALE" if args.execute else "SIMULAZIONE",
            "output": str(output)
        }, ensure_ascii=False))
        if args.execute:
            output.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(cmd, check=True, timeout=2400)
            print("Anteprima creata localmente. NON inviata alla radio.")
    except (OSError, subprocess.CalledProcessError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
