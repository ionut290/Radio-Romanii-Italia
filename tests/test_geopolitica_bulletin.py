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
        "region": "Europa",
    }
    item.update(overrides)
    return item


class TestBulletin(unittest.TestCase):
    def test_verified_curated_news_can_be_read(self):
        program = bulletin.build(NOW, "ro", {"items": [news()]}, {})
        self.assertIsNotNone(program)
        self.assertEqual(program["story_count"], 1)
        self.assertIn("Potrivit sursei", program["text"])
        self.assertIn("Un titlu verificat", program["text"])
        self.assertNotIn("Un titolo verificato", program["text"])

    def test_italian_is_fully_localized(self):
        program = bulletin.build(NOW, "it", {"items": [news()]}, {})
        self.assertIn("Secondo la fonte", program["text"])
        self.assertIn("Un titolo verificato", program["text"])
        self.assertNotIn("Un titlu verificat", program["text"])

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

    def test_duplicate_source_skipped(self):
        first = news()
        second = news(id="other", title_ro="Altă știre")
        program = bulletin.build(NOW, "ro", {"items": [first, second]}, {})
        self.assertEqual(program["story_count"], 1)


if __name__ == "__main__":
    unittest.main()
