"""Offline tests for non-destructive GTZAN genre pilot; model stays local."""
import importlib.util
from pathlib import Path
import sys
import unittest
import sqlite3
import tempfile
ROOT=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("rdi_music_genre_ai",ROOT/"rdi_music_genre_ai.py")
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class GenreDecisionTests(unittest.TestCase):
 def test_confident_hop_is_only_broad_urban(self):
  x=g.decide([-9,-9,-9,-9,9,-9,-9,-9,-9,-9])
  self.assertEqual(x["genre"],"urban")
  self.assertEqual(x["candidate"],"hiphop")
  self.assertTrue(x["needs_review"])
 def test_weak_ambiguous_genre_not_assigned(self):
  x=g.decide([0]*10)
  self.assertEqual(x["genre"],"non_identificato")
  self.assertEqual(x["score"],0.1)
 def test_only_known_genres(self):
  self.assertNotIn("trap",g.LABELS)
  self.assertEqual(len(g.LABELS),10)
  self.assertEqual(g.BROAD["disco"],"dance")
 def test_reuse_exact_100_yamnet_song_paths(self):
  with tempfile.TemporaryDirectory() as p:
   db=sqlite3.connect(Path(p)/"test.db")
   db.execute("CREATE TABLE track_ai (path TEXT,size INTEGER,modified REAL,model_id TEXT)")
   for i in range(102):
    db.execute("INSERT INTO track_ai VALUES (?,?,?,?)",(f"/music/track{i}.mp3",1,2,"yamnet-google-v1-audiomagic-f25b741"))
   db.execute("INSERT INTO track_ai VALUES (?,?,?,?)",("/music/not-in-pilot.mp3",1,2,"other-model"))
   db.commit()
   self.assertEqual(len(g.current_samples(db,100)),100)
   self.assertEqual(g.current_samples(db,100)[0][0],"/music/track0.mp3")
   db.close()

if __name__=="__main__":
 unittest.main()
