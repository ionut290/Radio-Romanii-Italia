#!/usr/bin/env bash
# RDI safe, read-only AzuraCast probe. Never print credentials or file contents.
set -euo pipefail
echo "RDI_ORACLE_PROBE=begin"
echo "UTC_DATE=$(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "DOCKER_CONTAINERS:"
docker ps --format '  {{.Names}}  {{.Status}}' | head -n 20
echo "AZURACAST_PLAYLIST_API_CODE=$(curl -k -sS -o /dev/null -w '%{http_code}' --max-time 7 https://radio-romanii-italia.duckdns.org/api/station/1/playlists || true)"
echo "HOST_STATION_MOUNT:"
python3 - <<'PY'
import json, subprocess, pathlib
ps=subprocess.run(["docker","ps","--format","{{.ID}}"],capture_output=True,text=True,check=True).stdout.split()
for id in ps:
  result=subprocess.run(["docker","inspect","--format","{{json .Mounts}}",id],capture_output=True,text=True)
  if result.returncode: continue
  for m in json.loads(result.stdout or "[]"):
    dest=m.get("Destination","")
    if dest=="/var/azuracast/stations":
      base=pathlib.Path(m["Source"])
      media=base/"radio-romanii-italia"/"media"
      print("station_mount_found=",base.is_dir(),"media_found=",media.is_dir())
      if media.is_dir():
        print("station_media_directories=",sorted(p.name for p in media.iterdir() if p.is_dir())[:24])
PY
echo "AZURACAST_CLI_COMMANDS:"
if docker ps --format '{{.Names}}' | grep -qx azuracast; then
  docker exec azuracast sh -c 'if command -v azuracast_cli >/dev/null 2>&1; then azuracast_cli list --raw 2>/dev/null | grep -E "azuracast:(station|api|account|sync|radio)" | head -n 32; elif test -e /var/azuracast/www/bin/console; then php /var/azuracast/www/bin/console list --raw 2>/dev/null | grep -E "azuracast:(station|api|account|sync|radio)" | head -n 32; fi' || true
fi
echo "RDI_ORACLE_PROBE=end"
