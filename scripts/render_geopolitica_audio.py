#!/usr/bin/env python3
"""Produce the Italian RDI Geopolitica radio edition with timed TV slides.

Original three-note audio identity + synthetic voice + one speech clip per story.
Precisely aligned slide timings are saved from the individual, measured MP3 clips.
This file never publishes an unverified headline or modifies AzuraCast.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
from pathlib import Path


def ffmpeg_executable() -> str:
    from imageio_ffmpeg import get_ffmpeg_exe
    return get_ffmpeg_exe()


def cmd(*args: str) -> None:
    command = [ffmpeg_executable() if args[0] == "ffmpeg" else args[0], *args[1:]]
    subprocess.run(command, check=True, stdout=subprocess.DEVNULL)


def duration(path: Path) -> float:
    from mutagen.mp3 import MP3
    return float(MP3(str(path)).info.length)


async def speech(text: str, voice: str, path: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate="-5%").save(str(path))


def chime(path: Path, descending: bool = False) -> None:
    """Three-note identity written for RDI; not sampled from another radio."""
    frequencies = [784, 587, 440] if descending else [440, 587, 784]
    inputs = []
    for frequency in frequencies:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=44100:duration=3.0"]
    filters = (
        "[0:a]volume=0.035,adelay=0|0[a0];"
        "[1:a]volume=0.032,adelay=470|470[a1];"
        "[2:a]volume=0.030,adelay=940|940[a2];"
        "[a0][a1][a2]amix=inputs=3:duration=longest,"
        "afade=t=in:st=0:d=0.08,afade=t=out:st=2.05:d=0.92,"
        "aresample=44100,aformat=channel_layouts=stereo[out]"
    )
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
        "-filter_complex", filters, "-map", "[out]", "-c:a", "libmp3lame",
        "-b:a", "192k", "-ar", "44100", str(path))


def mixing_jingle(bed: Path, spoken: Path, destination: Path) -> None:
    filters = (
        "[0:a]aresample=44100,aformat=channel_layouts=stereo,volume=0.72[music];"
        "[1:a]aresample=44100,aformat=channel_layouts=stereo,"
        "loudnorm=I=-18:TP=-1.5:LRA=11[voice];"
        "[music][voice]amix=inputs=2:duration=longest:dropout_transition=0[out]"
    )
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", str(bed), "-i", str(spoken), "-filter_complex", filters,
        "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k",
        "-ar", "44100", str(destination))


def stitch(clips: list[Path], destination: Path, track_title: str) -> None:
    inputs = []
    pieces = []
    for idx, clip in enumerate(clips):
        inputs += ["-i", str(clip)]
        pieces.append(f"[{idx}:a]aresample=44100,aformat=channel_layouts=stereo,"
                      f"loudnorm=I=-18:TP=-1.5:LRA=11[a{idx}]")
    join = "".join(f"[a{idx}]" for idx in range(len(clips)))
    filters = ";".join(pieces + [f"{join}concat=n={len(clips)}:v=0:a=1[out]"])
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs, "-filter_complex", filters, "-map", "[out]",
        "-metadata", f"title={track_title}",
        "-metadata", "artist=Radio Românii din Italia",
        "-metadata", "album=RDI Geopolitica",
        "-id3v2_version", "3", "-c:a", "libmp3lame", "-b:a", "192k",
        "-ar", "44100", str(destination))


def produce(folder: Path) -> dict:
    manifest_path = folder / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if data.get("language") != "it":
        raise ValueError("La produzione automatica richiede la lingua italiana")
    segments = data.get("segments")
    if not isinstance(segments, list) or len(segments) < 3:
        raise ValueError("Segmenti editoriali mancanti")
    if data.get("story_count", 0) < 1 or len(data.get("track_title", "")) < 20:
        raise ValueError("Dati o titolo radiofonico mancanti")
    exe = Path(ffmpeg_executable())
    if not exe.is_file():
        raise RuntimeError("FFmpeg portatile non disponibile")

    voice = "it-IT-DiegoNeural"
    jingle_voice = folder / "jingle-voce.mp3"
    asyncio.run(speech(
        "Erre. Di. I. Geopolitica. Il mondo in primo piano.",
        voice, jingle_voice,
    ))
    bed = folder / "jingle-note.mp3"
    opening = folder / "jingle-iniziale.mp3"
    chime(bed)
    mixing_jingle(bed, jingle_voice, opening)

    clips = [opening]
    timing = [{"kind": "jingle", "start_seconds": 0.0, "end_seconds": round(duration(opening), 2)}]
    elapsed = duration(opening)
    articles_by_id = {row["id"]: row for row in data.get("articles", [])}
    # Brevi separatori originali fra le notizie, senza coprire la voce.
    separator = folder / "stacco-notizie.mp3"
    chime(separator)
    separator_seconds = duration(separator)
    for index, segment in enumerate(segments):
        if segment.get("kind") == "story" and index > 1:
            clips.append(separator)
            timing.append({
                "kind": "transition",
                "start_seconds": round(elapsed, 2),
                "end_seconds": round(elapsed + separator_seconds, 2),
            })
            elapsed += separator_seconds
        words = str(segment.get("text", "")).strip()
        if len(words) < 20:
            raise ValueError("Testo di un segmento vuoto o troppo corto")
        audio = folder / f"voce-{index:02}.mp3"
        asyncio.run(speech(words, voice, audio))
        if audio.stat().st_size < 6000:
            raise ValueError("Segmento di voce non valido")
        sec = duration(audio)
        scene = {
            "kind": segment["kind"], "start_seconds": round(elapsed, 2),
            "end_seconds": round(elapsed + sec, 2),
        }
        if segment["kind"] == "story":
            article = articles_by_id.get(segment.get("id"))
            if not article or not str(article.get("article_url", "")).startswith("https://"):
                raise ValueError("Fonte non pubblicabile per il video")
            scene.update({
                "id": article["id"], "country": article["country"],
                "title": article["title"], "summary": article["summary"],
                "article_url": article["article_url"],
                "published_date": article["published_date"],
            })
        timing.append(scene)
        clips.append(audio)
        elapsed += sec

    closing = folder / "jingle-finale.mp3"
    chime(closing, descending=True)
    clips.append(closing)
    end = elapsed + duration(closing)
    timing.append({
        "kind": "end-jingle", "start_seconds": round(elapsed, 2),
        "end_seconds": round(end, 2),
    })
    track_title = data["track_title"]
    output = folder / f"{track_title}.mp3"
    stitch(clips, output, track_title)
    measured = duration(output)
    if not 40 <= measured <= 420:
        output.unlink(missing_ok=True)
        raise ValueError(f"Durata radiofonica non ammessa: {measured:.2f}s")
    if abs(measured-end) > 2.5:
        raise ValueError(f"Sincronizzazione audio imprecisa: {measured:.2f}s vs {end:.2f}s")

    data["audio_duration_seconds"] = round(measured, 2)
    data["synthetic_voice"] = voice
    data["audio_filename"] = output.name
    data["timeline"] = timing
    manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tv = {
        "schema_version": 1, "language": "it", "edition_id": data["edition_id"],
        "track_title": track_title, "audio_duration_seconds": round(measured, 2),
        "generated_at": data["generated_at"], "timeline": timing,
        "site": "https://radioromanii.duckdns.org/geopolitica.html",
        "notice": "Gli articoli e le fonti sono disponibili sul sito RDI. La lettura è in italiano.",
    }
    (folder / "tv-timing.json").write_text(json.dumps(tv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Anteprima pronta: {output.name}, {measured:.0f} secondi, {len(segments)-2} articoli sincronizzati")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default="/tmp/rdi-geopolitica")
    args = parser.parse_args()
    produce(Path(args.folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
