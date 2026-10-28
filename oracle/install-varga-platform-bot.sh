#!/usr/bin/env bash
set -euo pipefail
if [[ "${EUID}" -ne 0 ]]; then echo "Run as root" >&2; exit 1; fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP=/opt/varga-platform-bot
install -d -m 755 "$APP"
install -m 755 "$ROOT/oracle/varga-platform-bot.py" "$APP/varga-platform-bot.py"
install -m 755 "$ROOT/oracle/varga-platform-dashboard.py" "$APP/varga-platform-dashboard.py"
install -m 644 "$ROOT/oracle/varga-platform-dashboard.html" "$APP/varga-platform-dashboard.html"
install -d -m 750 /var/lib/varga-platform-bot
install -m 644 "$ROOT/oracle/varga-platform-bot.service" /etc/systemd/system/varga-platform-bot.service
install -m 644 "$ROOT/oracle/varga-platform-bot.timer" /etc/systemd/system/varga-platform-bot.timer
install -m 644 "$ROOT/oracle/varga-platform-dashboard.service" /etc/systemd/system/varga-platform-dashboard.service
systemctl daemon-reload
systemctl enable --now varga-platform-bot.timer
systemctl enable --now varga-platform-dashboard.service
systemctl start varga-platform-bot.service
systemctl is-active --quiet varga-platform-bot.timer
systemctl is-active --quiet varga-platform-dashboard.service
curl --fail --silent --show-error --max-time 5 http://127.0.0.1:8790/api/status \
  | /usr/bin/python3 -c 'import json,sys; d=json.load(sys.stdin); assert d.get("schema_version")==1 and set(d.get("platforms",{}))=={"cantieri","gestionale"}'
systemctl list-timers --no-pager varga-platform-bot.timer
echo "Dedicated Varga bot installed. Dashboard listens only on 127.0.0.1:8790."
echo "SSH tunnel: ssh -L 8790:127.0.0.1:8790 ubuntu@<oracle-host>"
