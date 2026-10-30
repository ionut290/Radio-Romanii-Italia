"""Offline YAMNet DJ decision and 100-sample tests; no model download needed."""
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("rdi_music_ai",ROOT/"rdi_music_ai.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class AudioModelPolicyTests(unittest.TestCase):
    def test_clear_urban_and_vocal_hints(self):
        x=m.decisions({"Hip hop music":0.60,"Pop music":0.12,
                       "Singing":0.41,"Music":0.66})
        self.assertEqual(x["genre_ai"],"urban")
        self.assertEqual(x["voice_ai"],"cantato_probabile")
        self.assertEqual(x["model"],m.MODEL_ID)

    def test_clear_instrumental_only_as_probable(self):
        x=m.decisions({"Electronic music":0.49,"Music":0.76,
                       "Singing":0.01,"Vocal music":0.01,"Speech":0.01})
        self.assertEqual(x["genre_ai"],"dance")
        self.assertEqual(x["voice_ai"],"strumentale_probabile")

    def test_ambiguous_scores_refuse_fabricated_genre(self):
        x=m.decisions({"Hip hop music":0.06,"Pop music":0.05,
                       "Singing":0.08,"Music":0.3})
        self.assertEqual(x["genre_ai"],"non_identificato")
        self.assertEqual(x["voice_ai"],"non_verificato")

    def test_no_trap_label_from_audio(self):
        x=m.decisions({"Hip hop music":0.55})
        self.assertNotEqual(x["genre_ai"],"trap")
        self.assertEqual(x["genre_ai"],"urban")

    def test_rapping_suggests_voice(self):
        x=m.decisions({"Rapping":0.6,"Hip hop music":0.7,"Music":0.6})
        self.assertEqual(x["voice_ai"],"cantato_probabile")

    def test_sample_excludes_spots_and_remains_fixed(self):
        with tempfile.TemporaryDirectory() as td:
            db=sqlite3.connect(Path(td)/"t.db")
            db.execute("CREATE TABLE tracks (path TEXT PRIMARY KEY,size INTEGER,modified REAL)")
            for n in range(115):
                db.execute("INSERT INTO tracks VALUES(?,?,?)",(f"/radio/track-{n}.mp3",1,2.0))
            db.execute("INSERT INTO tracks VALUES(?,?,?)",("/radio/spot/not-music.mp3",1,2.0))
            db.execute("INSERT INTO tracks VALUES(?,?,?)",("/radio/RDI Geopolitica/report.mp3",1,2.0))
            db.commit()
            a=m.sample_paths(db,100)
            self.assertEqual(len(a),100)
            self.assertEqual(a,m.sample_paths(db,100))
            self.assertFalse(any("/spot/" in x[0] or "Geopolitica" in x[0] for x in a))
            live={f"/radio/track-{n}.mp3" for n in range(100)}
            matched=m.sample_paths(db,100,live_paths=live)
            self.assertEqual(len(matched),100)
            self.assertTrue(all(x[0] in live for x in matched))
            self.assertEqual(m.sample_paths(db,100,live_paths=set()),[])
            db.close()

if __name__=="__main__":
    unittest.main()
