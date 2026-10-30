"""Offline tests for the safe RDI DJ suggestions; no AzuraCast account needed."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

SCRIPTS=Path(__file__).resolve().parents[1]/"scripts"
spec=importlib.util.spec_from_file_location("rdi_music_dj",SCRIPTS/"rdi_music_dj.py")
dj=importlib.util.module_from_spec(spec);spec.loader.exec_module(dj)

class ReadOnlyDJTests(unittest.TestCase):
    def test_genre_not_invented_from_bpm(self):
        item=dj.classify("", "Unknown song", 120,0.7,-12,8)
        self.assertEqual(item["genre"],"non_identificato")
        self.assertEqual(item["voice"],"non_verificato")
        self.assertEqual(item["energy_estimate"],"ritmata")
        self.assertEqual(item["suggested_slots"],["giorno_10_13","pomeriggio_13_17"])
        self.assertTrue(item["needs_review"])

    def test_explicit_instrumental_and_genre(self):
        item=dj.classify("Afrobeat", "Morning instrumental", 111,0.8,-14,8)
        self.assertEqual(item["genre"],"dance")
        self.assertEqual(item["voice"],"strumentale_dichiarato")

    def test_unknown_rhythm_not_programmed(self):
        item=dj.classify("Rock", "Guitar", 125,0.1,-9,8)
        self.assertEqual(item["genre"],"rock")
        self.assertIsNone(item["bpm_candidate"])
        self.assertFalse(item["suggested_slots"])

    def test_protected_broadcasts_excluded(self):
        self.assertTrue(dj.excluded("/x/RDI Geopolitica/news.mp3"))
        self.assertTrue(dj.excluded("/x/spot/advert.mp3"))
        self.assertTrue(dj.excluded("/x/TG della Sera/edizione.mp3"))
        self.assertFalse(dj.excluded("/x/Musika/Oltre-i-palazzi.mp3"))

    def test_report_makes_no_writes_to_playlist(self):
        with tempfile.TemporaryDirectory() as tmp:
            old=dj.DB
            dj.DB=Path(tmp)/"music.db"
            db=sqlite3.connect(dj.DB)
            db.execute("CREATE TABLE tracks (path TEXT PRIMARY KEY,size INTEGER,modified REAL,rms REAL,peak REAL,category TEXT,analyzed_at TEXT)")
            db.execute("INSERT INTO tracks VALUES(?,?,?,?,?,?,?)",("/music/Urban Test.mp3",1,2,-9,-1,"?", "2026-10-30"))
            db.execute("INSERT INTO tracks VALUES(?,?,?,?,?,?,?)",("/music/RDI Geopolitica/News.mp3",1,2,-9,-1,"?","2026-10-30"))
            db.commit();db.close()
            try:
                result=dj.report()
                self.assertEqual(result["total_inventoried"],2)
                self.assertEqual(result["total_music"],1)
                self.assertEqual(result["playlist_writes"],0)
                self.assertTrue(result["read_only"])
                self.assertFalse(result["tracks"][0]["ready_for_autodj"])
                self.assertNotIn("/music/",json.dumps(result))
            finally:
                dj.DB=old

if __name__=="__main__":unittest.main()
