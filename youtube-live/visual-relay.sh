#!/usr/bin/env bash
set -Eeuo pipefail
# Optional visual mode, uses existing root-only RTMP key.
source /etc/radio-youtube/relay.env
DISPLAY_NUM=":92"
export DISPLAY="$DISPLAY_NUM"
SITE_URL="${SITE_URL:-https://radio-romanii-italia.duckdns.org/}"
# Browser image is decorative; audio comes only from the AzuraCast MP3 source.
Xvfb "$DISPLAY_NUM" -screen 0 1280x720x24 -nolisten tcp &
XVFB_PID=$!
PROFILE=$(mktemp -d /tmp/radio-youtube-browser.XXXXXXXX)
cleanup() { kill "$BROWSER_PID" "$XVFB_PID" "${SCROLL_PID:-}" 2>/dev/null || true; rm -rf "$PROFILE"; }
trap cleanup EXIT INT TERM
sleep 2
chromium --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-background-networking \
  --user-data-dir="$PROFILE" --no-first-run --disable-session-crashed-bubble \
  --autoplay-policy=user-gesture-required --window-size=1280,720 \
  --window-position=0,0 --kiosk "$SITE_URL" >/dev/null 2>&1 &
BROWSER_PID=$!
sleep 10
# Rotate through homepage sections, then community. xdotool F5 refreshes news regularly.
(
  while true; do
    sleep 25
    xdotool key --clearmodifiers Page_Down
    sleep 25
    xdotool key --clearmodifiers Page_Down
    sleep 25
    xdotool key --clearmodifiers Home
    sleep 30
    xdotool key --clearmodifiers F5
    sleep 35
    # Show public community page, then return to the homepage.
    xdotool key --clearmodifiers ctrl+l
    xdotool type --clearmodifiers --delay 2 "${SITE_URL%/}/comunitate.html"
    xdotool key Return
    sleep 55
    xdotool key --clearmodifiers ctrl+l
    xdotool type --clearmodifiers --delay 2 "$SITE_URL"
    xdotool key Return
  done
) &
SCROLL_PID=$!

# Never echo the RTMP destination (contains stream key).
# Use short reconnect cycle if YouTube or AzuraCast interrupts.
while true; do
  ffmpeg -hide_banner -nostdin -loglevel error -stats_period 60 -nostats \
    -f x11grab -thread_queue_size 512 -framerate 15 -video_size 1280x720 -i "$DISPLAY_NUM.0" \
    -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 \
    -thread_queue_size 1024 -i "$SOURCE_URL" \
    -map 0:v:0 -map 1:a:0 \
    -c:v libx264 -preset ultrafast -pix_fmt yuv420p -r 15 -g 30 \
    -b:v 1000k -maxrate 1300k -bufsize 2600k \
    -c:a aac -b:a 128k -ar 44100 -ac 2 \
    -af "aresample=async=1:first_pts=0" \
    -f flv "rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_KEY" 2>&1 \
    | sed -u -E 's#rtmps?://[^[:space:]]+#[RTMP_REDACTED]#g' >&2 || true
  sleep 8
done
