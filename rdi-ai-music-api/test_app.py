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

    def test_youtube_consent_is_explicit_and_requires_an_uploaded_file(self):
        data=self.data(link="")
        data["audio"]=(io.BytesIO(b"x"*2000),"consented.mp3")
        data["spotlight_consent"]="yes"
        data["youtube_consent"]="yes"
        response=self.client.post("/api/ai-music/submissions",headers=self.origin,data=data)
        self.assertEqual(response.status_code,201)
        with service.db() as con:
            row=con.execute("SELECT status,youtube_consent FROM submissions WHERE id=?",
                             (response.json["id"],)).fetchone()
            self.assertEqual(row["status"],"pending")
            self.assertEqual(row["youtube_consent"],1)
        no_file=self.post(title="Link only",youtube_consent="yes",spotlight_consent="yes")
        self.assertEqual(no_file.status_code,201)
        with service.db() as con:
            self.assertEqual(con.execute("SELECT youtube_consent FROM submissions WHERE id=?",
               (no_file.json["id"],)).fetchone()[0],0)
        data=self.data(link="")
        data["audio"]=(io.BytesIO(b"x"*2000),"without-consent.mp3")
        data["spotlight_consent"]="yes"
        response=self.client.post("/api/ai-music/submissions",headers=self.origin,data=data)
        self.assertEqual(response.status_code,201)
        with service.db() as con:
            self.assertEqual(con.execute("SELECT youtube_consent FROM submissions WHERE id=?",
               (response.json["id"],)).fetchone()[0],0)

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

    def test_editor_can_attach_missing_audio_without_losing_votes_or_approval(self):
        sid=self.post(title="Roma",artist="Massimo Sculli",link="https://youtu.be/example").json["id"]
        self.assertEqual(self.client.post(
            f"/api/ai-music/admin/submissions/{sid}/review",
            headers=self.admin,json={"status":"approved"}).status_code,200)
        audio_url=f"/api/ai-music/admin/submissions/{sid}/attach-audio"
        self.assertEqual(self.client.post(audio_url,data={
            "audio":(io.BytesIO(b"x"*2300),"Roma.mp3")}).status_code,401)
        vote=self.client.post(f"/api/ai-music/spotlight/{sid}/vote",
                headers=self.origin,json={"visitor":"49c55ac8-c3fe-4a1f-8a9f-dda66b10e8d6"})
        self.assertEqual(vote.status_code,201)
        with patch.object(service.subprocess,"run") as probe:
            probe.return_value.returncode=0
            probe.return_value.stdout="codec_type=audio"
            attach=self.client.post(audio_url,headers=self.admin,data={
                "audio":(io.BytesIO(b"x"*2300),"Roma.mp3")})
        self.assertEqual(attach.status_code,201,attach.get_json())
        self.assertTrue(attach.json["preserved_votes"])
        duplicate=self.client.post(audio_url,headers=self.admin,data={
            "audio":(io.BytesIO(b"y"*2300),"Other.mp3")})
        self.assertEqual(duplicate.status_code,409)
        chart=self.client.get("/api/ai-music/spotlight").json["tracks"]
        self.assertEqual(len(chart),1)
        self.assertEqual(chart[0]["id"],sid)
        self.assertEqual(chart[0]["title"],"Roma")
        self.assertEqual(chart[0]["votes"],1)
        with service.db() as con:
            item=con.execute("SELECT status,file_name,spotlight_consent,youtube_consent FROM submissions WHERE id=?",(sid,)).fetchone()
            self.assertEqual(item["status"],"approved")
            self.assertEqual(item["file_name"],"Roma.mp3")
            self.assertEqual(item["spotlight_consent"],0)
            self.assertEqual(item["youtube_consent"],0)

    def test_editor_youtube_consent_requires_explicit_authorization_and_audio(self):
        sid=self.post(title="Roma").json["id"]
        url=f"/api/ai-music/admin/submissions/{sid}/youtube-consent"
        self.assertEqual(self.client.post(url,json={"enabled":True,
             "artist_permission_confirmed":True,
             "youtube_live_recording_authorized":True}).status_code,401)
        self.assertEqual(self.client.post(url,headers=self.admin,json={"enabled":True,
             "artist_permission_confirmed":True,
             "youtube_live_recording_authorized":True}).status_code,400)
        self.client.post(f"/api/ai-music/admin/submissions/{sid}/review",
            headers=self.admin,json={"status":"approved"})
        self.assertEqual(self.client.post(url,headers=self.admin,json={"enabled":True,
             "artist_permission_confirmed":True,
             "youtube_live_recording_authorized":True}).status_code,400)
        attach=f"/api/ai-music/admin/submissions/{sid}/attach-audio"
        with patch.object(service.subprocess,"run") as probe:
            probe.return_value.returncode=0
            probe.return_value.stdout="codec_type=audio"
            self.assertEqual(self.client.post(attach,headers=self.admin,
                data={"audio":(io.BytesIO(b"x"*2300),"Roma.mp3")}).status_code,201)
        self.assertEqual(self.client.post(url,headers=self.admin,
            json={"enabled":True}).status_code,400)
        self.assertEqual(self.client.post(url,headers=self.admin,
            json={"enabled":True,"artist_permission_confirmed":True,
                  "youtube_live_recording_authorized":True}).status_code,200)
        self.assertEqual(self.client.post(url,headers=self.admin,
            json={"enabled":False}).status_code,200)
        with service.db() as con:
            self.assertEqual(con.execute("SELECT youtube_consent FROM submissions WHERE id=?",(sid,)).fetchone()[0],0)

    def test_editor_rejects_invalid_source_audio_without_changing_submission(self):
        sid=self.post(title="Roma").json["id"]
        url=f"/api/ai-music/admin/submissions/{sid}/attach-audio"
        self.assertEqual(self.client.post(url,headers=self.admin,
            data={"audio":(io.BytesIO(b"x"*2300),"fake.exe")}).status_code,400)
        with patch.object(service.subprocess,"run") as probe:
            probe.return_value.returncode=1
            probe.return_value.stdout=""
            self.assertEqual(self.client.post(url,headers=self.admin,
                data={"audio":(io.BytesIO(b"x"*2300),"fake.mp3")}).status_code,400)
        with service.db() as con:
            self.assertIsNone(con.execute("SELECT stored_name FROM submissions WHERE id=?",(sid,)).fetchone()[0])

    def test_authenticated_identity_used_even_before_login_becomes_mandatory(self):
        # Members must never have to type their name/email again; editable
        # client fields cannot override Google verified identity.
        with patch.object(service,"GOOGLE_AUTH_READY",True), \
             patch.object(service,"AUTH_REQUIRED",False), \
             patch.object(service,"verify_google_credential",
                 return_value=("member@gmail.com","google-member-identity-009","Ionel Varga")):
            response=self.client.post("/api/ai-music/auth/google",
                headers=self.origin,json={
                    "credential":"a"*100,"nonce":"nonce_for_member_test_123456"})
            self.assertEqual(response.status_code,200)
            token=response.json["session"]
            headers={**self.origin,"Authorization":"Bearer "+token}
            upload=self.client.post("/api/ai-music/submissions",headers=headers,
                data=self.data(title="Own composition",
                               artist="Forged Artist",
                               email="forged@example.org"))
            self.assertEqual(upload.status_code,201)
            sid=upload.json["id"]
            with service.db() as con:
                track=con.execute("SELECT artist,email,user_id FROM submissions WHERE id=?",
                                  (sid,)).fetchone()
                self.assertEqual(track["artist"],"Ionel Varga")
                self.assertEqual(track["email"],"member@gmail.com")
                self.assertEqual(track["user_id"],response.json["user"]["id"])
            review=self.client.post(f"/api/ai-music/admin/submissions/{sid}/review",
                headers=self.admin,json={"status":"approved"})
            self.assertEqual(review.status_code,200)
            comment=self.client.post(f"/api/ai-music/spotlight/{sid}/comments",
                headers=headers,json={"body":"Great melody","nickname":"Forged commenter"})
            self.assertEqual(comment.status_code,201)
            visible=self.client.get(f"/api/ai-music/spotlight/{sid}/comments")
            self.assertEqual(visible.json["comments"][0]["nickname"],"Ionel Varga")
            # Stale credentials must not silently fall back to guest submission.
            unauthorized=self.client.post("/api/ai-music/submissions",
                headers={**self.origin,"Authorization":"Bearer invalid_session"},
                data=self.data(title="Forged"))
            self.assertEqual(unauthorized.status_code,401)

    def test_google_member_login_reuses_verified_email_and_existing_tracks(self):
        # A previously submitted artist must get the SAME RDI identity.
        old=self.post(title="Earlier submission",email="artist@gmail.com")
        self.assertEqual(old.status_code,201)
        nonce="google_nonce_test_1234567890"
        endpoint="/api/ai-music/auth/google"
        with patch.object(service,"GOOGLE_AUTH_READY",True), \
             patch.object(service,"GOOGLE_CLIENT_ID","test.apps.googleusercontent.com"), \
             patch.object(service,"AUTH_REQUIRED",True), \
             patch.object(service,"verify_google_credential",
                 return_value=("artist@gmail.com","google-sub-001","Google Artist")):
            credentials={"credential":"a"*100,"nonce":nonce}
            login=self.client.post(endpoint,headers=self.origin,json=credentials)
            self.assertEqual(login.status_code,200)
            self.assertTrue(login.json["session"])
            user=login.json["user"]
            self.assertEqual(user["email"],"artist@gmail.com")
            auth={**self.origin,"Authorization":"Bearer "+login.json["session"]}
            me=self.client.get("/api/ai-music/auth/me",headers=auth)
            self.assertEqual(me.status_code,200)
            owned=self.client.get("/api/ai-music/me/submissions",headers=auth)
            self.assertEqual(owned.status_code,200)
            self.assertEqual([x["id"] for x in owned.json["submissions"]],[old.json["id"]])
            uploaded=self.client.post("/api/ai-music/submissions",headers=auth,
                data=self.data(email="malicious@example.org",title="New Google track"))
            self.assertEqual(uploaded.status_code,201)
            with service.db() as con:
                rows=con.execute("SELECT id,email,user_id FROM submissions ORDER BY created_at").fetchall()
                self.assertEqual(len(rows),2)
                self.assertEqual(set(row["email"] for row in rows),{"artist@gmail.com"})
                self.assertEqual(set(row["user_id"] for row in rows),{user["id"]})
            second=self.client.post(endpoint,headers=self.origin,json=credentials)
            self.assertEqual(second.status_code,200)
            self.assertEqual(second.json["user"]["id"],user["id"])
            with service.db() as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM music_users").fetchone()[0],1)

    def test_google_login_does_not_link_different_google_account(self):
        nonce="google_nonce_test_1234567890"
        endpoint="/api/ai-music/auth/google"
        credential={"credential":"a"*100,"nonce":nonce}
        with patch.object(service,"GOOGLE_AUTH_READY",True), \
             patch.object(service,"GOOGLE_CLIENT_ID","test.apps.googleusercontent.com"), \
             patch.object(service,"verify_google_credential",
                 side_effect=[("music@gmail.com","google-sub-001","Artist A"),
                              ("music@gmail.com","google-sub-002","Artist B")]):
            self.assertEqual(self.client.post(endpoint,headers=self.origin,json=credential).status_code,200)
            forbidden=self.client.post(endpoint,headers=self.origin,json=credential)
            self.assertEqual(forbidden.status_code,409)
            with service.db() as con:
                self.assertEqual(con.execute("SELECT COUNT(*) FROM music_users").fetchone()[0],1)

    def test_google_login_off_wrong_origin_bad_token_and_no_code(self):
        endpoint="/api/ai-music/auth/google"
        params={"credential":"a"*100,"nonce":"google_nonce_test_1234567890"}
        # Simulate Google sign-in explicitly disabled, even when a valid Client ID
        # is configured in production and the google-auth library is installed.
        with patch.object(service,"GOOGLE_AUTH_READY",False):
            self.assertEqual(self.client.post(endpoint,headers=self.origin,json=params).status_code,503)
        with patch.object(service,"GOOGLE_AUTH_READY",True), \
             patch.object(service,"verify_google_credential",side_effect=ValueError("Bad token")):
            self.assertEqual(self.client.post(endpoint,headers={"Origin":"https://wrong.example.org"},
                json=params).status_code,403)
            self.assertEqual(self.client.post(endpoint,headers=self.origin,
                json={"credential":"short","nonce":params["nonce"]}).status_code,400)
            self.assertEqual(self.client.post(endpoint,headers=self.origin,
                json={"credential":"a"*100,"nonce":"short"}).status_code,400)
            self.assertEqual(self.client.post(endpoint,headers=self.origin,json=params).status_code,401)

    def test_google_credential_claims_must_match_google_client_and_nonce(self):
        import types
        payload={
            "iss":"https://accounts.google.com",
            "aud":"test.apps.googleusercontent.com",
            "nonce":"nonce_for_test_1234567890",
            "email_verified":True,
            "email":"artist@gmail.com",
            "sub":"google-account-sub-001",
            "name":"Artist RDI",
        }
        fake=types.SimpleNamespace(verify_oauth2_token=lambda *args,**kw:payload.copy())
        with patch.object(service,"GOOGLE_AUTH_READY",True), \
             patch.object(service,"GOOGLE_CLIENT_ID","test.apps.googleusercontent.com"), \
             patch.object(service,"google_id_token",fake), \
             patch.object(service,"GoogleAuthRequest",return_value=object()):
            self.assertEqual(service.verify_google_credential("a"*100,payload["nonce"]),
                             ("artist@gmail.com","google-account-sub-001","Artist RDI"))
            for k,v in [
                ("aud","wrong.client.id"),("iss","https://not.google.example"),
                ("email_verified",False),("nonce","wrong_nonce"),
                ("email","outside@example.org")]:
                tampered=payload.copy()
                tampered[k]=v
                fake.verify_oauth2_token=lambda *args,**kwargs:tampered.copy()
                with self.assertRaises(ValueError,msg=k):
                    service.verify_google_credential("a"*100,payload["nonce"])

    def test_email_member_login_and_guarded_actions(self):
        with patch.object(service,"AUTH_MAIL_READY",True), \
             patch.object(service,"AUTH_REQUIRED",True), \
             patch.object(service,"send_music_login_email") as deliver, \
             patch.object(service.secrets,"randbelow",return_value=123456):
            auth="/api/ai-music/auth"
            config=self.client.get(auth+"/config")
            self.assertEqual(config.status_code,200)
            self.assertTrue(config.json["login_required"])
            self.assertEqual(self.post(title="Anonymous").status_code,401)
            request_code=self.client.post(auth+"/request-code",headers=self.origin,
                  json={"email":"artist@example.org","name":"Test Music Artist"})
            self.assertEqual(request_code.status_code,200)
            deliver.assert_called_once_with("artist@example.org","123456")
            wrong=self.client.post(auth+"/verify-code",headers=self.origin,
                json={"email":"artist@example.org","code":"000000"})
            self.assertEqual(wrong.status_code,401)
            verified=self.client.post(auth+"/verify-code",headers=self.origin,
                json={"email":"artist@example.org","code":"123456"})
            self.assertEqual(verified.status_code,200)
            token=verified.json["session"]
            headers={**self.origin,"Authorization":"Bearer "+token}
            me=self.client.get(auth+"/me",headers=headers)
            self.assertEqual(me.status_code,200)
            self.assertEqual(me.json["user"]["display_name"],"Test Music Artist")
            submission=self.client.post("/api/ai-music/submissions",
                  data=self.data(title="Protected song"),headers=headers)
            self.assertEqual(submission.status_code,201)
            self.assertEqual(len(self.client.get("/api/ai-music/me/submissions",headers=headers).json["submissions"]),1)
            sid=submission.json["id"]
            self.assertEqual(self.client.post(f"/api/ai-music/admin/submissions/{sid}/review",
                  headers=self.admin,json={"status":"approved"}).status_code,200)
            visitor="8d9b18ca-7c76-4f6b-90f1-85ba92e1cd20"
            vote_url=f"/api/ai-music/spotlight/{sid}/vote"
            self.assertEqual(self.client.post(vote_url,headers=self.origin,
                  json={"visitor":visitor}).status_code,401)
            self.assertEqual(self.client.post(vote_url,headers=headers,
                  json={"visitor":visitor}).status_code,201)
            self.assertEqual(self.client.post(vote_url,headers=headers,
                  json={"visitor":"9d9b18ca-7c76-4f6b-90f1-85ba92e1cd20"}).status_code,409)
            comment_url=f"/api/ai-music/spotlight/{sid}/comments"
            self.assertEqual(self.client.post(comment_url,headers=self.origin,
                  json={"nickname":"Someone","body":"Great music"}).status_code,401)
            comment=self.client.post(comment_url,headers=headers,
                  json={"nickname":"Unknown","body":"Wonderful song"})
            self.assertEqual(comment.status_code,201)
            visible=self.client.get(comment_url).json["comments"]
            self.assertEqual(visible[0]["nickname"],"Test Music Artist")
            self.assertEqual(self.client.post(auth+"/logout",headers=headers).status_code,200)
            self.assertEqual(self.client.get(auth+"/me",headers=headers).status_code,401)

    def test_email_code_rate_and_expiry(self):
        with patch.object(service,"AUTH_MAIL_READY",True), \
             patch.object(service,"send_music_login_email"), \
             patch.object(service.secrets,"randbelow",return_value=123456):
            for i in range(1):
                self.assertEqual(self.client.post("/api/ai-music/auth/request-code",
                    headers=self.origin,json={"email":"artist@example.org"}).status_code,200)
            self.assertEqual(self.client.post("/api/ai-music/auth/request-code",
                headers=self.origin,json={"email":"artist@example.org"}).status_code,429)
            for i in range(5):
                self.assertEqual(self.client.post("/api/ai-music/auth/verify-code",
                    headers=self.origin,json={"email":"artist@example.org","code":"000000"}).status_code,401)
            self.assertEqual(self.client.post("/api/ai-music/auth/verify-code",
                headers=self.origin,json={"email":"artist@example.org","code":"123456"}).status_code,401)

    def test_rate_limit_persists_across_requests(self):
        # The batch upload UI sends ten separate requests; they must all succeed.
        self.assertGreaterEqual(service.RATE_MAX, 10)
        for i in range(service.RATE_MAX):
            response=self.post(title=f"Track {i+1}")
            self.assertEqual(response.status_code, 201)
        rejected=self.post(title="Over the limit")
        self.assertEqual(rejected.status_code, 429)
        self.assertIn("Retry-After",rejected.headers)
        self.assertGreater(int(rejected.headers["Retry-After"]),0)
        self.assertEqual(rejected.json["retry_after_seconds"],int(rejected.headers["Retry-After"]))
        with service.db() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM rate_events").fetchone()[0], service.RATE_MAX)

    def test_six_prior_uploads_leave_room_for_four_more(self):
        # Reproduce the real-world case: six existing songs, four left to send.
        for i in range(6):
            self.assertEqual(self.post(title=f"Already submitted {i+1}").status_code,201)
        for i in range(4):
            self.assertEqual(self.post(title=f"Remaining {i+1}").status_code,201)
        with service.db() as con:
            self.assertEqual(con.execute("SELECT COUNT(*) FROM submissions").fetchone()[0],10)

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

    def test_spotlight_pagination_and_playlist_consent(self):
        with patch.object(service,"RATE_MAX",100):
            for i in range(23):
                sid=self.post(title=f"Song {i}").json["id"]
                self.assertEqual(self.client.post(f"/api/ai-music/admin/submissions/{sid}/review",
                    headers=self.admin,json={"status":"approved"}).status_code,200)
        first=self.client.get("/api/ai-music/spotlight?page=1").json
        second=self.client.get("/api/ai-music/spotlight?page=2").json
        self.assertEqual(first["total"],23)
        self.assertEqual(first["total_pages"],2)
        self.assertEqual(len(first["tracks"]),20)
        self.assertEqual(len(second["tracks"]),3)
        self.assertEqual(set(t["id"] for t in first["tracks"]) &
                         set(t["id"] for t in second["tracks"]),set())
        self.assertEqual(self.client.get("/api/ai-music/spotlight/playlist").json["tracks"],[])
        self.assertEqual(self.client.get("/api/ai-music/spotlight?page=garbage").status_code,200)

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
