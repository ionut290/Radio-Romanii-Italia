"""Safety and relevance tests for RDI 18:00 television footage."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tg_video_rights", ROOT / "scripts/tg_video_rights.py")
rights = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rights)

REVIEWED = {
    "id": "it-roma-pexels",
    "kind": "video", "rights_reviewed": True, "audio_muted": True,
    "editorial_visual": True, "credit": "Florian Delée / Pexels",
    "reviewed_on": "2026-10-29",
    "src": "https://videos.pexels.com/video-files/36386388/15430954_2560_1440_30fps.mp4",
    "source_url": "https://www.pexels.com/video/aerial-view-of-historic-rome-skyline-36386388/",
    "license_url": "https://www.pexels.com/license/"
}
LIBRARY = {
    "schema_version": 1,
    "event_clips": [],
    "repertory_clips": [{
        "id": "rome-cinema-context", "landscape_id": "it-roma-pexels",
        "all_terms": [["roma", "romano"], ["cinema", "film", "festival"]],
        "max_seconds": 14,
    }],
}
LANDSCAPES = {"items": [REVIEWED]}


def story(title="Il cinema romeno a Roma, presentato un film al festival"):
    return {"title_original": title, "source_url": "https://example.org/news/1",
            "category": "Diaspora"}


class VideoSafetyTests(unittest.TestCase):
    def test_relevant_city_cinema_broll_is_authorized_and_silent(self):
        got = rights.select_video(story(), LIBRARY, LANDSCAPES)
        self.assertEqual(got["kind"], "repertory")
        self.assertEqual(got["seconds"], 14)
        self.assertIn("REPERTORIO", got["notice"])

    def test_unrelated_article_has_no_video(self):
        self.assertIsNone(rights.select_video(story("Riforma pensioni nel 2027"), LIBRARY, LANDSCAPES))
        self.assertIsNone(rights.select_video(story("Inaugurato il centro sportivo di Roma"), LIBRARY, LANDSCAPES))

    def test_sensitive_news_is_not_associated_with_random_stock_video(self):
        self.assertIsNone(rights.select_video(story("Incendio durante un festival cinematografico a Roma"), LIBRARY, LANDSCAPES))

    def test_unreviewed_stock_or_unmuted_footage_does_not_air(self):
        for override in ({"rights_reviewed": False}, {"audio_muted": False},
                         {"license_url": ""}, {"source_url": "https://example.org/a"},
                         {"src": "https://evil.example.org/watch/123"}):
            modified = {"items": [{**REVIEWED, **override}]}
            self.assertIsNone(rights.select_video(story(), LIBRARY, modified))

    def test_same_stock_clip_not_reused_for_multiple_stories(self):
        items = [story(), story("Un festival cinema a Roma apre le porte")]
        found = rights.resolve_for_stories(items, LIBRARY, LANDSCAPES)
        self.assertEqual(sum(x is not None for x in found), 1)

    def test_publisher_embed_not_permitted_by_merely_exposing_a_video(self):
        news = {**story(), "video": "https://media.publisher.it/news.mp4",
                "video_url": "https://media.publisher.it/news.mp4"}
        self.assertEqual(rights.select_video(news, {"schema_version": 1, "event_clips": [],
                         "repertory_clips": []}, LANDSCAPES), None)

    def test_approved_article_original_video_selected_first(self):
        event = {
            "id": "approved-event", "article_url": story()["source_url"],
            "src": "https://media.publisher.it/news.mp4", "youtube_live_authorized": True,
            "rights_reviewed": True, "audio_muted": True,
            "license_reference": "https://publisher.it/licenza/rdi/2026-10-30",
            "permission_reference": "Autorizzazione scritta RDI del 30 ottobre 2026",
            "reviewed_on": "2026-10-30", "credit": "Editore"
        }
        lib = {**LIBRARY, "event_clips": [event]}
        got = rights.select_video(story(), lib, LANDSCAPES)
        self.assertEqual(got["kind"], "event")
        self.assertEqual(got["src"], event["src"])
        self.assertIn("DELL'EVENTO", got["notice"])
        for flag in ("rights_reviewed", "youtube_live_authorized", "audio_muted"):
            self.assertNotEqual(
                rights.select_video(story(), {**lib, "event_clips": [{**event, flag: False}]},
                                    {"items": []}), got)

    def test_mismatched_event_article_url_never_gets_the_footage(self):
        record = {
            "article_url": "https://example.org/another-event",
            "src": "https://media.publisher.it/news.mp4",
            "youtube_live_authorized": True, "rights_reviewed": True,
            "audio_muted": True, "license_reference": "https://publisher.it/licenza",
            "permission_reference": "Permesso specifico per il servizio pubblicato",
            "reviewed_on": "2026-10-30", "credit": "Editore",
        }
        self.assertIsNone(rights.select_video(story(),
                        {"schema_version": 1, "event_clips": [record], "repertory_clips": []},
                        {"items": []}))

    def test_video_host_safety(self):
        for bad in ("https://youtube.com/watch?v=123", "http://media.example.com/a.mp4",
                    "https://127.0.0.1/a.mp4", "https://localhost/a.mp4",
                    "https://media.example.org/watch", "javascript:alert(1)"):
            self.assertFalse(rights.safe_media_url(bad), bad)
        self.assertTrue(rights.safe_media_url("https://media.example.org/a.mp4"))


if __name__ == "__main__":
    unittest.main()
