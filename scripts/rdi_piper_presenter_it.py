#!/usr/bin/env python3
"""RDI Italian Piper presenter: offline audio preparation, NEVER on-air deployment.

Reuses the verified ~/rdi-piper-test/venv and it_IT-serena-medium.
Outputs immutable WAV files + JSON manifest in ~/rdi-piper-test/annunci.
Does not connect to AzuraCast, YouTube, FFmpeg, or GitHub.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
from zoneinfo import ZoneInfo

ROME = ZoneInfo("Europe/Rome")
HOME = Path.home()
BASE = HOME / "rdi-piper-test"
PIPER = BASE / "venv/bin/python"
VOICES = BASE / "voices"
OUTPUT = BASE / "annunci"
MODEL = "it_IT-serena-medium"
MAX_TEXT = 650
SCRIPTS = {
    "apertura": "Buongiorno, benvenuti su Radio Românii din Italia. Una voce che unisce le persone, attraverso la musica, le notizie e le storie della nostra comunità.",
    "notizie": "È il momento dell'informazione su Radio Românii din Italia. Le notizie e i collegamenti alle fonti sono disponibili sul nostro sito. Restate con noi.",
    "top3": "E ora, su Radio Românii din Italia, scopriamo la classifica RDI AI Music. Le posizioni sono scelte dai voti degli ascoltatori. Buon ascolto!",
    "storia": "Questa è RDI Storia. Un viaggio negli avvenimenti che hanno segnato il passato, per capire meglio il nostro presente.",
    "musica": "La musica continua su Radio Românii din Italia. Grazie di essere con noi, ovunque vi troviate.",
    "sera": "Buonasera da Radio Românii din Italia. Continuiamo insieme tra musica, racconti e aggiornamenti dalla nostra comunità.",
    "notte": "È notte su Radio Românii din Italia. Lasciatevi accompagnare dalla nostra selezione musicale. Buon ascolto.",
}

def generate(now: dt.datetime, dry_run: bool) -> list[dict]:
    if not PIPER.is_file():
        raise SystemExit("Piper non installato: eseguire prima il test iniziale.")
    if not VOICES.is_dir():
        raise SystemExit("Voce Serena non trovata nella cartella di prova.")
    if not any(VOICES.glob(MODEL + ".onnx*")):
        raise SystemExit("Modello Serena mancante; nessun download automatico.")
    entries = []
    for key, words in SCRIPTS.items():
        if not 5 < len(words) <= MAX_TEXT:
            raise ValueError(f"Testo fuori limite per {key}")
        digest = hashlib.sha256((MODEL + "\0" + words).encode()).hexdigest()[:16]
        filename = f"{key}-{digest}.wav"
        dest = OUTPUT / filename
        entries.append({"slot": key, "audio_filename": filename, "text": words, "sha256_text": digest, "ready": dest.is_file() and dest.stat().st_size > 2048})
        if dry_run or entries[-1]["ready"]:
            continue
        OUTPUT.mkdir(parents=True, exist_ok=True)
        fd, tmpname = tempfile.mkstemp(dir=OUTPUT, prefix=".piper-", suffix=".wav")
        os.close(fd)
        tmp = Path(tmpname)
        try:
            cmd = [str(PIPER), "-m", "piper", "-m", MODEL, "--data-dir", str(VOICES), "-f", str(tmp), "--", words]
            # Low process priority; CPU thread cap limits contention with LIVE.
            env = dict(os.environ, OMP_NUM_THREADS="2", OPENBLAS_NUM_THREADS="2")
            result = subprocess.run(["nice", "-n", "15", *cmd], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=120, check=False)
            if result.returncode != 0 or tmp.stat().st_size < 2048:
                raise RuntimeError(f"Piper non ha generato {key}: {result.stderr[-700:]}")
            tmp.replace(dest)
            entries[-1]["ready"] = True
        finally:
            tmp.unlink(missing_ok=True)
    if not dry_run:
        manifest = {
            "generated_at": now.astimezone(ROME).isoformat(),
            "language": "it",
            "voice": MODEL,
            "state": "PREVIEW_ONLY_NOT_ON_AIR",
            "license_review_required": True,
            "announcements": entries,
        }
        OUTPUT.mkdir(parents=True, exist_ok=True)
        temporary = OUTPUT / ".manifest.tmp"
        temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(OUTPUT / "manifest.json")
    return entries

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Verifica testi e file senza generare nulla")
    args = parser.parse_args()
    result = generate(dt.datetime.now(dt.timezone.utc), args.dry_run)
    print(json.dumps({"mode": "dry-run" if args.dry_run else "preview-only", "folder": str(OUTPUT), "count": len(result), "ready": sum(bool(x["ready"]) for x in result), "on_air": False}, ensure_ascii=False))
    if not args.dry_run:
        print("Nessun audio è stato inviato ad AzuraCast o YouTube.")

if __name__ == "__main__":
    main()
