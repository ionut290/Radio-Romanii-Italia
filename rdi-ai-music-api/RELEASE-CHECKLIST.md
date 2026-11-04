# Operational release checklist

1. Do not merge PR #20 until the API has been deployed on the SAME HTTPS origin as the HTML site, and a privacy notice has been approved.
2. On Oracle Ubuntu, first inspect `sudo nginx -T` to identify the active server block. Do NOT replace or overwrite any existing Nginx config.
3. Copy the `rdi-ai-music-api` directory from this branch to the server, then run `sudo bash install-ubuntu.sh` from within that directory. The installer preserves an existing token file. Do not publish `/etc/rdi-ai-music.env`.
4. Add the contents of `nginx-location.example.conf` inside the site's EXISTING HTTPS server block. Validate using `sudo nginx -t`, reload, and verify `https://radioromanii.duckdns.org/api/ai-music/health` returns JSON `{"ok":true,"service":"rdi-ai-music"}`. Verify HTTP redirects to HTTPS.
5. Verify `GET /api/ai-music/admin/submissions` WITHOUT a bearer token returns **401** and that private files cannot be fetched as direct URLs. Add reverse-proxy rate limiting and sufficient disk quota; configure backups and scheduled retention/deletion for rejected applications and files.
6. On staging, send a submission with a public HTTPS music link and another with an MP3 file. Confirm they appear as `pending`. Verify invalid/oversized uploads fail, an unverified client cannot access audio, and an approved file is still *not* aired.
7. Set up the editorial workflow: token retrieved safely from the server's protected env file by the authorized admin (not by copying into source code). Restrict access to the moderation page. Review terms of AI music providers and obtained rights.
8. Only after validation merge PR #20 and deploy the static site. Perform one end-to-end test in production.
9. Configure AzuraCast import into a quarantined / dedicated folder only after API version, station ID, and playlist settings are verified; map manual approval to explicit import and rotation, never publish files on initial submission.

**Known limitations:** the current in-process IP throttle is per Gunicorn worker; it is not reliable as a public anti-abuse control. The privacy checkbox is not itself a complete GDPR privacy notice; link an actual notice and define a retention policy prior to public launch. The upload extension is checked at intake and ffprobe is checked at approval; add virus scanning for untrusted files before permitting public intake.
