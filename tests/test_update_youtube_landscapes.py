import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("youtube_landscapes", ROOT / "scripts" / "update_youtube_landscapes.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def commons(asset_id, licence="CC BY-SA 4.0"):
    return {"pageid": asset_id, "title": f"File:Scenic View {asset_id}.jpg", "imageinfo": [{
        "thumburl": f"https://upload.wikimedia.org/wikipedia/commons/thumb/a/a1/Scenic_{asset_id}.jpg/1280px-Scenic_{asset_id}.jpg",
        "extmetadata": {"Artist": {"value": "<a>Ana</a>"}, "LicenseShortName": {"value": licence},
                          "LicenseUrl": {"value": "https://creativecommons.org/licenses/by-sa/4.0/"}},
    }]}


class CommonsItemTests(unittest.TestCase):
    def test_commons_image_carries_credit_and_license(self):
        item = module.commons_item(commons(1234), "Italia", "Rome skyline", "2026-11-07")
        self.assertEqual(item["kind"], "commons")
        self.assertIn("Ana", item["credit"])
        self.assertIn("CC BY-SA", item["credit"])
        self.assertEqual(item["src"], item["poster"])

    def test_rejects_restricted_or_non_commons_sources(self):
        restricted = commons(1234, "CC BY-NC 4.0")
        self.assertIsNone(module.commons_item(restricted, "Italia", "Rome skyline", "2026-11-07"))
        unsafe = commons(1234)
        unsafe["imageinfo"][0]["thumburl"] = "https://example.org/photo.jpg"
        self.assertIsNone(module.commons_item(unsafe, "Italia", "Rome skyline", "2026-11-07"))


if __name__ == "__main__":
    unittest.main()
