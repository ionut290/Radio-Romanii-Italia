#!/usr/bin/env python3
"""Test offline del catalogo video: non deve mai autorizzare automaticamente."""
import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from types import SimpleNamespace
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

    def test_malformed_parliament_rss_recovers_items(self):
        source = mod.SOURCES[0]
        xml = (b'<rss><channel><item><title>Video di un altro evento</title>'
               b'<link>https://multimedia.europarl.europa.eu/it/otherevents_20261021_vd</link>'
               b'<description>Durata 60 min.<br><br>Test</description>'
               b'<pubDate>Wed, 21 Oct 2026 17:00:00 GMT</pubDate>'
               b'</item></channel></rss>')
        items = mod.parse_rss(xml, source)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["language_hint"], "it")
        self.assertFalse(items[0]["audio_italiano_verificato"])

    def test_commission_listing(self):
        source = mod.SOURCES[1]
        html = b'<a href="/en/media/video/I-291498">EU poverty strategy 29/10/2026 02:05</a>'
        data = mod.parse_listing(html, source)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["published_at"], "2026-10-29")
        self.assertEqual(data[0]["language_hint"], "und")

    def test_ep_news_on_eu_av_portal(self):
        source = mod.SOURCES[1]
        html = b'<a href="/en/media/video/I-297008">EP News Visit by Roberta METSOLA 29/10/2026 03:23</a>'
        data = mod.parse_listing(html, source)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["source_id"], "parlamento_europeo")
        self.assertFalse(data[0]["diritti_verificati"])

    def test_italian_language_metadata_is_explicit(self):
        example = (b"<html><body><h1>Italian speech requested</h1>"
                   b"<section>Media information ID I-294336 Date 15/09/2026 "
                   b"Languages Original English Italiano "
                   b"Personalities Jack Chambers Raffaele Fitto</section></body></html>")
        declared, available = mod.declared_language_versions(example)
        self.assertTrue(available)
        self.assertEqual(declared, "Original English Italiano")

    def test_italy_title_and_italian_site_are_not_audio(self):
        bad = (b"<h1>Italy talks of Italian policy</h1><section>"
               b"Languages Original English francais Category Clip</section>")
        declared, available = mod.declared_language_versions(bad)
        self.assertFalse(available)
        self.assertEqual(declared, "Original English francais")
        self.assertEqual(mod.declared_language_versions(b"<h1>Italia</h1>"), ("", False))

    def test_browser_fallback_parses_actual_rendered_languages(self):
        html = b"<html><p>Languages Original English Italiano</p><p>Personalities Two Speakers</p></html>"
        with patch.object(mod.shutil, "which", return_value="/usr/bin/google-chrome"), patch.object(
            mod.subprocess, "run", return_value=SimpleNamespace(returncode=0, stdout=html)
        ) as run:
            data = mod.fetch_rendered_metadata("https://audiovisual.ec.europa.eu/en/media/video/I-294336")
            self.assertTrue(mod.declared_language_versions(data)[1])
            self.assertIn("--dump-dom", run.call_args.args[0])
            self.assertLessEqual(run.call_args.kwargs["timeout"], 30)
        self.assertIsNone(mod.fetch_rendered_metadata("https://untrusted.example/media/video/I-1"))

    def test_italian_reference_is_pending_review(self):
        samples = mod.official_italian_examples(NOW)
        self.assertEqual(len(samples), 1)
        self.assertTrue(samples[0]["italian_version_available"])
        self.assertTrue(samples[0]["italian_audio_in_player_verified"])
        self.assertTrue(samples[0]["italian_audio_download_option_verified"])
        self.assertFalse(samples[0]["audio_italiano_verificato"])
        self.assertFalse(mod.eligible_video(samples[0], NOW))

    def test_separate_italian_audio_requires_explicit_sync(self):
        self.assertTrue(mod.official_italian_examples(NOW)[0]["italian_audio_download_option_verified"])
        data = {
            "approved": True, "audio_italiano_verificato": True, "diritti_verificati": True,
            "musica_e_terzi_verificati": True, "video_completo": True,
            "audio_track_language": "it", "audio_sync_verified": True,
            "source_id": "commissione_europea", "title": "Conferenza stampa sul diritto europeo",
            "reviewed_by": "RDI", "reviewed_at": "2026-10-29T12:00:00+01:00",
            "credit": "European Union", "media_url": "https://audiovisual.ec.europa.eu/video.mp4",
            "source_url": "https://audiovisual.ec.europa.eu/en/media/video/I-294336",
            "rights_url": "https://audiovisual.ec.europa.eu/en/conditions-of-use",
            "duration_seconds": 949, "audio_mode": "separate_it",
            "audio_url": "https://audiovisual.ec.europa.eu/it.aac",
            "original_audio_muted": True, "audio_offset_ms": 0,
        }
        self.assertTrue(mod.eligible_video(data, NOW))
        data["original_audio_muted"] = False
        self.assertFalse(mod.eligible_video(data, NOW))
        data["original_audio_muted"] = True
        data["audio_offset_ms"] = 7000
        self.assertFalse(mod.eligible_video(data, NOW))
        data["audio_offset_ms"] = 0
        data["audio_sync_verified"] = False
        self.assertFalse(mod.eligible_video(data, NOW))


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
            video_completo=True, audio_track_language="it", audio_sync_verified=True,
            audio_mode="embedded_it", audio_stream_index=1,
            reviewed_by="RDI", reviewed_at="2026-10-29T11:00:00+01:00",
            credit="© European Union, 2026, CC BY 4.0",
        )
        self.assertTrue(mod.eligible_video(item, NOW))
        item["musica_e_terzi_verificati"] = False
        self.assertFalse(mod.eligible_video(item, NOW))
        item["musica_e_terzi_verificati"] = True
        item["audio_mode"] = "separate_it"
        self.assertFalse(mod.eligible_video(item, NOW))
        item["audio_url"] = "https://audiovisual.ec.europa.eu/italiano.aac"
        item["original_audio_muted"] = True
        item["audio_offset_ms"] = 0
        self.assertTrue(mod.eligible_video(item, NOW))
        item["audio_mode"] = "embedded_it"
        schedule = mod.build_schedule([item], NOW)
        self.assertEqual(schedule["ready_videos"][0]["id"], "video-1")
        self.assertFalse(schedule["live_enabled"])
        self.assertEqual(schedule["daily_schedule"][0]["starts_at"], "2026-10-30T18:00:00+01:00")
        winter = mod.build_schedule([item], dt.datetime(2027, 3, 27, 13, tzinfo=dt.timezone.utc))
        self.assertEqual(winter["daily_schedule"][1]["starts_at"], "2027-03-28T18:00:00+02:00")


if __name__ == "__main__":
    unittest.main()
