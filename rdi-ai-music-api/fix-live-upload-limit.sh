#!/usr/bin/env bash
# RDI AI MUSIC: safely allow a complete 10-song batch on the live Oracle API.
# Usage (on the Oracle server): sudo bash fix-live-upload-limit.sh
set -Eeuo pipefail

APP="/opt/rdi-ai-music-api/app.py"
SERVICE="rdi-ai-music.service"
[[ $(id -u) -eq 0 ]] || { echo "ERROR: run using sudo bash." >&2; exit 1; }
[[ -f "$APP" ]] || { echo "ERROR: missing live API file $APP" >&2; exit 1; }
command -v systemctl >/dev/null || { echo "ERROR: systemctl unavailable" >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: python3 unavailable" >&2; exit 1; }

BACKUP="$APP.bak-batch10-$(date -u +%Y%m%dT%H%M%SZ)"
cp -p -- "$APP" "$BACKUP"
echo "Backup created: $BACKUP"

rollback() {
  echo "ERROR: validation or service check failed. Restoring backup." >&2
  cp -p -- "$BACKUP" "$APP"
  systemctl restart "$SERVICE" || true
}
trap rollback ERR

python3 - "$APP" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
source = path.read_text(encoding="utf-8")
# Case 1: original production backend with RATE_MAX=6.
match = re.search(r"(?m)^RATE_MAX\s*=\s*(\d+)\s*$", source)
if match:
    value = int(match.group(1))
    if value == 12:
        print("Already configured for 12 hourly submissions.")
    elif value == 6:
        patched = source[:match.start()] + "RATE_MAX=12" + source[match.end():]
        path.write_text(patched, encoding="utf-8")
        print("Changed production submission limit: 6 -> 12/hour.")
    else:
        raise SystemExit(f"Unexpected configured RATE_MAX={value}. Not changing automatically.")
# Case 2: new source supports environment overrides and defaults to 12.
elif 'RDI_AI_SUBMISSION_RATE_MAX' in source:
    match_default = re.search(r'RDI_AI_SUBMISSION_RATE_MAX","(\d+)"', source)
    if not match_default or int(match_default.group(1)) < 10:
        raise SystemExit("Source uses an unrecognized rate-limit default.")
    print("Source already includes configurable 12/hour submission limit.")
else:
    raise SystemExit("RATE_MAX setting not found. Not modifying unexpected server code.")
PY

python3 -m py_compile "$APP"
systemctl restart "$SERVICE"
sleep 2
systemctl is-active --quiet "$SERVICE"
curl --fail --silent --show-error --max-time 8 "http://127.0.0.1:8766/api/ai-music/health"
echo
echo "SUCCESS: RDI AI MUSIC backend restarted and is healthy."
echo "Ten uploads can now fit inside the per-IP hourly limit."
echo "All existing submissions and vote data are preserved."
trap - ERR
