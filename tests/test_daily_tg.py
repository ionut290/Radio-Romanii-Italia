"""Tests for RDI's 16:00 Europe/Rome editorial cutoff and TV deep-dives."""
import datetime as dt
import importlib.util
import pathlib
import unittest
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("daily_tg", ROOT / "scripts/build_daily_tg.py")
tg = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tg)
ROME = ZoneInfo("Europe/Rome")
NOW = dt.datetime(2026, 10, 30, 16, 25, tzinfo=ROME)


def article(n=1, **extra):
    item = {
        "id": f"test-story-{n}", "category": "Diaspora",
        "title": f"Un importante incontro per la comunità romena nel comune numero {n}",
        "body": "Testo documentato di origine italiana su fatti, contesto e conseguenze. " * 26,
        "summary": "Due fonti riferiscono l'iniziativa.",
        "url": f"https://rdi.example.org/news/{n}",
        "source": "Testata locale",
        "source_urls": [f"https://reporter.example.org/news/{n}",
                        f"https://comune.example.it/notizie/{n}"],
        "published": f"2026-10-30T{9+n:02d}:25:00+01:00",
        "image": "https://random-publisher.example.org/photo.jpg",
        "fallbackImage": "./editorial-images/neutral.svg",
    }
    item.update(extra)
    return item


class DailyTgTests(unittest.TestCase):
    def test_cutoff_rome_winter(self):
        self.assertEqual(tg.cutoff_for(NOW).isoformat(), "2026-10-30T16:00:00+01:00")

    def test_cutoff_rome_summer(self):
        summer = dt.datetime(2026, 7, 9, 17, 5, tzinfo=ROME)
        self.assertEqual(tg.cutoff_for(summer).isoformat(), "2026-07-09T16:00:00+02:00")

    def test_includes_facts_before_16(self):
        self.assertIsNotNone(tg.eligible(article(), tg.cutoff_for(NOW)))

    def test_excludes_facts_after_16(self):
        self.assertIsNone(tg.eligible(article(published="2026-10-30T16:01:00+01:00"),
                                      tg.cutoff_for(NOW)))

    def test_excludes_previous_day(self):
        self.assertIsNone(tg.eligible(article(published="2026-10-29T23:59:00+01:00"),
                                      tg.cutoff_for(NOW)))

    def test_excludes_single_source_and_same_domain(self):
        self.assertIsNone(tg.eligible(article(source_urls=[
            "https://source.example.org/a", "https://www.source.example.org/b"]),
            tg.cutoff_for(NOW)))

    def test_excludes_thin_reports(self):
        self.assertIsNone(tg.eligible(article(body="Una frase breve"), tg.cutoff_for(NOW)))

    def test_excludes_unreviewed_ai(self):
        self.assertIsNone(tg.eligible(article(editorial_status="ai_assisted_unreviewed"),
                                      tg.cutoff_for(NOW)))

    def test_publisher_image_not_cleared_for_broadcast(self):
        selected = tg.eligible(article(), tg.cutoff_for(NOW))
        self.assertEqual(selected["visual"], "./editorial-images/neutral.svg")
        self.assertNotIn("random-publisher", selected["visual"])

    def test_selects_several_categories_and_deduplicates(self):
        rows = [article(1), article(2), article(3), article(4),
                article(5, category="Italia"), article(6, category="România")]
        selected = tg.select_stories(NOW, rows)
        self.assertEqual(len(selected), 5)
        self.assertLessEqual(sum(x["category"] == "Diaspora" for x in selected), 3)

    def test_missing_key_fails_closed(self):
        with self.assertRaises(RuntimeError):
            tg.request_script([article()], "")

    def test_validation_requires_all_original_ids(self):
        selected = [tg.eligible(article(1), tg.cutoff_for(NOW))]
        prose = "Questa informazione appare nel documento, e viene attribuita alle fonti citate. " * 4
        paragraphs = {s: prose for s in ("fact", "context", "implications", "developments")}
        good = {"language": "it", "stories": [{
            "id": selected[0]["id"], "title_it": "Una notizia", "kicker": "Italia",
            **paragraphs,
        }]}
        self.assertEqual(len(tg.validate_script(good, selected)), 1)
        good["stories"][0]["id"] = "invented-story"
        with self.assertRaises(ValueError):
            tg.validate_script(good, selected)


if __name__ == "__main__":
    unittest.main()
