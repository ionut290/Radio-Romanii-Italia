#!/usr/bin/env bash
set -euo pipefail
# Install only the dedicated RDI Control Center; leave other services untouched.
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run as root" >&2
  exit 1
fi
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install -d -m 755 /opt/rdi-control-center
install -m 755 "$ROOT/oracle/rdi-control-center.py" /opt/rdi-control-center/rdi-control-center.py
install -d -m 750 /var/lib/rdi-control-center
install -m 644 "$ROOT/oracle/rdi-control-center.service" /etc/systemd/system/rdi-control-center.service
install -m 644 "$ROOT/oracle/rdi-control-center.timer" /etc/systemd/system/rdi-control-center.timer
systemctl daemon-reload
systemctl enable --now rdi-control-center.timer
systemctl list-timers --no-pager rdi-control-center.timer
echo "RDI Control Center timer installed. Existing radio and YouTube services unchanged."
