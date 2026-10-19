#!/usr/bin/env bash
set -Eeuo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run with sudo"; exit 1; }
[[ -s /etc/radio-youtube/relay.env ]] || { echo "First configure base Youtube relay"; exit 1; }
df -Pk / | awk 'NR==2 {if ($4 < 1500000) {print "Insufficient free space (<1.5GB)"; exit 1}}'
echo "Installing browser capture dependencies. The existing YouTube relay will remain running."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y chromium-browser xvfb xdotool || {
  echo "Chromium package not available. Check installation; original stream is unchanged."
  exit 1
}
# Some Ubuntu releases ship chromium as snap and wrapper.
command -v chromium >/dev/null || { echo "chromium executable not found; visual mode not installed."; exit 1; }
install -m 700 "$(dirname "$0")/visual-relay.sh" /usr/local/sbin/radio-youtube-visual
cat > /etc/systemd/system/radio-youtube-visual.service <<'SERVICE'
[Unit]
Description=Radio Romanii din Italia YouTube browser capture
Wants=network-online.target
After=network-online.target
[Service]
Type=simple
ExecStart=/usr/local/sbin/radio-youtube-visual
Restart=always
RestartSec=10
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
echo "Installed but NOT started. Test using: sudo systemctl start radio-youtube-visual"
echo "Important: STOP radio-youtube.service first; do not send two streams with the same key."
