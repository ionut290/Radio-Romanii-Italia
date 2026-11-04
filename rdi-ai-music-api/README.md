# RDI AI MUSIC moderation API

Backend for the RDI site. Keep this directory on the private Oracle server, never on a public static host. Files are private and are not auto-published.

## Configuration
- RDI_AI_ADMIN_TOKEN: long random token (required, server-side only).
- RDI_AI_DATA_DIR: /var/lib/rdi-ai-music (SQLite DB plus private audio files).
- RDI_AI_MAX_MB: per-track audio limit (default 30).

Run with gunicorn on 127.0.0.1:8766; configure the existing HTTPS reverse proxy to forward **only** /api/ai-music/ to that port, preserving the URI. Do not expose :8766 publicly. Protect the admin page with HTTP authentication too if possible. Place the private data directory outside the website's document root, owned by the service account (0700); do not put uploads on a shared static filesystem.

Submission: POST /api/ai-music/submissions (multipart form-data). Admin: GET /api/ai-music/admin/submissions, GET /api/ai-music/admin/submissions/:id/audio, POST /api/ai-music/admin/submissions/:id/review {status, note}. Admin calls require Authorization: Bearer <RDI_AI_ADMIN_TOKEN>.

Before public launch: configure HTTPS and origin/rate limiting at reverse proxy; ensure adequate storage, backup and retention policy, malware scans, legal/privacy notice and verified rights. The in-memory rate limit is per-worker and does not substitute for proxy rate limiting. No AzuraCast key is ever exposed to browsers; approved items must be manually reviewed and imported into a playlist until the particular AzuraCast version and folder/playlist API have been validated. The admin token should not be shared. Do not enable production until this setup is complete.
