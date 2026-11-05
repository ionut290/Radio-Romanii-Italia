"""Regression tests: no public moderation and only the RDI origin may use the browser API.

Run from rdi-ai-music-api with:
  RDI_AI_ADMIN_TOKEN=test-token RDI_AI_DATA_DIR=$(mktemp -d) python3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest
from pathlib import Path

_tmp = tempfile.TemporaryDirectory(prefix="rdi-ai-test-")
os.environ["RDI_AI_DATA_DIR"] = _tmp.name
os.environ["RDI_AI_ADMIN_TOKEN"] = "test-token"
os.environ["RDI_AI_PUBLIC_ORIGIN"] = "https://radioromanii.duckdns.org"

from app import app  # noqa: E402

class TestAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def tearDown(self):
        from app import RATE
        RATE.clear()

    def test_health(self):
        self.assertEqual(self.client.get("/api/ai-music/health").status_code, 200)

    def test_admin_requires_bearer(self):
        self.assertEqual(self.client.get("/api/ai-music/admin/submissions").status_code, 401)

    def test_browser_origin_allowed_and_preflight(self):
        response = self.client.options(
            "/api/ai-music/admin/submissions/any/review",
            headers={"Origin": "https://radioromanii.duckdns.org",
                     "Access-Control-Request-Method": "POST",
                     "Access-Control-Request-Headers": "Authorization, Content-Type"}
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"),
                         "https://radioromanii.duckdns.org")

    def test_other_origin_rejected(self):
        result = self.client.post("/api/ai-music/submissions",
            headers={"Origin": "https://untrusted.example"})
        self.assertEqual(result.status_code, 403)
        self.assertIsNone(result.headers.get("Access-Control-Allow-Origin"))

    def test_submission_stays_pending(self):
        result = self.client.post("/api/ai-music/submissions", data={
            "artist": "RDI test", "email": "test@example.com",
            "title": "Original track", "platform": "Mureka",
            "link": "https://example.com/track.mp3",
            "rights": "yes", "privacy": "yes"
        }, headers={"Origin": "https://radioromanii.duckdns.org"})
        self.assertEqual(result.status_code, 201)
        sid = result.json["id"]
        listing = self.client.get("/api/ai-music/admin/submissions",
            headers={"Authorization": "Bearer test-token"})
        self.assertEqual(listing.status_code, 200)
        row = next(x for x in listing.json["submissions"] if x["id"] == sid)
        self.assertEqual(row["status"], "pending")

if __name__ == "__main__":
    unittest.main()
