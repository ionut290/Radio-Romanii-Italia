#!/usr/bin/env bash
# Explicit manual installer; no Facebook broadcast is started automatically.
set -Eeuo pipefail
if (( EUID != 0 )); then echo "Use: sudo bash facebook-live/setup.sh"; exit 1; fi
[[ -r /etc/radio-youtube/relay.env ]] || { echo "Existing radio settings unavailable"; exit 1; }
command -v ffmpeg >/dev/null || { echo "FFmpeg not installed"; exit 1; }
echo "Enter the RTMPS server URL from Facebook Live Producer (not your Page URL):"
read -r -p "RTMPS server: " fb_server
[[ "$fb_server" == rtmps://* && "$fb_server" != *[$' \t\r\n']* ]] || {
  echo "Invalid RTMPS server address"; exit 1;
}
echo "Paste your Facebook STREAM KEY (input is hidden; never share it in chat):"
read -r -s -p "Facebook stream key: " fb_key
echo
[[ -n "$fb_key" && "$fb_key" != *[$' \t\r\n']* ]] || { echo "Invalid key"; exit 1; }
install -d -m 700 /etc/radio-facebook
umask 077
printf 'FB_RTMPS_URL=%q\nFB_STREAM_KEY=%q\n' "$fb_server" "$fb_key" > /etc/radio-facebook/relay.env
chmod 600 /etc/radio-facebook/relay.env
unset fb_key
install -m 700 "$(dirname "$0")/relay.sh" /usr/local/sbin/rdi-facebook-relay
cat > /etc/systemd/system/rdi-facebook.service <<'SERVICE'
[Unit]
Description=RDI optional independent Facebook Live relay
Wants=network-online.target
After=network-online.target
StartLimitIntervalSec=300
StartLimitBurst=3

[Service]
Type=simple
User=root
ExecStart=/usr/local/sbin/rdi-facebook-relay
Restart=always
RestartSec=20
NoNewPrivileges=true
ProtectSystem=strict

[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
echo "Installed but NOT started or enabled. YouTube and AzuraCast unchanged."
echo "After preparing Facebook Live: sudo systemctl start rdi-facebook.service"
echo "To stop Facebook only: sudo systemctl stop rdi-facebook.service"
