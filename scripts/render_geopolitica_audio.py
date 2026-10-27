#!/usr/bin/env python3
"""Create a broadcast-ready MP3 from an editorial RDI geopolitical script.

Audio is generated in CI as a PREVIEW; no AzuraCast playlists are changed.
This uses a synthetic voice (not a human presenter's identity) and an
original three-note chime, not a third-party copyrighted jingle.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import subprocess
from pathlib import Path


def cmd(*args: str) -> None:
    subprocess.run(list(args), check=True, stdout=subprocess.DEVNULL)


def chime(path: Path, descending: bool = False) -> None:
    frequencies = [660, 550, 440] if descending else [440, 550, 660]
    inputs = []
    for frequency in frequencies:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={frequency}:sample_rate=44100:duration=2.3"]
    filters = (
        "[0:a]volume=0.025,adelay=0|0[a0];"
        "[1:a]volume=0.023,adelay=480|480[a1];"
        "[2:a]volume=0.020,adelay=960|960[a2];"
        "[a0][a1][a2]amix=inputs=3:duration=longest,"
        "afade=t=in:st=0:d=0.15,afade=t=out:st=1.25:d=0.95,"
        "aformat=channel_layouts=stereo[out]"
    )
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *inputs,
        "-filter_complex", filters, "-map", "[out]", "-c:a", "libmp3lame",
        "-b:a", "160k", str(path))


async def speech(text: str, voice: str, path: Path) -> None:
    import edge_tts
    await edge_tts.Communicate(text, voice, rate="-5%").save(str(path))


def duration(path: Path) -> float:
    p = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nokey=1:noprint_wrappers=1", str(path)
    ], text=True)
    return float(p.strip())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default="/tmp/rdi-geopolitica")
    args = parser.parse_args()
    folder = Path(args.folder)
    data = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    transcript = (folder / "bulletin.txt").read_text(encoding="utf-8").strip()
    if len(transcript) < 200 or data.get("story_count", 0) < 1:
        raise ValueError("No viable editorial script")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        raise RuntimeError("FFmpeg and FFprobe required")
    voice = {"ro": "ro-RO-AlinaNeural", "it": "it-IT-ElsaNeural"}[data["language"]]
    speech_path = folder / "narration.mp3"
    asyncio.run(speech(transcript, voice, speech_path))
    if speech_path.stat().st_size < 10_000:
        raise ValueError("Speech synthesis returned empty/invalid media")
    intro = folder / "opening.mp3"
    outro = folder / "closing.mp3"
    chime(intro)
    chime(outro, descending=True)
    final = folder / "rdi-geopolitica.mp3"
    filters = (
        "[0:a]aresample=44100,aformat=channel_layouts=stereo[a0];"
        "[1:a]aresample=44100,aformat=channel_layouts=stereo,"
        "loudnorm=I=-18:TP=-1.5:LRA=11[a1];"
        "[2:a]aresample=44100,aformat=channel_layouts=stereo[a2];"
        "[a0][a1][a2]concat=n=3:v=0:a=1[out]"
    )
    cmd("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(intro),
        "-i", str(speech_path), "-i", str(outro), "-filter_complex", filters,
        "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k",
        "-ar", "44100", str(final))
    seconds = duration(final)
    if not 40 <= seconds <= 420:
        final.unlink(missing_ok=True)
        raise ValueError(f"Unexpected bulletin duration: {seconds:.1f} sec")
    data["audio_duration_seconds"] = round(seconds, 1)
    data["synthetic_voice"] = voice
    (folder / "manifest.json").write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"RDI geopolitical audio preview: {final} ({seconds:.0f}s), synthetic voice {voice}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
