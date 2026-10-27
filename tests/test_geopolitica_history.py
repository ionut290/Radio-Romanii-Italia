"""Persistent rotation of published geopolitical radio editions."""
import importlib.util
import pathlib
import unittest

PATH = pathlib.Path(__file__).resolve().parents[1] / "scripts/record_geopolitica_history.py"
SPEC = importlib.util.spec_from_file_location("rdi_geopolitica_history", PATH)
history = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(history)


class TestHistory(unittest.TestCase):
    def test_record_and_deduplicate(self):
        manifest = {"edition_id": "20261027-1952", "story_signatures": ["abc"],
                    "sources": [{"url": "https://example.org/a"}]}
        saved = history.record(manifest, {})
        saved = history.record(manifest, saved)
        self.assertEqual(len(saved["editions"]), 1)
        self.assertEqual(saved["editions"][0]["source_urls"], ["https://example.org/a"])

    def test_keep_recent_editions(self):
        current = {"editions": [{"edition_id": str(i), "signatures": [str(i)]}
                                for i in range(75)]}
        next_one = history.record({"edition_id": "new", "story_signatures": ["new"], "sources": []}, current)
        self.assertEqual(len(next_one["editions"]), 72)
        self.assertEqual(next_one["editions"][-1]["edition_id"], "new")

    def test_empty_edition_not_recorded(self):
        with self.assertRaises(ValueError):
            history.record({"edition_id": "x", "story_signatures": []}, {})


if __name__ == "__main__":
    unittest.main()
