#!/usr/bin/env bash
set -Eeuo pipefail

# Install a separate, restartable YouTube relay; AzuraCast is not modified.
if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo bash youtube-live/setup.sh"
  exit 1
fi

command -v ffmpeg >/dev/null || {
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y ffmpeg
}
command -v systemctl >/dev/null || { echo "systemd required"; exit 1; }

install -d -m 700 /etc/radio-youtube
DEFAULT_SOURCE="https://radio-romanii-italia.duckdns.org/listen/radio-romanii-italia/radio.mp3"
read -r -p "Radio source URL [${DEFAULT_SOURCE}]: " SOURCE
SOURCE="${SOURCE:-$DEFAULT_SOURCE}"
[[ "$SOURCE" == https://* || "$SOURCE" == http://* ]] || { echo "Source URL must be http(s)"; exit 1; }

echo "Paste your YouTube stream key below (input hidden; never commit it to GitHub)."
read -r -s -p "YouTube stream key: " KEY
echo
[[ -n "$KEY" && "$KEY" != *[[:space:]]* && "$KEY" != *"/"* ]] || { echo "Invalid stream key"; exit 1; }

# Restrict secrets to root. The key is NOT stored in the public repository.
umask 077
printf 'SOURCE_URL=%q\nYOUTUBE_KEY=%q\n' "$SOURCE" "$KEY" > /etc/radio-youtube/relay.env
chmod 600 /etc/radio-youtube/relay.env
unset KEY

cat > /usr/local/sbin/radio-youtube-relay <<'RELAY'
#!/usr/bin/env bash
set -Eeuo pipefail
source /etc/radio-youtube/relay.env
# Persistent service: retry stream interruptions without affecting AzuraCast.
while true; do
  ffmpeg -hide_banner -nostdin -loglevel warning \
    -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 \
    -thread_queue_size 1024 -i "$SOURCE_URL" \
    -f lavfi -i "color=c=0x132c57:s=1280x720:r=25" \
    -map 1:v:0 -map 0:a:0 \
    -c:v libx264 -preset veryfast -tune stillimage \
    -pix_fmt yuv420p -r 25 -g 50 -b:v 1200k -maxrate 1200k -bufsize 2400k \
    -c:a aac -b:a 128k -ar 44100 -ac 2 \
    -af "aresample=async=1:first_pts=0" \
    -f flv "rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_KEY" || true
  sleep 8
done
RELAY
chmod 700 /usr/local/sbin/radio-youtube-relay

cat > /etc/systemd/system/radio-youtube.service <<'SERVICE'
[Unit]
Description=Radio Romanii din Italia - YouTube live relay
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/sbin/radio-youtube-relay
Restart=always
RestartSec=10
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/etc/radio-youtube

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable --now radio-youtube.service
echo "Service started. Check: sudo systemctl status radio-youtube.service"
echo "Stop: sudo systemctl stop radio-youtube.service"
echo "Logs: sudo journalctl -u radio-youtube.service -n 30 --no-pager"
