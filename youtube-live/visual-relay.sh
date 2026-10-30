#!/usr/bin/env bash
set -Eeuo pipefail
# Optional visual mode, uses existing root-only RTMP key.
source /etc/radio-youtube/relay.env
DISPLAY_NUM=":92"
export DISPLAY="$DISPLAY_NUM"

# Route Chromium playback to a private PulseAudio null sink so approved
# Telegram audio/video is captured by FFmpeg without changing AzuraCast.
AUDIO_UID=$(id -u ubuntu)
PULSE_RUNTIME="/run/user/$AUDIO_UID"
PULSE_SERVER_URI="unix:$PULSE_RUNTIME/pulse/native"
PULSE_COOKIE_FILE="/home/ubuntu/.config/pulse/cookie"
PULSE_CAPTURE_READY=0
BROWSER_AUDIO_ENV=()
FFMPEG_ENV_ARGS=()
FFMPEG_AUDIO_INPUT_ARGS=()
FFMPEG_AUDIO_MAP_ARGS=(-map 1:a:0 -af "aresample=async=1:first_pts=0")

if command -v pulseaudio >/dev/null && command -v pactl >/dev/null; then
  install -d -o ubuntu -g ubuntu -m 700 "$PULSE_RUNTIME"
  runuser -u ubuntu -- env HOME=/home/ubuntu XDG_RUNTIME_DIR="$PULSE_RUNTIME" pulseaudio --start --exit-idle-time=-1 >/tmp/rdi-pulse-start.log 2>&1 || true
  for attempt in {1..15}; do
    if runuser -u ubuntu -- env HOME=/home/ubuntu XDG_RUNTIME_DIR="$PULSE_RUNTIME" pactl info >/dev/null 2>&1; then break; fi
    sleep 1
  done
  if runuser -u ubuntu -- env HOME=/home/ubuntu XDG_RUNTIME_DIR="$PULSE_RUNTIME" pactl info >/dev/null 2>&1; then
    if ! runuser -u ubuntu -- env HOME=/home/ubuntu XDG_RUNTIME_DIR="$PULSE_RUNTIME" pactl list short sinks | awk '{print $2}' | grep -Fxq rdi_telegram_sink; then
      runuser -u ubuntu -- env HOME=/home/ubuntu XDG_RUNTIME_DIR="$PULSE_RUNTIME" pactl load-module module-null-sink sink_name=rdi_telegram_sink rate=44100 channels=2 >/dev/null || true
    fi
    if runuser -u ubuntu -- env HOME=/home/ubuntu XDG_RUNTIME_DIR="$PULSE_RUNTIME" pactl list short sinks | awk '{print $2}' | grep -Fxq rdi_telegram_sink; then
      PULSE_CAPTURE_READY=1
      BROWSER_AUDIO_ENV=("PULSE_SERVER=$PULSE_SERVER_URI" "PULSE_SINK=rdi_telegram_sink")
      FFMPEG_ENV_ARGS=("PULSE_SERVER=$PULSE_SERVER_URI" "PULSE_COOKIE=$PULSE_COOKIE_FILE")
      FFMPEG_AUDIO_INPUT_ARGS=(-f pulse -sample_rate 44100 -channels 2 -thread_queue_size 256 -i rdi_telegram_sink.monitor)
      FFMPEG_AUDIO_MAP_ARGS=(-filter_complex "[2:a]asplit=2[sidechain][telegram_audio];[1:a][sidechain]sidechaincompress=threshold=0.025:ratio=6:attack=20:release=550[music_ducked];[music_ducked][telegram_audio]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95,aresample=async=1:first_pts=0[aout]" -map "[aout]")
    fi
  fi
fi

if [[ "$PULSE_CAPTURE_READY" == 1 ]]; then
  echo "PulseAudio attivo: audio Telegram verrà miscelato nella diretta YouTube."
else
  echo "PulseAudio non disponibile: continuo con l'audio AzuraCast senza interrompere la diretta." >&2
fi
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
    -f x11grab -thread_queue_size 512 -framerate 15 -video_size 1280x720 -i "$DISPLAY_NUM.0" \
    -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 \
    -thread_queue_size 1024 -i "$SOURCE_URL" \
    "${FFMPEG_AUDIO_INPUT_ARGS[@]}" \
    -map 0:v:0 \
    "${FFMPEG_AUDIO_MAP_ARGS[@]}" \
    -c:v libx264 -preset ultrafast -pix_fmt yuv420p -r 15 -g 30 \
    -b:v 2500k -minrate 2500k -maxrate 2500k -bufsize 5000k \
    -x264-params "nal-hrd=cbr:force-cfr=1" \
    -c:a aac -b:a 128k -ar 44100 -ac 2 \
    -f flv "rtmp://a.rtmp.youtube.com/live2/$YOUTUBE_KEY" 2>&1 \
    | sed -u -E 's#rtmps?://[^[:space:]]+#[RTMP_REDACTED]#g' >&2 || true
  sleep 8
done
