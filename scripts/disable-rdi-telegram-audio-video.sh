#!/usr/bin/env bash
set -Eeuo pipefail

if [ "$EUID" -ne 0 ]; then
  echo "Esegui questo programma con sudo." >&2
  exit 1
fi

REVISION="b784f852a2572fc5976e8a490d8a2df9e9a5da38"
BASE="https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/$REVISION"
TMP_DIR="$(mktemp -d /tmp/rdi-disable-av.XXXXXX)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Scarico la configurazione senza audio e video Telegram..."
curl -fsSL "$BASE/youtube-live/visual-relay.sh" -o "$TMP_DIR/radio-youtube-visual"
curl -fsSL "$BASE/rdi-live-publisher.py" -o "$TMP_DIR/publish-approved.py"
curl -fsSL "$BASE/rdi-telegram-publish.service" -o "$TMP_DIR/rdi-telegram-publish.service"

install -o root -g root -m 700 "$TMP_DIR/radio-youtube-visual" /usr/local/sbin/radio-youtube-visual
install -o root -g root -m 644 "$TMP_DIR/publish-approved.py" /opt/rdi-telegram-live/publish-approved.py
install -o root -g root -m 644 "$TMP_DIR/rdi-telegram-publish.service" /etc/systemd/system/rdi-telegram-publish.service

echo "Disattivo audio e video nel bot; testo e foto restano disponibili..."
python3 - <<'PY'
from pathlib import Path

path = Path("/opt/rdi-telegram-live/receiver.py")
text = path.read_text(encoding="utf-8")
marker = "RDI_DISABLE_AUDIO_VIDEO_20261030"
anchor = 'text = (msg.get("text") or "").strip()\n'
guard = """    # RDI_DISABLE_AUDIO_VIDEO_20261030
    document = msg.get("document") or {}
    mime_type = document.get("mime_type", "") if isinstance(document, dict) else ""
    if any(msg.get(key) for key in ("voice", "audio", "video", "video_note")) or mime_type.startswith(("audio/", "video/")):
        reply(chat_id, "Al momento il bot accetta messaggi di testo e foto; audio e video non sono disponibili.")
        return
"""
if marker not in text:
    if text.count(anchor) != 1:
        raise SystemExit("Non trovo il punto sicuro per aggiornare receiver.py; nessuna modifica applicata al bot.")
    backup = path.with_suffix(".py.bak-disable-av")
    if not backup.exists():
        backup.write_text(text, encoding="utf-8")
    path.write_text(text.replace(anchor, anchor + guard, 1), encoding="utf-8")
PY

find /var/lib/docker/volumes/azuracast_station_data/_data/rdi-live-media -type f \( -iname '*.mp3' -o -iname '*.m4a' -o -iname '*.ogg' -o -iname '*.oga' -o -iname '*.opus' -o -iname '*.wav' -o -iname '*.mp4' -o -iname '*.webm' -o -iname '*.m4v' -o -iname '*.mov' \) -delete 2>/dev/null || true

systemctl daemon-reload
systemctl restart rdi-telegram-live.service
systemctl start rdi-telegram-publish.service
systemctl start rdi-telegram-publish.timer
echo "Riavvio la diretta YouTube con il solo audio AzuraCast..."
systemctl restart radio-youtube-visual.service
systemctl --no-pager is-active rdi-telegram-live.service
systemctl --no-pager is-active rdi-telegram-publish.timer
systemctl --no-pager is-active radio-youtube-visual.service
