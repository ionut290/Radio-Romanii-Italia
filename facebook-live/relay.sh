#!/usr/bin/env bash
# Optional Facebook Live relay. It never changes the existing YouTube service.
set -Eeuo pipefail
umask 077
source /etc/radio-youtube/relay.env
source /etc/radio-facebook/relay.env
[[ -n "$SOURCE_URL" && -n "$FB_RTMPS_URL" && -n "$FB_STREAM_KEY" ]] || { echo "Missing relay settings" >&2; exit 1; }
[[ "$FB_RTMPS_URL" == rtmps://* ]] || { echo "Facebook requires RTMPS" >&2; exit 1; }
[[ -S /tmp/.X11-unix/X92 ]] || { echo "RDI visual display :92 unavailable; nothing started" >&2; exit 1; }
command -v ffmpeg >/dev/null || { echo "FFmpeg is required" >&2; exit 1; }
# Use same video display and same radio sound as YouTube, with independent encoder.
# Credential is never echoed; redact any server URL in unexpected error logs.
fb_server="$(printf '%s' "$FB_RTMPS_URL" | sed 's#/*$##')"
ffmpeg -hide_banner -nostdin -loglevel error -nostats \
  -f x11grab -thread_queue_size 512 -framerate 15 -video_size 1280x720 -i ":92.0" \
  -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 10 \
  -thread_queue_size 1024 -i "$SOURCE_URL" \
  -map 0:v:0 -map 1:a:0 \
  -c:v libx264 -preset ultrafast -pix_fmt yuv420p -r 15 -g 30 \
  -b:v 1800k -maxrate 2000k -bufsize 4000k \
  -c:a aac -b:a 128k -ar 44100 -ac 2 -af "aresample=async=1:first_pts=0" \
  -t 07:50:00 -f flv "$fb_server/$FB_STREAM_KEY" 2>&1 |
  sed -u -E 's#rtmps?://[^[:space:]]+#[RTMPS_ADDRESS_REDACTED]#g'
