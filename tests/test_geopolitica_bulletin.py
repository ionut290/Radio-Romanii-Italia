"""Editorial safeguards for hourly RDI geopolitical bulletin."""
import datetime as dt
import importlib.util
import pathlib
import unittest
from zoneinfo import ZoneInfo

PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts/build_geopolitica_bulletin.py"
SPEC = importlib.util.spec_from_file_location("rdi_geopolitica_bulletin", PATH)
bulletin = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bulletin)
ROME = ZoneInfo("Europe/Rome")
NOW = dt.datetime(2026, 10, 27, 17, 30, tzinfo=ROME)


def news(**overrides):
    item = {
        "id": "editorial-test-1", "published_date": "2026-10-27",
        "title_ro": "Un titlu verificat de redacție", "title_it": "Un titolo verificato dalla redazione",
        "summary_ro": "Redacția a verificat această relatare pe baza surselor identificabile, iar informațiile rămân atribuite acestora.",
        "summary_it": "La redazione ha verificato la notizia sulla base delle fonti indicate; le informazioni restano attribuite alle fonti.",
        "source_name": "Agenție de presă", "source_url": "https://example.org/news/1",
        "region": "Ucraina",
    }
    item.update(overrides)
    return item


class TestBulletin(unittest.TestCase):
    def test_verified_curated_news_can_be_read(self):
        program = bulletin.build(NOW, "ro", {"items": [news()]}, {})
        self.assertIsNotNone(program)
        self.assertEqual(program["story_count"], 1)
        self.assertIn("Ucraina.", program["text"])
        self.assertIn("Un titlu verificat", program["text"])
        self.assertNotIn("Un titolo verificato", program["text"])

    def test_italian_is_fully_localized(self):
        program = bulletin.build(NOW, "it", {"items": [news()]}, {})
        self.assertIn("Per leggere gli articoli completi", program["text"])
        self.assertIn("Ucraina.", program["text"])
        self.assertNotIn("Secondo la fonte", program["text"])
        self.assertNotIn("Agenție de presă", program["text"])
        self.assertIn("Un titolo verificato", program["text"])
        self.assertNotIn("Un titlu verificat", program["text"])
        self.assertEqual(program["segments"][1]["kind"], "story")
        self.assertTrue(program["segments"][1]["text"].startswith("Ucraina."))
        self.assertEqual(program["articles"][0]["source_name"], "Agenție de presă")

    def test_unverified_external_geopolitical_feed_is_never_spoken(self):
        self.assertIsNone(bulletin.build(NOW, "ro", {}, {"items": [news()]}))

    def test_explicitly_approved_extra_news_is_eligible(self):
        story = news(editorial_verified=True, approved_for_radio=True)
        self.assertIsNotNone(bulletin.build(NOW, "ro", {}, {"items": [story]}))

    def test_stale_item_skipped(self):
        self.assertIsNone(bulletin.build(NOW, "ro", {"items": [news(published_date="2026-10-21")]}, {}))

    def test_future_item_skipped(self):
        self.assertIsNone(bulletin.build(NOW, "ro", {"items": [news(published_date="2026-10-29")]}, {}))

    def test_invalid_source_url_skipped(self):
        self.assertIsNone(bulletin.build(NOW, "ro", {"items": [news(source_url="http://unsafe.test")]}, {}))

    def test_missing_translation_skipped(self):
        self.assertIsNone(bulletin.build(NOW, "it", {"items": [news(title_it="")]}, {}))

    def test_source_mentions_removed_from_speech(self):
        passage = ("Secondo Reuters e AP, il 27 ottobre si è verificato un evento. "
                   "Un testimone Reuters ha riferito i fatti.")
        spoken = bulletin.broadcast_summary(passage, "it", "Reuters")
        self.assertNotIn("Reuters", spoken)
        self.assertNotIn("Secondo", spoken)
        self.assertIn("testimone", spoken)

    def test_default_language_is_italian(self):
        import argparse
        self.assertEqual(bulletin.build(NOW, "it", {"items": [news()]}, {})["language"], "it")

    def test_recently_spoken_story_is_not_repeated(self):
        item = news()
        signature = bulletin.story_signature({
            "title": item["title_it"], "summary": item["summary_it"]
        })
        history = {"editions": [{"signatures": [signature]}]}
        self.assertIsNone(bulletin.build(NOW, "it", {"items": [item]}, {}, history))

    def test_new_verified_secondary_story_replaces_used_story(self):
        first = news()
        second = news(id="new-story", source_url="https://example.org/news/2",
                      region="Sudan", title_it="Un altro fatto verificato")
        signature = bulletin.story_signature({
            "title": first["title_it"], "summary": first["summary_it"]
        })
        program = bulletin.build(NOW, "it", {"items": [first, second]}, {},
                                 {"editions": [{"signatures": [signature]}]})
        self.assertEqual(program["story_count"], 1)
        self.assertEqual(program["articles"][0]["id"], "new-story")

    def test_substantive_update_can_be_selected(self):
        original = news()
        updated = news(summary_it="Un nuovo aggiornamento verificato aggiunge dettagli sostanziali e concreti alla notizia originaria.")
        signature = bulletin.story_signature({
            "title": original["title_it"], "summary": original["summary_it"]
        })
        program = bulletin.build(NOW, "it", {"items": [updated]}, {},
                                 {"editions": [{"signatures": [signature]}]})
        self.assertEqual(program["story_count"], 1)

    def test_duplicate_source_skipped(self):
        first = news()
        second = news(id="other", title_ro="Altă știre")
        program = bulletin.build(NOW, "ro", {"items": [first, second]}, {})
        self.assertEqual(program["story_count"], 1)


if __name__ == "__main__":
    unittest.main()
