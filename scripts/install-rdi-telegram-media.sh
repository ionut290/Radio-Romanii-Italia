#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "$EUID" -ne 0 ]]; then
  echo "Esegui questo programma con sudo." >&2
  exit 1
fi

# Pinned to the reviewed source revision so GitHub's raw cache cannot serve an older file.
REVISION="8308595aad5513c6979efe333216089fe49b63ea"
BASE="https://raw.githubusercontent.com/ionut290/Radio-Romanii-Italia/$REVISION"
TMP_DIR="$(mktemp -d /tmp/rdi-telegram-media.XXXXXX)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT

echo "Installo PulseAudio per acquisire l'audio di Chromium..."
DEBIAN_FRONTEND=noninteractive apt-get install -y pulseaudio pulseaudio-utils

echo "Scarico i componenti RDI..."
curl -fsSL "$BASE/youtube-live/visual-relay.sh" -o "$TMP_DIR/radio-youtube-visual"
curl -fsSL "$BASE/rdi-live-publisher.py" -o "$TMP_DIR/publish-approved.py"
curl -fsSL "$BASE/rdi-telegram-publish.service" -o "$TMP_DIR/rdi-telegram-publish.service"

install -o root -g root -m 700 "$TMP_DIR/radio-youtube-visual" /usr/local/sbin/radio-youtube-visual
install -o root -g root -m 644 "$TMP_DIR/publish-approved.py" /opt/rdi-telegram-live/publish-approved.py
install -o root -g root -m 644 "$TMP_DIR/rdi-telegram-publish.service" /etc/systemd/system/rdi-telegram-publish.service
install -d -o root -g root -m 755 /var/lib/docker/volumes/azuracast_station_data/_data/rdi-live-media

echo "Aggiungo la rotta pubblica per i soli file approvati..."
cp -a /var/azuracast/varga-custom.conf "/var/azuracast/varga-custom.conf.bak-rdi-media-$(date +%Y%m%d-%H%M%S)"
python3 - <<'PY'
from pathlib import Path

path = Path("/var/azuracast/varga-custom.conf")
text = path.read_text(encoding="utf-8")
marker = "location ^~ /rdi-live-media/ {"
if marker not in text:
    block = """location ^~ /rdi-live-media/ {
    if ($host != radio-romanii-italia.duckdns.org) { return 404; }
    if ($request_method = OPTIONS) { return 204; }
    alias /var/azuracast/stations/rdi-live-media/;
    default_type application/octet-stream;
    types {
        image/jpeg jpg jpeg;
        image/png png;
        image/webp webp;
        video/mp4 mp4 m4v;
        video/webm webm;
        video/quicktime mov;
        audio/mpeg mp3;
        audio/mp4 m4a;
        audio/ogg ogg oga opus;
        audio/wav wav;
    }
    add_header Access-Control-Allow-Origin "https://radioromanii.duckdns.org" always;
    add_header Access-Control-Allow-Methods "GET, HEAD, OPTIONS" always;
    add_header Access-Control-Allow-Headers "Range" always;
    add_header Cache-Control "no-store" always;
}
"""
    path.write_text(text.rstrip() + "\n\n" + block, encoding="utf-8")
else:
    print("La rotta media esiste già; la lascio invariata.")
PY

docker exec azuracast nginx -t
docker exec azuracast nginx -s reload

systemctl stop rdi-telegram-publish.timer || true
systemctl daemon-reload
systemctl start rdi-telegram-publish.service
systemctl start rdi-telegram-publish.timer

echo "Riavvio il relay YouTube per attivare la cattura audio; la diretta potrebbe riconnettersi per qualche secondo."
systemctl restart radio-youtube-visual.service
systemctl --no-pager --full status radio-youtube-visual.service
systemctl --no-pager is-active rdi-telegram-publish.timer
