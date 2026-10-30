#!/usr/bin/env bash
# Install RDI DJ in SHADOW mode only: no AzuraCast station mutation or playlist credentials.
set -euo pipefail
test "$EUID" -eq 0 || { echo "Run with sudo/root" >&2; exit 1; }
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"
TARGET=/opt/rdi-music-dj
USER_HOME=/home/ubuntu/rdi-music
install -d -m 755 "$TARGET"
install -d -o ubuntu -g ubuntu -m 700 "$USER_HOME"
for name in rdi_music_scan.py rdi_music_rhythm.py rdi_music_features.py rdi_music_preview.py rdi_music_dj.py; do
  install -m 644 "$SOURCE/scripts/$name" "$TARGET/$name"
done
install -m 644 "$SOURCE/scripts/rdi-music-dj.html" "$TARGET/rdi-music-dj.html"
install -m 644 "$SOURCE/oracle/rdi-music-dj-analyze.service" /etc/systemd/system/rdi-music-dj-analyze.service
install -m 644 "$SOURCE/oracle/rdi-music-dj-analyze.timer" /etc/systemd/system/rdi-music-dj-analyze.timer
install -m 644 "$SOURCE/oracle/rdi-music-dj-web.service" /etc/systemd/system/rdi-music-dj-web.service
python3 -m py_compile "$TARGET/"rdi_music_{scan,rhythm,features,preview,dj}.py
# The report builder uses an existing SQLite database if present; initially empty is fine.
runuser -u ubuntu -- env HOME=/home/ubuntu python3 "$TARGET/rdi_music_dj.py" report
systemctl daemon-reload
systemctl enable --now rdi-music-dj-analyze.timer
systemctl enable rdi-music-dj-web.service
systemctl restart rdi-music-dj-web.service
systemctl is-active --quiet rdi-music-dj-analyze.timer
systemctl is-active --quiet rdi-music-dj-web.service
curl -fsS --max-time 8 http://127.0.0.1:8788/api/report |
  python3 -c 'import json,sys;x=json.load(sys.stdin);assert x["read_only"] and x["playlist_writes"]==0 and x["schema_version"]==1;print("DJ_REPORT=PRIVATE_READ_ONLY");print("DJ_EXISTING_TRACKS=",x["total_music"])'
curl -fsS --max-time 8 http://127.0.0.1:8788/ | grep -q 'DJ intelligente'
echo "RDI_DJ_DASHBOARD=http://127.0.0.1:8788 (SSH port-forward required)"
echo "RDI_DJ_TIMER=ACTIVE"
echo "RDI_DJ_MODE=SHADOW_NO_PLAYLIST_CHANGES"
# Start a bounded scan in the background under the same low-priority systemd constraints.
systemctl start --no-block rdi-music-dj-analyze.service
