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

    def test_password_setup_login_session_and_logout(self):
        status=self.client.get("/api/ai-music/admin/auth-status")
        self.assertEqual(status.json["password_configured"],False)
        setup="/api/ai-music/admin/setup-password"
        password="RDI Secure Password! 2026"
        self.assertEqual(self.client.post(setup,headers=self.origin,
            json={"current_token":"wrong","password":password}).status_code,401)
        self.assertEqual(self.client.post(setup,headers=self.origin,
            json={"current_token":"unit-test-admin-token","password":"short"}).status_code,400)
        self.assertEqual(self.client.post(setup,headers=self.origin,
            json={"current_token":"unit-test-admin-token","password":password}).status_code,201)
        self.assertEqual(self.client.get("/api/ai-music/admin/auth-status").json["password_configured"],True)
        self.assertEqual(self.client.post(setup,headers=self.origin,
            json={"current_token":"unit-test-admin-token","password":password}).status_code,409)
        self.assertEqual(self.client.post("/api/ai-music/admin/login",headers=self.origin,
            json={"password":"wrong"}).status_code,401)
        login=self.client.post("/api/ai-music/admin/login",headers=self.origin,
            json={"password":password})
        self.assertEqual(login.status_code,200)
        session=login.json["session"]
        auth={"Authorization":"Bearer "+session}
        self.assertEqual(self.client.get("/api/ai-music/admin/submissions",headers=auth).status_code,200)
        self.assertEqual(self.client.post("/api/ai-music/admin/logout",headers=auth).status_code,200)
        self.assertEqual(self.client.get("/api/ai-music/admin/submissions",headers=auth).status_code,401)
        # Existing admin token remains functional for managed migration.
        self.assertEqual(self.client.get("/api/ai-music/admin/submissions",headers=self.admin).status_code,200)

    def test_login_rejects_bruteforce_attempts(self):
        self.client.post("/api/ai-music/admin/setup-password",headers=self.origin,
                         json={"current_token":"unit-test-admin-token","password":"Valid strong password 2026"})
        for _ in range(5):
            self.assertEqual(self.client.post("/api/ai-music/admin/login",headers=self.origin,
                json={"password":"wrong"}).status_code,401)
        self.assertEqual(self.client.post("/api/ai-music/admin/login",headers=self.origin,
                json={"password":"Valid strong password 2026"}).status_code,429)

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
        self.assertEqual(response.status_code, 201, response.get_json())
        sid = response.json["id"]
        private_url = f"/api/ai-music/admin/submissions/{sid}/audio"
        self.assertEqual(self.client.get(private_url).status_code, 401)
        response = self.client.get(private_url, headers=self.admin)
        try:
            self.assertEqual(response.status_code, 200)
        finally:
            response.close()
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

    def test_rate_limit_persists_across_requests(self):
        for _ in range(6):
            self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post().status_code, 429)
        with service.db() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM rate_events").fetchone()[0], 6)

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

    def test_spotlight_only_approved_and_private_data_hidden(self):
        pending = self.post(title="Pending").json["id"]
        approved = self.post(title="Approved", email="secret@example.org", notes="private note").json["id"]
        review = self.client.post(
            f"/api/ai-music/admin/submissions/{approved}/review",
            headers=self.admin, json={"status": "approved"},
        )
        self.assertEqual(review.status_code, 200)
        resp = self.client.get("/api/ai-music/spotlight", headers=self.origin)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json["tracks"]), 1)
        track = resp.json["tracks"][0]
        self.assertEqual(track["id"], approved)
        self.assertNotEqual(track["id"], pending)
        self.assertEqual(track["votes"], 0)
        for secret in ("email", "notes", "stored_name", "file_name", "reviewed_note"):
            self.assertNotIn(secret, track)

    def test_audio_spotlight_preview_requires_explicit_opt_in(self):
        audio_bytes=b"audio-test-payload"
        def make_upload(consent):
            fields=self.data(link="",spotlight_consent=consent)
            fields["audio"]=(io.BytesIO(audio_bytes),"example.mp3")
            return self.client.post("/api/ai-music/submissions",data=fields,headers=self.origin).json["id"]
        without=make_upload("no")
        with_consent=make_upload("yes")
        for sid in (without,with_consent):
            with patch.object(service.subprocess,"run") as probe:
                probe.return_value.returncode=0
                probe.return_value.stdout="codec_type=audio"
                response=self.client.post(
                    f"/api/ai-music/admin/submissions/{sid}/review",
                    headers=self.admin,json={"status":"approved"})
                self.assertEqual(response.status_code,200)
        no_consent_url=f"/api/ai-music/spotlight/{without}/audio"
        consent_url=f"/api/ai-music/spotlight/{with_consent}/audio"
        self.assertEqual(self.client.get(no_consent_url).status_code,404)
        response=self.client.get(consent_url)
        try:
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.data,audio_bytes)
            self.assertEqual(response.headers["Content-Disposition"],"inline")
        finally:
            response.close()
        tracks={t["id"]:t for t in self.client.get("/api/ai-music/spotlight").json["tracks"]}
        self.assertEqual(tracks[without]["audio_preview"],0)
        self.assertEqual(tracks[with_consent]["audio_preview"],1)

    def test_editor_can_enable_and_revoke_public_play_only_with_consent(self):
        fields=self.data(link="",spotlight_consent="no")
        fields["audio"]=(io.BytesIO(b"test-audio"),"track.mp3")
        sid=self.client.post("/api/ai-music/submissions",data=fields,headers=self.origin).json["id"]
        endpoint=f"/api/ai-music/admin/submissions/{sid}/spotlight-consent"
        public_audio=f"/api/ai-music/spotlight/{sid}/audio"
        self.assertEqual(self.client.post(endpoint,json={"enabled":True,"artist_permission_confirmed":True}).status_code,401)
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={"enabled":True,"artist_permission_confirmed":True}).status_code,400)
        with patch.object(service.subprocess,"run") as probe:
            probe.return_value.returncode=0
            probe.return_value.stdout="codec_type=audio"
            self.assertEqual(self.client.post(f"/api/ai-music/admin/submissions/{sid}/review",headers=self.admin,json={"status":"approved"}).status_code,200)
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={"enabled":True}).status_code,400)
        self.assertEqual(self.client.get(public_audio).status_code,404)
        result=self.client.post(endpoint,headers=self.admin,json={"enabled":True,"artist_permission_confirmed":True})
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.client.get(public_audio).status_code,200)
        self.assertEqual(self.client.post(endpoint,headers=self.admin,json={"enabled":False}).status_code,200)
        self.assertEqual(self.client.get(public_audio).status_code,404)
        with service.db() as con:
            val=con.execute("SELECT spotlight_consent FROM submissions WHERE id=?",(sid,)).fetchone()[0]
        self.assertEqual(val,0)

    def test_comments_open_under_approved_track_only_and_hide(self):
        pending=self.post(title="Pending").json["id"]
        approved=self.post(title="Approved").json["id"]
        self.client.post(f"/api/ai-music/admin/submissions/{approved}/review",
                         headers=self.admin,json={"status":"approved"})
        path=f"/api/ai-music/spotlight/{approved}/comments"
        self.assertEqual(self.client.get(f"/api/ai-music/spotlight/{pending}/comments").status_code,404)
        self.assertEqual(self.client.post(path,json={"nickname":"Ana","body":"Bellissima canzone!"}).status_code,403)
        self.assertEqual(self.client.post(path,headers=self.origin,json={"nickname":"A","body":"x"}).status_code,400)
        self.assertEqual(self.client.post(path,headers=self.origin,json={"nickname":"Ana","body":"https://spam.example"}).status_code,400)
        with patch.object(service.time,"time",return_value=1800000000):
            result=self.client.post(path,headers=self.origin,json={"nickname":"Ana","body":"Bellissima canzone!"})
        self.assertEqual(result.status_code,201,result.get_json())
        cid=result.json["id"]
        comments=self.client.get(path).json["comments"]
        self.assertEqual(len(comments),1)
        self.assertEqual(comments[0]["nickname"],"Ana")
        self.assertNotIn("ip_key",comments[0])
        with patch.object(service.time,"time",return_value=1800000010):
            self.assertEqual(self.client.post(path,headers=self.origin,json={"nickname":"Bello","body":"Un altro commento"}).status_code,429)
        self.assertEqual(self.client.post(f"/api/ai-music/admin/spotlight/comments/{cid}/hide").status_code,401)
        self.assertEqual(self.client.post(f"/api/ai-music/admin/spotlight/comments/{cid}/hide",headers=self.admin).status_code,200)
        self.assertEqual(self.client.get(path).json["comments"],[])

    def test_spotlight_vote_requires_origin_and_valid_uuid(self):
        sid = self.post().json["id"]
        self.client.post(f"/api/ai-music/admin/submissions/{sid}/review",
                         headers=self.admin, json={"status": "approved"})
        vote_url = f"/api/ai-music/spotlight/{sid}/vote"
        visitor = "be9fbcf6-eafd-49b9-8431-2be1f99a62c5"
        self.assertEqual(self.client.post(vote_url, json={"visitor": visitor}).status_code, 403)
        self.assertEqual(self.client.post(vote_url, headers=self.origin,
                                          json={"visitor": "no"}).status_code, 400)
        self.assertEqual(self.client.post(vote_url, headers=self.origin,
                                          json={"visitor": visitor}).status_code, 201)
        self.assertEqual(self.client.post(vote_url, headers=self.origin,
                                          json={"visitor": visitor}).status_code, 409)
        self.assertEqual(self.client.get("/api/ai-music/spotlight").json["tracks"][0]["votes"], 1)

    def test_spotlight_vote_rejected_for_pending_and_rate_limited(self):
        import uuid
        pending = self.post(title="Pending").json["id"]
        approved = self.post(title="Approved").json["id"]
        self.client.post(f"/api/ai-music/admin/submissions/{approved}/review",
                         headers=self.admin, json={"status": "approved"})
        self.assertEqual(self.client.post(
            f"/api/ai-music/spotlight/{pending}/vote", headers=self.origin,
            json={"visitor": str(uuid.uuid4())}).status_code, 404)
        with patch.object(service, "VOTE_IP_DAILY_MAX", 2):
            for _ in range(2):
                self.assertEqual(self.client.post(
                    f"/api/ai-music/spotlight/{approved}/vote", headers=self.origin,
                    json={"visitor": str(uuid.uuid4())}).status_code, 201)
            self.assertEqual(self.client.post(
                f"/api/ai-music/spotlight/{approved}/vote", headers=self.origin,
                json={"visitor": str(uuid.uuid4())}).status_code, 429)


if __name__ == "__main__":
    unittest.main()
