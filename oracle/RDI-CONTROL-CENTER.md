# RDI Control Center — Oracle

The control center is a private, loopback-only Oracle service. It gathers the health data
used by the RDI dashboard every five minutes and records automatic recovery attempts.
It does not expose an internet-facing management port.

## Monitored areas

- **Radio:** AzuraCast Now Playing plus a short sample from the public MP3 stream. An
  MP3 frame sample confirms that audio bytes arrive; it does not prove a listener can
  hear the stream on every device.
- **AzuraCast:** the existing inspector checks only the RDI Geopolitica playlist ID 12,
  its enabled state, hourly minute 10, and media counts. It does not change playlists.
  The inspector creates and revokes a temporary AzuraCast API key for its read request;
  no long-lived AzuraCast credential is stored.
- **YouTube Live:** systemd state for the standard relay, optional visual relay, browser
  watchdog and rescue browser, plus FFmpeg process count. FFmpeg running is not proof
  that YouTube accepted RTMP; the dashboard labels that separately as unconfirmed.
- **Redaction:** freshness and counts from the public editorial status and Geopolitica
  feeds. This does not prove that the separate ChatGPT editorial automation completed.
- **Website:** HTTP and JSON checks for the homepage, editorial status, article
  supplement and Geopolitica feeds.
- **Oracle:** CPU, memory, disk, Docker and container states.

## Automatic recovery boundary

The only automatic service restart is \`radio-youtube.service\`, and only when all of
these conditions hold:

1. systemd reports that the unit is \`failed\`;
2. the standard relay is enabled;
3. \`radio-youtube-visual.service\` is not active;
4. the restart cooldown and three-attempt daily limit allow it.

The optional visual relay is never started or restarted by the control center. If both
YouTube relays are active, it reports a conflict and changes nothing. AzuraCast,
Docker, other systemd services, playlists, the website, and GitHub content are monitored
but not modified. A restart attempt and its outcome are recorded in
\`/var/lib/rdi-control-center/actions.jsonl\`; the current health report is stored in
\`status.json\`.

## Install and private dashboard access

Run on Oracle as root from the current repository checkout:

\`\`\`bash
sudo bash oracle/install-rdi-control-center.sh
\`\`\`

The dashboard binds only to \`127.0.0.1:8787\`. From an authorized computer, open an SSH
tunnel:

\`\`\`bash
ssh -L 8787:127.0.0.1:8787 ubuntu@<oracle-host>
\`\`\`

Then visit \`http://127.0.0.1:8787\`. No public reverse-proxy route or public dashboard
is configured.

## Inspect and audit

\`\`\`bash
sudo systemctl status rdi-control-center.timer rdi-control-center-web.service
sudo journalctl -u rdi-control-center.service -n 50 --no-pager
sudo cat /var/lib/rdi-control-center/status.json
sudo tail -n 50 /var/lib/rdi-control-center/actions.jsonl
\`\`\`

To stop only this control center:

\`\`\`bash
sudo systemctl disable --now rdi-control-center.timer rdi-control-center-web.service
\`\`\`

This does not stop radio or YouTube services.
