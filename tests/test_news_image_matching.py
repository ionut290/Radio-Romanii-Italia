"""Regression tests for misleading RDI stock-photo assignments."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from news_image_matching import choose_relevant_photo


class PhotoMatchingTests(unittest.TestCase):
    def setUp(self):
        self.lib = {
            "travel": [{"image": "./editorial-images/news-covers/aeroporto.jpg", "description": "Famiglia in un terminal aeroportuale"}],
            "sports": [
                {"image": "./editorial-images/news-covers/volei.jpg", "description": "Partita amatoriale di pallavolo"},
                {"image": "./editorial-images/news-covers/calcio.jpg", "description": "Partita di calcio amatoriale"},
            ],
            "finance": [
                {"image": "./editorial-images/news-covers/bar.jpg", "description": "Titolare di un caffè controlla la gestione"},
                {"image": "./editorial-images/news-covers/economia.jpg", "description": "Economia e bilancio"},
            ],
            "institution": [{"image": "./editorial-images/news-covers/parlamento.jpg", "description": "Aula parlamentare durante una seduta"}],
        }

    def get(self, title, summary=""):
        return choose_relevant_photo({"title": title, "summary": summary}, self.lib, set())

    def test_aviation_accident_no_fake_airport_photo(self):
        self.assertIsNone(self.get("Elicottero italiano cade in Bosnia, quattro militari morti"))

    def test_football_does_not_receive_volleyball_photo(self):
        self.assertEqual(self.get("Serie A Fiorentina-Atalanta, spettacolo e gol")["image"].split("/")[-1], "calcio.jpg")

    def test_pensions_do_not_receive_cafe_photo(self):
        self.assertIsNone(self.get("Riforma pensioni 2027: cosa prevede la Manovra"))

    def test_generic_city_ranking_not_construction(self):
        self.assertIsNone(self.get("Brescia è la città ideale per lavorare e vivere"))

    def test_parliament_matches_parliament(self):
        self.assertEqual(self.get("Parlamento approva il nuovo decreto")["image"].split("/")[-1], "parlamento.jpg")

    def test_respect_reusable_flag(self):
        self.lib["sports"][1]["reusable"] = False
        self.assertIsNone(self.get("Serie A Fiorentina-Atalanta, spettacolo e gol"))

    def test_no_repeat_photo(self):
        used = {"./editorial-images/news-covers/calcio.jpg"}
        self.assertIsNone(choose_relevant_photo({"title": "Serie A Fiorentina-Atalanta"}, self.lib, used))


if __name__ == "__main__":
    unittest.main()
