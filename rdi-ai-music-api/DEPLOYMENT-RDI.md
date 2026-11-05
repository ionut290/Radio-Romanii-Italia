# RDI AI MUSIC — release / production checklist

## Current topology (November 2026)
- Public site: GitHub Pages, https://radioromanii.duckdns.org
- Oracle/AzuraCast HTTPS: https://radio-romanii-italia.duckdns.org
- Existing Flask/Gunicorn service: rdi-ai-music, http://127.0.0.1:8766
- API and editorial site are different origins; the Flask app strictly allows
  https://radioromanii.duckdns.org in CORS.
- Public coming-soon page is live. Do **not** replace it with the working
  submission form until all end-to-end checks below pass.
- AzuraCast nginx includes a read-only bind-mounted custom config containing
  an upstream for a stopped container. `nginx -t` currently fails. A restart,
  reload or blind Docker recreation may interrupt the radio. Plan maintenance
  and fix/validate this independently BEFORE adding any API proxy configuration.

## HTTPS activation
Expose only `/api/ai-music/` through the **existing** certified Oracle HTTPS
host. Do not use `ai.radio-romanii-italia.duckdns.org` with the existing cert:
the hostname does not match and browser uploads will be rejected.

The trusted proxy should forward complete paths to `127.0.0.1:8766`,
set an upload size limit of 32 MB and preserve the real client IP. Keep
Gunicorn bound to localhost; never open port 8766 to the Internet.
The existing `nginx-location.example.conf` is illustrative, not a drop-in
AzuraCast container config. Test the exact active container configuration
before any reload. No unauthenticated admin routes are permitted.

## Deployment
1. Back up `/opt/rdi-ai-music-api/app.py`, `/etc/rdi-ai-music.env` and
   `/var/lib/rdi-ai-music/submissions.sqlite3`; never print the admin token.
2. Install reviewed `app.py` and `import_azuracast.py` under
   `/opt/rdi-ai-music-api/` with restrictive permissions. The importer needs
   read-only access to approved audio and write access to its SQLite import
   tracking table, under the existing service account `rdi-ai`.
3. In the existing root-owned EnvironmentFile, set
   `RDI_AI_PUBLIC_ORIGIN=https://radioromanii.duckdns.org`.
   Reuse the existing admin token; do not regenerate it unnecessarily.
4. Restart **only** `rdi-ai-music` after code is staged. Validate
   `/api/ai-music/health` locally; verify browser CORS OPTIONS and 401 on
   unauthenticated admin requests.
5. After validating the reverse proxy, stage the trilingual submission and
   editorial pages from the feature branch. Never publish the submission form
   before HTTPS and CORS are verified from outside.

## AzuraCast publication (deliberately off by default)
Configure `RDI_AI_AZURA_API_BASE` (existing HTTPS host),
`RDI_AI_AZURA_STATION_ID` (actual station ID) and
`RDI_AI_AZURA_API_KEY` (dedicated account with Manage Station Media
permissions) **on Oracle only**, never in GitHub or the website.
Create the `AI-MUSIC` folder and apply the intended special playlist using
AzuraCast Media Manager's 'Apply to Folder' option. A playlist must also
participate in the desired general AutoDJ rotation, configured in AzuraCast.
AzuraCast's native folder-to-playlist mapping ensures uploaded files join only
the chosen playlist.

`import_azuracast.py SUBMISSION_ID` only previews the operation.
`import_azuracast.py SUBMISSION_ID --publish` sends one approved local file,
records successful import and prevents a second import of the same submission.
It refuses pending/rejected submissions and link-only entries. **It is not
configured or executed by CI or automatically upon approval.** Test the real
instance's media upload API and destination mapping before turning on
automated publishing. Approving a song by itself currently does NOT place it
on-air.

## End-to-end release gate
- Public page served on GitHub Pages.
- Public origin POST and authenticated admin GET/POST via HTTPS succeed.
- CORS preflight works for Authorization; unrelated origins are rejected.
- Test MP3 upload stays pending and is absent from AutoDJ.
- Admin can download the file, verify copyright permissions, approve/reject.
- Importer dry run lists correct destination, then one test approved MP3 is
  imported and visible in the AI-MUSIC playlist. Verify AutoDJ configuration.
- Separate review for link-only entries (manual acquisition and rights check).
- Monitor logs and test no radio interruption; only then enable the public
  form and, if desired, separately implement a background approved-only queue.

No part of this document is authorization to restart or recreate AzuraCast
while its Nginx configuration test is failing.
