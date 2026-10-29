#!/usr/bin/env python3
"""Test offline del catalogo video: non deve mai autorizzare automaticamente."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from zoneinfo import ZoneInfo

file = Path(__file__).resolve().parents[1] / "scripts/update_europa_videos.py"
spec = importlib.util.spec_from_file_location("rdi_europa", file)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
NOW = dt.datetime(2026, 10, 29, 19, tzinfo=dt.timezone.utc)


class EuropaCatalogTests(unittest.TestCase):
    def test_rss_does_not_approve_audio(self):
        source = mod.SOURCES[0]
        xml = b"""<rss><channel><item><title>Conferenza stampa UE</title><link>https://www.europarl.europa.eu/news/it/press-room/2026/test-video</link><pubDate>Thu, 29 Oct 2026 09:00:00 GMT</pubDate></item></channel></rss>"""
        data = mod.parse_rss(xml, source)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["status"], "DA_VERIFICARE")
        self.assertFalse(data[0]["audio_italiano_verificato"])
        self.assertFalse(data[0]["diritti_verificati"])

    def test_commission_listing(self):
        source = mod.SOURCES[1]
        html = b'<a href="/en/media/video/I-291498">EU poverty strategy 29/10/2026 02:05</a>'
        data = mod.parse_listing(html, source)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["published_at"], "2026-10-29")
        self.assertEqual(data[0]["language_hint"], "und")

    def test_host_does_not_trust_lookalikes(self):
        self.assertFalse(mod.page_allowed("https://audiovisual.ec.europa.eu.evil.example/en/media/video/I-42"))
        self.assertFalse(mod.page_allowed("http://audiovisual.ec.europa.eu/en/media/video/I-42"))
        self.assertTrue(mod.page_allowed("https://audiovisual.ec.europa.eu/en/media/video/I-42"))

    def test_no_approvals_means_no_program(self):
        schedule = mod.build_schedule([], NOW)
        self.assertFalse(schedule["live_enabled"])
        self.assertEqual(len(schedule["daily_schedule"]), 8)
        self.assertTrue(all(day["status"] == "NESSUN_VIDEO_APPROVATO" for day in schedule["daily_schedule"]))

    def test_gate_and_dst(self):
        item = dict(
            id="video-1", source_id="commissione_europea", title="Un servizio sull'Unione europea",
            source_url="https://audiovisual.ec.europa.eu/en/media/video/I-291498",
            media_url="https://audiovisual.ec.europa.eu/clip.mp4",
            rights_url="https://audiovisual.ec.europa.eu/en/conditions-of-use",
            duration_seconds=125, approved=True, audio_italiano_verificato=True,
            diritti_verificati=True, musica_e_terzi_verificati=True,
            video_completo=True, reviewed_by="RDI", reviewed_at="2026-10-29T11:00:00+01:00",
            credit="© European Union, 2026, CC BY 4.0",
        )
        self.assertTrue(mod.eligible_video(item, NOW))
        item["musica_e_terzi_verificati"] = False
        self.assertFalse(mod.eligible_video(item, NOW))
        item["musica_e_terzi_verificati"] = True
        schedule = mod.build_schedule([item], NOW)
        self.assertEqual(schedule["ready_videos"][0]["id"], "video-1")
        self.assertFalse(schedule["live_enabled"])
        self.assertEqual(schedule["daily_schedule"][0]["starts_at"], "2026-10-29T18:00:00+01:00")
        winter = mod.build_schedule([item], dt.datetime(2027, 3, 27, 13, tzinfo=dt.timezone.utc))
        self.assertEqual(winter["daily_schedule"][1]["starts_at"], "2027-03-28T18:00:00+02:00")


if __name__ == "__main__":
    unittest.main()
