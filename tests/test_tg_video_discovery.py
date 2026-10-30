"""Discovery finds video URLs in article markup but never claims publication rights."""
import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
S = importlib.util.spec_from_file_location("tg_video_candidates",ROOT/"scripts/discover_tg_article_videos.py")
v=importlib.util.module_from_spec(S)
S.loader.exec_module(v)

class DiscoveryTests(unittest.TestCase):
    def test_og_video_and_json_ld_are_review_only(self):
        html='''<html><meta property="og:video:secure_url" content="https://cdn.editor.it/movie.mp4">
        <script type="application/ld+json">{"@type":"VideoObject","contentUrl":"https://cdn.editor.it/recap.mp4"}</script></html>'''
        links=v.discover_html(html,"https://editor.it/news/story")
        self.assertEqual(len(links),2)
        self.assertIn("https://cdn.editor.it/movie.mp4",links)

    def test_unsafe_link_ignored(self):
        self.assertEqual(v.discover_html('<video src="http://localhost/a.mp4"></video>',"https://news.it/a"),[])

    def test_external_embeds_do_not_become_permission(self):
        old=v.collect
        try:
            v.collect=lambda url:["https://cdn.edizione.it/s1.mp4"]
            record=v.prepare({"candidates":[{"id":"x","source_url":"https://news.it/a",
                   "title_original":"Servizio","source_name":"Editor"}]})
        finally:
            v.collect=old
        self.assertEqual(record["status"],"research_only_no_broadcast_rights")
        self.assertFalse(record["items"][0]["video_candidates"][0]["youtube_live_authorized"])
        self.assertFalse(record["items"][0]["video_candidates"][0]["rights_reviewed"])

if __name__=="__main__":
    unittest.main()
