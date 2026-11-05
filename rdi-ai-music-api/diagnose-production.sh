#!/usr/bin/env bash
# RDI AI MUSIC read-only diagnostics. Never changes files/services.
set -u
echo '=== RDI AI MUSIC: preflight (read-only) ==='
echo '[1] Date / hostname'
date -u '+UTC %Y-%m-%d %H:%M:%S' || true
hostname || true
echo '[2] Backend service state'
systemctl is-active rdi-ai-music 2>/dev/null || true
systemctl is-enabled rdi-ai-music 2>/dev/null || true
echo '[3] Local backend response'
curl -sS --connect-timeout 3 --max-time 8 -o /dev/null -w 'localhost /health HTTP %{http_code}\n' http://127.0.0.1:8766/api/ai-music/health || true
echo '[4] Public HTTPS backend response'
curl -sS --connect-timeout 5 --max-time 12 -o /dev/null -w 'public /health HTTP %{http_code} TLS verify %{ssl_verify_result}\n' https://radio-romanii-italia.duckdns.org/api/ai-music/health || true
echo '[5] Public CORS preflight'
curl -sS -X OPTIONS --connect-timeout 5 --max-time 12 -o /dev/null -w 'public OPTIONS HTTP %{http_code}\n' -H 'Origin: https://radioromanii.duckdns.org' -H 'Access-Control-Request-Method: POST' https://radio-romanii-italia.duckdns.org/api/ai-music/submissions || true
echo '[6] Admin route without token (expected 401)'
curl -sS --connect-timeout 5 --max-time 12 -o /dev/null -w 'public admin HTTP %{http_code}\n' https://radio-romanii-italia.duckdns.org/api/ai-music/admin/submissions || true
echo '[7] Listening processes (no secrets)'
ss -ltn 2>/dev/null | grep -E '(:8766|:80 |:443 )' || true
echo '[8] AzuraCast containers (read-only)'
docker ps --format '{{.Names}} {{.Status}}' 2>/dev/null | grep -Ei 'azura|nginx|web' || true
echo '[9] Local host nginx syntax status (read-only)'
if command -v nginx >/dev/null 2>&1; then sudo -n nginx -t 2>&1 | tail -6; else echo 'Host nginx command unavailable (AzuraCast may use container nginx)'; fi
echo '=== Done. No services restarted; no configurations changed. ==='
