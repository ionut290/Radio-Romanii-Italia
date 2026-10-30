#!/usr/bin/env bash
set -Eeuo pipefail
# Optional visual mode, uses existing root-only RTMP key.
source /etc/radio-youtube/relay.env
DISPLAY_NUM=":92"
export DISPLAY="$DISPLAY_NUM"

# Use AzuraCast as the sole audio source. Telegram audio and video are disabled.
AUDIO_UID=$(id -u ubuntu)
PULSE_RUNTIME="/run/user/$AUDIO_UID"
BROWSER_AUDIO_ENV=()
FFMPEG_ENV_ARGS=()
FFMPEG_AUDIO_INPUT_ARGS=()
FFMPEG_AUDIO_MAP_ARGS=(-map 1:a:0 -af "aresample=async=1:first_pts=0")
SITE_URL="${SITE_URL:-https://radioromanii.duckdns.org/youtube-news.html}"
# AzuraCast stays the base program; approved Telegram audio is mixed and ducks the music.
Xvfb "$DISPLAY_NUM" -screen 0 1280x720x24 -nolisten tcp &
XVFB_PID=$!
PROFILE=/home/ubuntu/radio-youtube-browser
install -d -o ubuntu -g ubuntu -m 700 "$PROFILE"
cleanup() { kill "$BROWSER_PID" "$XVFB_PID" "${SCROLL_PID:-}" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
sleep 2
# Browser refreshes preserve the active FFmpeg audio relay.
runuser -u ubuntu -- env HOME=/home/ubuntu XDG_RUNTIME_DIR="$PULSE_RUNTIME" "${BROWSER_AUDIO_ENV[@]}" /snap/bin/chromium --disable-gpu --disable-dev-shm-usage --disable-background-networking \
  --disable-translate --disable-features=Translate,TranslateUI --lang=ro-RO \
  --user-data-dir="$PROFILE" --no-first-run --disable-session-crashed-bubble \
  --autoplay-policy=no-user-gesture-required --window-size=1280,720 \
  --window-position=0,0 --kiosk "$SITE_URL" >/tmp/radio-youtube-chromium.log 2>&1 &
BROWSER_PID=$!
sleep 10
if ! pgrep -u ubuntu -f "/snap/chromium|/usr/lib/chromium|chrome" >/dev/null; then
  echo "Chromium not running: stopping visual relay so operator can restore blue relay" >&2
  tail -n 15 /tmp/radio-youtube-chromium.log >&2 || true
  exit 1
fi
# The dedicated youtube-news.html cycles through news cards automatically.
# Do not inject keyboard commands or navigate to login/community pages.

# Never echo the RTMP destination (contains stream key).
# Use short reconnect cycle if YouTube or AzuraCast interrupts.
while true; do
  env "${FFMPEG_ENV_ARGS[@]}" ffmpeg -hide_banner -nostdin -loglevel error -stats_period 60 -nostats \
    -f x11grab -thread_queue_size 512 -framerate 10 -video_size 1280x720 -i "$DISPLAY_NUM.0" \
    -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 \
    -thread_queue_size 1024 -i "$SOURCE_URL" \
    "${FFMPEG_AUDIO_INPUT_ARGS[@]}" \
    -map 0:v:0 -vf scale=854:480:flags=fast_bilinear \
    "${FFMPEG_AUDIO_MAP_ARGS[@]}" \
    -c:v libx264 -preset ultrafast -pix_fmt yuv420p -r 10 -g 20 \
    -b:v 1200k -minrate 1200k -maxrate 1200k -bufsize 2400k \
    -x264-params "nal-hrd=cbr:force-cfr=1" \
    -c:a aac -b:a 128k -ar 44100 -ac 2 \
    -f flv "rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_KEY" 2>&1 \
    | sed -u -E 's#rtmps?://[^[:space:]]+#[RTMP_REDACTED]#g' >&2 || true
  sleep 8
done
