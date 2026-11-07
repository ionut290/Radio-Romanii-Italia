import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("youtube_landscapes", ROOT / "scripts" / "update_youtube_landscapes.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def photo(asset_id):
    return {"id": asset_id, "url": f"https://www.pexels.com/photo/scenic-view-{asset_id}/", "photographer": "Ana",
            "src": {"landscape": f"https://images.pexels.com/photos/{asset_id}/pexels-photo-{asset_id}.jpeg"}}


def video(asset_id):
    return {"id": asset_id, "url": f"https://www.pexels.com/video/scenic-video-{asset_id}/", "user": {"name": "Mihai"},
            "video_files": [{"file_type": "video/mp4", "width": 1920, "height": 1080,
                             "link": f"https://videos.pexels.com/video-files/{asset_id}/clip-{asset_id}.mp4"}],
            "video_pictures": [{"picture": f"https://images.pexels.com/videos/{asset_id}/clip-{asset_id}.jpeg"}]}


class PexelsItemTests(unittest.TestCase):
    def test_photo_carries_credit_and_safe_source(self):
        item = module.photo_item(photo(1234), "Italia", "Rome Italy skyline", "2026-11-07")
        self.assertEqual(item["kind"], "photo")
        self.assertEqual(item["credit"], "Ana / Pexels")
        self.assertEqual(item["src"], item["poster"])

    def test_video_prefers_16_by_9_mp4(self):
        item = module.video_item(video(5678), "România", "Bucharest Romania", "2026-11-07")
        self.assertEqual(item["kind"], "video")
        self.assertIn("videos.pexels.com/video-files/5678", item["src"])

    def test_rejects_non_pexels_sources(self):
        unsafe = photo(1234)
        unsafe["src"]["landscape"] = "https://example.org/photo.jpg"
        self.assertIsNone(module.photo_item(unsafe, "Italia", "Rome Italy", "2026-11-07"))


if __name__ == "__main__":
    unittest.main()
