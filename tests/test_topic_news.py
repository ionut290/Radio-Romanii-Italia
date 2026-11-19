"""Offline regression tests for the bilingual topical RDI news collector."""
import datetime as dt
import email.utils
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from topic_news import TOPIC_SEARCHES, _fetch_topic, collect_topic_news, MAX_PER_TOPIC


class _Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class TopicNewsTests(unittest.TestCase):
    NOW = dt.datetime(2026, 11, 19, 12, 0, tzinfo=dt.timezone.utc)

    def test_user_requested_categories_are_present(self):
        categories = {row[0] for row in TOPIC_SEARCHES}
        self.assertTrue({
            "Muzică", "Cinema și seriale", "Tehnologie",
            "Inteligență artificială", "Educație"
        }.issubset(categories))
        self.assertEqual(len(categories), len(TOPIC_SEARCHES))

    def test_rss_requires_source_https_and_fresh_date(self):
        recent = email.utils.format_datetime(self.NOW - dt.timedelta(hours=1))
        stale = email.utils.format_datetime(self.NOW - dt.timedelta(hours=50))
        xml = f"""<?xml version="1.0"?>
        <rss><channel>
          <item><title>Concert nou - Publicație</title>
          <link>https://news.google.com/rss/articles/1</link>
          <source>Publicație</source><pubDate>{recent}</pubDate></item>
          <item><title>Prea veche</title>
          <link>https://news.google.com/rss/articles/2</link>
          <source>Ziar</source><pubDate>{stale}</pubDate></item>
          <item><title>Fără sursă</title>
          <link>https://news.google.com/rss/articles/3</link>
          <pubDate>{recent}</pubDate></item>
          <item><title>Link nesigur</title>
          <link>http://example.com/article</link>
          <source>Ziar</source><pubDate>{recent}</pubDate></item>
        </channel></rss>"""
        with patch("topic_news.urllib.request.urlopen", return_value=_Response(xml.encode("utf-8"))):
            items = _fetch_topic("Muzică", "concerti when:2d", "it", self.NOW, {})
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "Concert nou")
        self.assertEqual(items[0]["source"], "Publicație")
        self.assertEqual(items[0]["category"], "Muzică")
        self.assertEqual(items[0]["summary"], "")

    def test_collector_balances_languages_and_preserves_seen_links(self):
        def fake_fetch(category, query, lang, now, headers):
            return [
                {"category": category, "title": f"{category} {lang} {i}",
                 "url": f"https://news.google.com/{category}/{lang}/{i}",
                 "source": "Ziar", "published": self.NOW.isoformat(),
                 "summary": "", "image": ""}
                for i in range(3)
            ]
        already_seen = {"https://news.google.com/Muzică/ro/0"}
        with patch("topic_news._fetch_topic", side_effect=fake_fetch):
            items = collect_topic_news(self.NOW, already_seen, {})
        for category, _, _ in TOPIC_SEARCHES:
            group = [article for article in items if article["category"] == category]
            self.assertLessEqual(len(group), MAX_PER_TOPIC)
            self.assertTrue(any("/it/" in article["url"] for article in group))
            self.assertTrue(any("/ro/" in article["url"] for article in group))
        self.assertEqual(len(items), len({item["url"] for item in items}))
        self.assertNotIn("https://news.google.com/Muzică/ro/0", {a["url"] for a in items})


if __name__ == "__main__":
    unittest.main()
