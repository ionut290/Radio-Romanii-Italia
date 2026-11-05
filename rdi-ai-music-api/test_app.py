"""Regression checks for RDI AI MUSIC before enabling public submissions.

Run in the API virtualenv: python -m unittest discover -s . -p 'test_*.py' -v
All data is written to a temporary directory; no production service is touched.
"""
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as service


class SubmissionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.patches = [
            patch.object(service, "ROOT", self.root),
            patch.object(service, "FILES", self.root / "uploads"),
            patch.object(service, "DB", self.root / "submissions.sqlite3"),
            patch.object(service, "ADMIN_TOKEN", "unit-test-admin-token"),
            patch.object(service, "RATE", {}),
        ]
        for p in self.patches:
            p.start()
        self.client = service.app.test_client()
        self.origin = {"Origin": service.PUBLIC_ORIGIN}
        self.admin = {"Authorization": "Bearer unit-test-admin-token"}

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def data(self, **values):
        fields = dict(
            artist="Test Artist",
            email="artist@example.org",
            title="Original composition",
            platform="Suno",
            link="https://example.org/track",
            rights="yes",
            privacy="yes",
        )
        fields.update(values)
        return fields

    def post(self, **values):
        return self.client.post(
            "/api/ai-music/submissions",
            data=self.data(**values),
            headers=self.origin,
        )

    def test_health_is_public(self):
        response = self.client.get("/api/ai-music/health")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json["ok"])

    def test_admin_requires_secret(self):
        response = self.client.get("/api/ai-music/admin/submissions")
        self.assertEqual(response.status_code, 401)
        response = self.client.get(
            "/api/ai-music/admin/submissions",
            headers=self.admin,
        )
        self.assertEqual(response.status_code, 200)

    def test_wrong_origin_is_forbidden(self):
        response = self.client.post(
            "/api/ai-music/submissions",
            headers={"Origin": "https://untrusted.example"},
            data=self.data(),
        )
        self.assertEqual(response.status_code, 403)

    def test_preflight_allows_public_origin(self):
        response = self.client.options(
            "/api/ai-music/submissions",
            headers=self.origin,
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(
            response.headers.get("Access-Control-Allow-Origin"),
            service.PUBLIC_ORIGIN,
        )

    def test_required_rights_and_privacy(self):
        self.assertEqual(self.post(rights="no").status_code, 400)
        self.assertEqual(self.post(privacy="no").status_code, 400)

    def test_unsafe_link_rejected(self):
        self.assertEqual(self.post(link="http://example.org/track").status_code, 400)
        self.assertEqual(self.post(link="javascript:alert(1)").status_code, 400)

    def test_link_submission_stays_pending(self):
        response = self.post()
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["status"], "pending")
        records = self.client.get(
            "/api/ai-music/admin/submissions",
            headers=self.admin,
        ).json["submissions"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["status"], "pending")

    def test_audio_is_private_and_never_auto_approved(self):
        fields = self.data(link="")
        fields["audio"] = (io.BytesIO(b"not-real-audio"), "demo.mp3")
        response = self.client.post(
            "/api/ai-music/submissions",
            data=fields,
            headers=self.origin,
        )
        self.assertEqual(response.status_code, 201)
        sid = response.json["id"]
        private_url = f"/api/ai-music/admin/submissions/{sid}/audio"
        self.assertEqual(self.client.get(private_url).status_code, 401)
        self.assertEqual(
            self.client.get(private_url, headers=self.admin).status_code, 200
        )
        # A fake MP3 must not pass audio validation when ffprobe is available.
        with patch.object(service.subprocess, "run") as probe:
            probe.return_value.returncode = 1
            probe.return_value.stdout = ""
            review = self.client.post(
                f"/api/ai-music/admin/submissions/{sid}/review",
                headers=self.admin,
                json={"status": "approved"},
            )
        self.assertEqual(review.status_code, 400)

    def test_review_is_explicit(self):
        sid = self.post().json["id"]
        response = self.client.post(
            f"/api/ai-music/admin/submissions/{sid}/review",
            headers=self.admin,
            json={"status": "approved", "note": "Verified manually"},
        )
        self.assertEqual(response.status_code, 200)
        records = self.client.get(
            "/api/ai-music/admin/submissions",
            headers=self.admin,
        ).json["submissions"]
        self.assertEqual(records[0]["status"], "approved")


if __name__ == "__main__":
    unittest.main()
