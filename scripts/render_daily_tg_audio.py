#!/usr/bin/env python3
"""Create a preview TG MP3 plus an exact on-air video timing manifest.

The audio is produced in a GitHub Actions artifact; this script does not
alter AzuraCast or start a YouTube stream. It reuses ElsaNeural and the
original RDI audio identity from the existing verified geopolitics bulletin.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import subprocess

from render_geopolitica_audio import chime, duration, ffmpeg_executable, mixing_jingle, speech


def merge(clips: list[Path], out: Path, title: str) -> None:
    ffmpeg = ffmpeg_executable()
    args: list[str] = []
    filters: list[str] = []
    for i, part in enumerate(clips):
        args += ["-i", str(part)]
        filters.append(f"[{i}:a]aresample=44100,aformat=channel_layouts=stereo,loudnorm=I=-18:TP=-1.5:LRA=11[a{i}]")
    joined = "".join(f"[a{i}]" for i in range(len(clips)))
    filters.append(f"{joined}concat=n={len(clips)}:v=0:a=1[out]")
    subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", *args,
                    "-filter_complex", ";".join(filters), "-map", "[out]",
                    "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
                    "-metadata", f"title={title}",
                    "-metadata", "artist=Radio Românii din Italia",
                    "-metadata", "album=TG RDI della sera",
                    str(out)], check=True)


def section_boundaries(spoken: str, paragraphs: list[str]) -> list[float]:
    """Approximate per-part visual timing by actual spoken word proportions.

    Audio timeline remains measured precisely from the speech clip; the four
    subheadings are informational cues, never used to claim frame sync.
    """
    words = [max(1, len(p.split())) for p in paragraphs]
    lead = max(0, len(spoken.split()) - sum(words))
    words[0] += lead
    total = max(1, sum(words))
    elapsed = 0
    cuts = []
    for count in words:
        elapsed += count
        cuts.append(round(elapsed / total, 4))
    cuts[-1] = 1.0
    return cuts


def produce(folder: Path) -> dict:
    manifest = folder / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    if data.get("language") != "it" or data.get("synthetic_voice") != "it-IT-ElsaNeural":
        raise ValueError("Lingua o voce non corrispondente")
    stories = data.get("articles")
    segments = data.get("segments")
    if not isinstance(stories, list) or len(stories) < 4 or len(segments or []) != len(stories) + 2:
        raise ValueError("Edizione priva di approfondimenti")
    article_map = {a["id"]: a for a in stories}
    voice = data["synthetic_voice"]

    jingle_voice = folder / "jingle-voce.mp3"
    asyncio.run(speech("Radio Românii din Italia. TG RDI della sera.", voice, jingle_voice))
    bed = folder / "jingle-note.mp3"
    opening = folder / "jingle-iniziale.mp3"
    chime(bed)
    mixing_jingle(bed, jingle_voice, opening)
    clips = [opening]
    elapsed = duration(opening)
    timeline = [{"kind": "jingle", "start_seconds": 0, "end_seconds": round(elapsed, 2)}]
    for index, segment in enumerate(segments):
        if segment.get("kind") not in {"intro", "story", "outro"} or len(segment.get("text", "")) < 30:
            raise ValueError("Segmento TG non valido")
        if index == 0 and segment["kind"] != "intro":
            raise ValueError("Apertura mancante")
        if index == len(segments) - 1 and segment["kind"] != "outro":
            raise ValueError("Chiusura mancante")
        clip = folder / f"voce-{index:02d}.mp3"
        asyncio.run(speech(segment["text"], voice, clip))
        if clip.stat().st_size < 6000:
            raise ValueError("Audio troppo corto")
        length = duration(clip)
        scene = {
            "kind": segment["kind"],
            "start_seconds": round(elapsed, 2),
            "end_seconds": round(elapsed + length, 2),
        }
        if segment["kind"] == "story":
            article = article_map.get(segment.get("id"))
            if not article:
                raise ValueError("Articolo non presente nel manifesto")
            scene.update({
                "id": article["id"], "title": article["title"],
                "category": article["category"], "kicker": article["kicker"],
                "summary": article["paragraphs"][0][:550],
                "sections": [p[:600] for p in article["paragraphs"]],
                "section_ends": section_boundaries(segment["text"], article["paragraphs"]),
                "image": article["image"], "image_notice": article["image_notice"],
                # Only videos from the separately reviewed rights registry enter
                # the public timeline. No arbitrary embedded article players.
                "video": article.get("video"),
                "source_name": article["source_name"],
                "source_url": article["source_url"],
            })
        timeline.append(scene)
        clips.append(clip)
        elapsed += length
    closing = folder / "jingle-finale.mp3"
    chime(closing, descending=True)
    timeline.append({"kind": "end-jingle", "start_seconds": round(elapsed, 2),
                     "end_seconds": round(elapsed + duration(closing), 2)})
    clips.append(closing)
    out = folder / (data["track_title"] + ".mp3")
    merge(clips, out, data["track_title"])
    measured = duration(out)
    if not (240 <= measured <= 2100) or abs(measured - timeline[-1]["end_seconds"]) > 3:
        out.unlink(missing_ok=True)
        raise ValueError(f"Durata TG non valida o disallineata: {measured:.1f}")
    data["audio_duration_seconds"] = round(measured, 2)
    data["audio_filename"] = out.name
    data["timeline"] = timeline
    manifest.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tv = {
        "schema_version": 1, "type": "rdi-daily-tg",
        "language": "it", "edition_id": data["edition_id"],
        "cutoff_at": data["cutoff_at"], "track_title": data["track_title"],
        "audio_duration_seconds": data["audio_duration_seconds"],
        "timeline": timeline, "editorial_notice": data["editorial_notice"],
    }
    (folder / "tv-timing.json").write_text(json.dumps(tv, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Anteprima TG: {out.name}; {measured / 60:.1f} min; {len(stories)} servizi.")
    return data


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default="/tmp/rdi-tg-sera")
    args = parser.parse_args()
    produce(Path(args.folder))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
