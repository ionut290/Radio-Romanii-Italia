#!/usr/bin/env python3
"""Crea una prova comica RDI più conversazionale con voci italiane Edge TTS."""
from __future__ import annotations
import asyncio
import json
import subprocess
from pathlib import Path
import imageio_ffmpeg
import edge_tts
from mutagen.mp3 import MP3

OUT = Path("demo-output")
WORK = Path("/tmp/rdi-pronto-rdi-demo")
OUT.mkdir(parents=True, exist_ok=True)
WORK.mkdir(parents=True, exist_ok=True)
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
HOST = "it-IT-IsabellaNeural"
CALLER = "it-IT-DiegoNeural"

TURNS = [
    (HOST, "Ciao a tutti, sono le dodici! Benvenuti a Pronto RDI, il centralino dei piccoli drammi quotidiani. Oggi è in linea Laura, che ha appena ricevuto un mobile da montare. Laura, dimmi: com'è andata?"),
    (CALLER, "Ciao! Male, ma con grande dignità. Ho aperto la scatola e ho trovato quarantadue pezzi di legno, dodici viti e un foglio con un omino sorridente. Lui sembrava sapere cosa fare. Io no."),
    (HOST, "Hai chiesto aiuto?"),
    (CALLER, "Ho scritto nel gruppo del condominio: «Qualcuno ha una brugola?» La signora del terzo ha risposto: «Io ho la rucola, va bene lo stesso?» L'amministratore invece mi ha detto di aprire una pratica."),
    (HOST, "Una pratica per una brugola?"),
    (CALLER, "Esatto. Dopo dieci minuti mi è arrivata una mail: richiesta presa in carico. Dopo altri dieci: la brugola è in ferie fino a lunedì. Intanto il mobile era ancora sdraiato sul pavimento."),
    (HOST, "E alla fine come hai risolto?"),
    (CALLER, "La signora è salita con l'insalata e suo marito con gli attrezzi. In mezz'ora abbiamo montato tutto. Ci avanzano tre viti, ma il mobile sta in piedi e loro sono rimasti a pranzo."),
    (HOST, "Questa è la vera solidarietà condominiale: magari non trovi la brugola, ma trovi due vicini e un piatto pronto. Grazie Laura!"),
    (CALLER, "Grazie a voi. Se domani sentite un rumore, non sono io: è il mobile che sta riflettendo sulle tre viti avanzate."),
    (HOST, "Avete ascoltato una telefonata simulata di Pronto RDI: i personaggi sono inventati, le piccole avventure molto plausibili. Torniamo domani a mezzogiorno. Bună ziua e buon pranzo!"),
]

async def main() -> None:
    clips: list[Path] = []
    voices = set(await edge_tts.list_voices())
    available = {v.get("ShortName") for v in voices}
    for voice in (HOST, CALLER):
        if voice not in available:
            raise RuntimeError(f"Voce Edge TTS non disponibile: {voice}")

    for idx, (voice, text) in enumerate(TURNS, 1):
        path = WORK / f"line-{idx:02}.mp3"
        await edge_tts.Communicate(text, voice, rate="+1%").save(str(path))
        if not path.exists() or path.stat().st_size < 1000:
            raise RuntimeError(f"Voce non generata per la battuta {idx}")
        clips.append(path)

    ring = WORK / "squillo.mp3"
    subprocess.run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-i",
        "aevalsrc='(sin(2*PI*440*t)+sin(2*PI*480*t))*0.12':s=44100:d=1.2",
        "-af", "volume='if(lt(mod(t,0.6),0.28),1,0)'",
        "-c:a", "libmp3lame", "-b:a", "192k", str(ring)
    ], check=True)
    clips.insert(1, ring)

    concat = WORK / "concat.txt"
    concat.write_text("".join(f"file '{p.as_posix()}'\n" for p in clips), encoding="utf-8")
    output = OUT / "RDI-Pronto-RDI-prova-v2.mp3"
    subprocess.run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
        "-metadata", "title=Pronto RDI - provino conversazionale",
        "-metadata", "artist=Radio Românii din Italia",
        str(output)
    ], check=True)
    duration = float(MP3(str(output)).info.length)
    (OUT / "metadata.json").write_text(json.dumps({
        "title": "Pronto RDI - provino conversazionale",
        "duration_seconds": round(duration, 1),
        "host_voice": HOST,
        "caller_voice": CALLER,
        "fiction_notice": "Telefonata simulata; personaggi inventati."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PROVA_PRONTO_RDI={duration:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
