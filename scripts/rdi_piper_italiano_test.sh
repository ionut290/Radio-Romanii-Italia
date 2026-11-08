#!/usr/bin/env bash
# RDI - prova isolata del conduttore Piper TTS italiano.
# Non modifica AzuraCast, FFmpeg, Chromium, le playlist o le pagine LIVE.
set -euo pipefail

ACTION="${1:---check}"
BASE="${HOME}/rdi-piper-test"
VENV="${BASE}/venv"
DATA="${BASE}/voices"
OUT="${BASE}/rdi-conduttore-test-it.wav"
VOICE="it_IT-serena-medium"

log(){ printf '[RDI Piper] %s\n' "$*"; }

log "Architettura: $(uname -m); sistema: $(uname -s)"
log "Python: $(python3 --version 2>&1 || true)"
log "RAM disponibile (MiB): $(awk '/MemAvailable:/ { printf "%d", $2/1024 }' /proc/meminfo)"
log "Disco disponibile nella home (MiB): $(df -Pm "$HOME" | awk 'NR==2 {print $4}')"
log "Nessun processo radio o diretta viene modificato."

case "$ACTION" in
  --check)
    log "Modalità diagnostica: nessuna installazione eseguita."
    if python3 -m venv --help >/dev/null 2>&1; then
      log "Modulo venv disponibile."
    else
      log "Modulo venv non disponibile; verificare python3-venv."
    fi
    ;;
  --test)
    [[ "$(uname -s)" == "Linux" ]] || { log "Questo script richiede Linux."; exit 2; }
    [[ "$(uname -m)" == "aarch64" || "$(uname -m)" == "x86_64" ]] || { log "Architettura da verificare: $(uname -m)"; exit 2; }
    mem="$(awk '/MemAvailable:/ {print int($2/1024)}' /proc/meminfo)"
    disk="$(df -Pm "$HOME" | awk 'NR==2 {print $4}')"
    if (( mem < 1400 || disk < 1100 )); then
      log "Test bloccato per proteggere la diretta: servono almeno 1400 MiB RAM disponibili e 1100 MiB liberi nella home."
      exit 3
    fi
    mkdir -p "$BASE" "$DATA"
    python3 -m venv "$VENV"
    log "Installazione Piper isolata nel virtualenv (bassa priorità CPU)."
    nice -n 15 timeout 240 "$VENV/bin/python" -m pip install --disable-pip-version-check --only-binary=:all: 'piper-tts==1.8.0'
    log "Scaricamento della sola voce italiana Serena."
    ( cd "$DATA"; nice -n 15 timeout 180 "$VENV/bin/python" -m piper.download_voices "$VOICE" )
    log "Generazione WAV test; nessuna messa in onda."
    nice -n 15 timeout 150 "$VENV/bin/python" -m piper -m "$VOICE" --data-dir "$DATA" -f "$OUT" -- 'Buongiorno e benvenuti su Radio Românii din Italia. Sono la voce sperimentale del vostro conduttore digitale. Questo è soltanto un test di pronuncia e qualità audio, non è una trasmissione in diretta.'
    log "File audio creato: $OUT"
    ls -lh "$OUT"
    ;;
  *) log "Uso: bash $0 --check oppure bash $0 --test"; exit 2 ;;
esac
