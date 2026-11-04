#!/usr/bin/env bash
# RDI AI MUSIC backend installation on Ubuntu. Run manually after reviewing settings.
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Run as root: sudo bash install-ubuntu.sh"; exit 1; }
SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TARGET=/opt/rdi-ai-music-api
DATA_DIR=/var/lib/rdi-ai-music
ENV_PATH=/etc/rdi-ai-music.env
if [[ -e "$ENV_PATH" ]]; then
  echo "Existing environment file found. Will not overwrite it."
else
  echo "Creating new token and protected environment file."
  install -m 0600 -o root -g root /dev/null "$ENV_PATH"
  TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  printf 'RDI_AI_ADMIN_TOKEN=%s\nRDI_AI_DATA_DIR=%s\nRDI_AI_MAX_MB=30\n' "$TOKEN" "$DATA_DIR" > "$ENV_PATH"
  unset TOKEN
fi
if ! id -u rdi-ai >/dev/null 2>&1; then
  useradd --system --home-dir "$DATA_DIR" --shell /usr/sbin/nologin rdi-ai
fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv ffmpeg
install -d -o root -g root -m 0755 "$TARGET"
install -d -o rdi-ai -g rdi-ai -m 0700 "$DATA_DIR"
install -d -o rdi-ai -g rdi-ai -m 0700 "$DATA_DIR/uploads"
install -m 0644 -o root -g root "$SOURCE_DIR/app.py" "$TARGET/app.py"
install -m 0644 -o root -g root "$SOURCE_DIR/requirements.txt" "$TARGET/requirements.txt"
python3 -m venv "$TARGET/.venv"
"$TARGET/.venv/bin/pip" install --no-cache-dir -r "$TARGET/requirements.txt"
install -m 0644 "$SOURCE_DIR/rdi-ai-music.service" /etc/systemd/system/rdi-ai-music.service
# The service must be able to read the token without making it readable by other users.
chown root:rdi-ai "$ENV_PATH"
chmod 0640 "$ENV_PATH"
systemctl daemon-reload
systemctl enable --now rdi-ai-music.service
systemctl --no-pager --full status rdi-ai-music.service | head -25 || true
curl --fail --silent --show-error http://127.0.0.1:8766/api/ai-music/health
printf '\nBackend installed LOCALLY only. Next: configure HTTPS reverse proxy for /api/ai-music/.\n'
printf 'DO NOT paste the secret token into chat or commit it into GitHub.\n'
