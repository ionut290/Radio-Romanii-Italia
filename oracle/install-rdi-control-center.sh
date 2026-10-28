#!/usr/bin/env bash
set -euo pipefail
# Install only the dedicated RDI Control Center; leave station and YouTube configuration untouched.
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP=/opt/rdi-control-center
install -d -m 755 "$APP"
install -m 755 "$ROOT/oracle/rdi-control-center.py" "$APP/rdi-control-center.py"
install -m 755 "$ROOT/oracle/rdi-control-center-web.py" "$APP/rdi-control-center-web.py"
install -m 644 "$ROOT/oracle/control-center.html" "$APP/control-center.html"
# The AzuraCast inspector creates a short-lived API credential and revokes it;
# the probe only reads playlist 12 and never writes playlist or media data.
install -m 755 "$ROOT/scripts/deploy-geopolitica-oracle.py" "$APP/deploy-geopolitica-oracle.py"
install -m 644 "$ROOT/scripts/rdi-geopolitica-auth.php" "$APP/rdi-geopolitica-auth.php"
install -d -m 750 /var/lib/rdi-control-center
install -m 644 "$ROOT/oracle/rdi-control-center.service" /etc/systemd/system/rdi-control-center.service
install -m 644 "$ROOT/oracle/rdi-control-center.timer" /etc/systemd/system/rdi-control-center.timer
install -m 644 "$ROOT/oracle/rdi-control-center-web.service" /etc/systemd/system/rdi-control-center-web.service
systemctl daemon-reload
systemctl enable --now rdi-control-center.timer
systemctl enable rdi-control-center-web.service
systemctl restart rdi-control-center-web.service
systemctl restart rdi-control-center.service
systemctl is-active --quiet rdi-control-center.timer
systemctl is-active --quiet rdi-control-center-web.service
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8787/api/status \
  | /usr/bin/python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("schema_version")==2'
systemctl list-timers --no-pager rdi-control-center.timer
echo "RDI Control Center installed. Dashboard listens only on 127.0.0.1:8787."
echo "Open it through SSH: ssh -L 8787:127.0.0.1:8787 ubuntu@<oracle-host>"
echo "No other playlist, YouTube configuration, or stream key was changed."
