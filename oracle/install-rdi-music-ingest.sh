#!/usr/bin/env bash
# Add newly uploaded songs to a private read-only rotation pool, not to live.
set -euo pipefail
test "$EUID" -eq 0 || { echo "Root required" >&2; exit 1; }
SRC="$(cd "$(dirname "$0")/.." && pwd)"
APP=/opt/rdi-music-dj
install -d -m 755 "$APP"
install -m 644 "$SRC/scripts/rdi_music_ingest.py" "$APP/rdi_music_ingest.py"
install -m 644 "$SRC/scripts/rdi_music_rotation.py" "$APP/rdi_music_rotation.py"
install -m 644 "$SRC/scripts/rdi_music_dj.py" "$APP/rdi_music_dj.py"
install -m 644 "$SRC/scripts/rdi-music-dj.html" "$APP/rdi-music-dj.html"
install -m 644 "$SRC/oracle/rdi-music-ingest.service" /etc/systemd/system/rdi-music-ingest.service
install -m 644 "$SRC/oracle/rdi-music-ingest.timer" /etc/systemd/system/rdi-music-ingest.timer
python3 -m py_compile "$APP"/rdi_music_{ingest,rotation,dj}.py
systemctl daemon-reload
# Inventory is always local; no credentials to control station playlists.
systemctl enable --now rdi-music-ingest.timer
systemctl is-active --quiet rdi-music-ingest.timer
# Perform first synchronous scan of live station media.
systemctl start rdi-music-ingest.service
systemctl is-failed --quiet rdi-music-ingest.service && exit 1 || true
systemctl restart rdi-music-dj-web.service
systemctl is-active --quiet rdi-music-dj-web.service
for try in $(seq 1 20); do
 if curl -fsS --max-time 8 http://127.0.0.1:8788/api/rotation \
   -o /tmp/rdi-ingest-rotation.json 2>/dev/null; then break; fi
 sleep 1
done
python3 - <<'PY'
import json
from pathlib import Path
p=Path("/tmp/rdi-ingest-rotation.json")
assert p.is_file()
d=json.loads(p.read_text())
assert d["schema_version"]==2 and d["read_only"] and d["playlist_writes"]==0
assert d["automatic_broadcast_enabled"] is False and d["ready_for_live"] is False
assert d["duplicate_tracks"]==0 and d["covers_all_24h_in_blocks"]
assert d["live_index_verified"] is True
print("RDI_LIVE_MUSIC_ROTATION_POOL="+str(d["pool_tracks_total"]))
print("RDI_LIVE_MUSIC_NEW_TRACKS="+str(d["new_tracks_in_pool"]))
print("RDI_LIVE_MUSIC_TODAY_SELECTION="+str(d["total_unique_tracks"]))
print("RDI_LIVE_MUSIC_PLAYLIST_WRITES=0")
PY
rm -f /tmp/rdi-ingest-rotation.json
echo "RDI_MUSIC_LIVE_INGEST_TIMER=ENABLED"
