#!/usr/bin/env bash
set -Eeuo pipefail
# Install a browser-only recovery watchdog. Does not touch FFmpeg, AzuraCast or RTMP secrets.
if [[ "$EUID" -ne 0 ]]; then
  echo "Run with sudo: sudo bash youtube-live/install-browser-watchdog.sh" >&2
  exit 1
fi
command -v systemctl >/dev/null
command -v ps >/dev/null
command -v grep >/dev/null
[[ -x /snap/bin/chromium ]] || { echo "Snap Chromium executable not found" >&2; exit 1; }
id ubuntu >/dev/null

install -d -m 755 /usr/local/libexec
install -d -m 700 -o ubuntu -g ubuntu /home/ubuntu/rdi-youtube-watchdog-profile

cat > /usr/local/libexec/rdi-youtube-browser-watchdog <<'WATCH'
#!/usr/bin/env bash
set -Eeuo pipefail
# A systemd timer calls this every 30 seconds. Only the graphical browser is touched.
visual='radio-youtube-visual.service'
rescue='rdi-youtube-browser-rescue.service'

# The video source is only used while the visual relay is active.
if ! systemctl is-active --quiet "$visual"; then
  if systemctl is-active --quiet "$rescue"; then
    systemctl stop "$rescue"
  fi
  exit 0
fi
[[ -S /tmp/.X11-unix/X92 ]] || exit 0

# Match only the actual kiosk browser (not utility processes or this watchdog).
# This includes the original visual-relay Chromium and the manually restored browser.
kiosks=$(ps -u ubuntu -ww -o args= | grep -E '[/]chrome[[:space:]].*--kiosk[=[:space:]]+https?://[^[:space:]]*/youtube-news\.html' || true)
external=$(printf '%s\n' "$kiosks" | grep -v -- '--user-data-dir=/home/ubuntu/rdi-youtube-watchdog-profile' || true)

# Prefer the original Chromium if it is available, avoiding duplicate kiosk windows.
if [[ -n "$external" ]]; then
  if systemctl is-active --quiet "$rescue"; then
    systemctl stop "$rescue"
    logger -t rdi-youtube-browser-watchdog 'Stopped extra rescue browser; original kiosk is present'
  fi
  exit 0
fi

# If our fallback kiosk is alive, leave it untouched.
if [[ -n "$kiosks" ]]; then
  exit 0
fi

# Never restart visual-relay, Xvfb, FFmpeg or AzuraCast.
if systemctl is-active --quiet "$rescue"; then
  systemctl restart "$rescue"
else
  systemctl reset-failed "$rescue" >/dev/null 2>&1 || true
  systemctl start "$rescue"
fi
logger -t rdi-youtube-browser-watchdog 'Chromium kiosk recovery requested; FFmpeg left running'
WATCH
chmod 755 /usr/local/libexec/rdi-youtube-browser-watchdog

cat > /etc/systemd/system/rdi-youtube-browser-rescue.service <<'SERVICE'
[Unit]
Description=RDI Chromium kiosk recovery (video only)
Wants=network-online.target
After=network-online.target
ConditionPathExists=/tmp/.X11-unix/X92
StartLimitIntervalSec=0

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu
Environment=DISPLAY=:92
ExecStart=/snap/bin/chromium --disable-gpu --disable-dev-shm-usage --no-first-run --disable-session-crashed-bubble --disable-translate --disable-features=Translate,TranslateUI --lang=ro-RO --user-data-dir=/home/ubuntu/rdi-youtube-watchdog-profile --window-size=1280,720 --window-position=0,0 --kiosk https://radioromanii.duckdns.org/youtube-news.html
Restart=always
RestartSec=8
TimeoutStopSec=10

[Install]
WantedBy=multi-user.target
SERVICE

cat > /etc/systemd/system/rdi-youtube-browser-watchdog.service <<'SERVICE'
[Unit]
Description=Check and repair RDI YouTube browser without touching live encoder

[Service]
Type=oneshot
ExecStart=/usr/local/libexec/rdi-youtube-browser-watchdog
SERVICE

cat > /etc/systemd/system/rdi-youtube-browser-watchdog.timer <<'TIMER'
[Unit]
Description=Check RDI YouTube Chromium every 30 seconds

[Timer]
OnBootSec=45s
OnUnitActiveSec=30s
AccuracySec=5s
Unit=rdi-youtube-browser-watchdog.service

[Install]
WantedBy=timers.target
TIMER

systemctl daemon-reload
systemctl enable --now rdi-youtube-browser-watchdog.timer
# Run the initial check; the currently working Chromium should remain unchanged.
systemctl start rdi-youtube-browser-watchdog.service

echo 'RDI browser-only watchdog installed.'
systemctl is-active rdi-youtube-browser-watchdog.timer
systemctl is-active radio-youtube-visual.service
systemctl is-active rdi-youtube-browser-rescue.service || true
