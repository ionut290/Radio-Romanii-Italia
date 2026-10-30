#!/usr/bin/env python3
"""Crea un provino comico RDI con la voce Elsa e una voce telefonica italiana."""
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

TURNS = [
    ("it-IT-ElsaNeural", "Sono le dodici e questo è Pronto RDI: il centralino dei piccoli drammi quotidiani. In linea c’è Laura, alle prese con un mobile nuovo. Ciao Laura, raccontaci tutto."),
    ("it-IT-DiegoNeural", "Ciao! Ho scritto nel gruppo del condominio: qualcuno ha una brugola? Il mobile è ancora in scatola e io ho già perso le istruzioni."),
    ("it-IT-ElsaNeural", "E qualcuno ti ha risposto?"),
    ("it-IT-DiegoNeural", "In sette. Il primo mi ha mandato il numero dell’idraulico. La signora del terzo ha scritto: io ho la rucola, va bene lo stesso? E l’amministratore: per le brugole bisogna aprire una pratica."),
    ("it-IT-ElsaNeural", "Una pratica per una vite?"),
    ("it-IT-DiegoNeural", "Sì. Mi è arrivata un’email: richiesta presa in carico. Poi un’altra: la brugola è in ferie fino a lunedì."),
    ("it-IT-ElsaNeural", "E il mobile?"),
    ("it-IT-DiegoNeural", "L’ho montato da solo. Mi avanzano tre viti, un ripiano e un gancio misterioso. Però sta in piedi."),
    ("it-IT-ElsaNeural", "Allora è un mobile moderno: si regge sulla fiducia."),
    ("it-IT-DiegoNeural", "È salita la signora con la rucola. Ha detto: se non sistemiamo il mobile, almeno pranziamo."),
    ("it-IT-ElsaNeural", "Questa è solidarietà condominiale: magari non trovi la brugola, ma trovi il pranzo. E il mobile?"),
    ("it-IT-DiegoNeural", "Adesso è perfetto. Ho usato la rucola per segnare quale ripiano non devo toccare."),
    ("it-IT-ElsaNeural", "Avete ascoltato una telefonata simulata di Pronto RDI. I personaggi sono inventati, i piccoli drammi molto plausibili. Domani a mezzogiorno un’altra chiamata. Bună ziua e buon pranzo!"),
]

async def main() -> None:
    clips: list[Path] = []
    for idx, (voice, text) in enumerate(TURNS, 1):
        path = WORK / f"line-{idx:02}.mp3"
        await edge_tts.Communicate(text, voice, rate="-3%").save(str(path))
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
    output = OUT / "RDI-Pronto-RDI-prova.mp3"
    subprocess.run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat),
        "-c:a", "libmp3lame", "-b:a", "192k", "-ar", "44100",
        "-metadata", "title=Pronto RDI - puntata prova",
        "-metadata", "artist=Radio Românii din Italia",
        str(output)
    ], check=True)
    duration = float(MP3(str(output)).info.length)
    (OUT / "metadata.json").write_text(json.dumps({
        "title": "Pronto RDI - puntata prova",
        "duration_seconds": round(duration, 1),
        "host_voice": "it-IT-ElsaNeural",
        "caller_voice": "it-IT-DiegoNeural",
        "fiction_notice": "Telefonata simulata; personaggi inventati."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"PROVA_PRONTO_RDI={duration:.1f}s")

if __name__ == "__main__":
    asyncio.run(main())
