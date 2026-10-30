"""Safe and resumable live AzuraCast inventory reconciler tests."""
import importlib.util
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("rdi_music_ingest",ROOT/"rdi_music_ingest.py")
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ImportTests(unittest.TestCase):
 def test_new_and_removed_files_reconcile_only_live_index(self):
  with tempfile.TemporaryDirectory() as temp:
   db=sqlite3.connect(Path(temp)/"a.db")
   f1=[("/music/old.mp3",300000,1.0),("/music/new.mp3",400000,2.0)]
   a=mod.reconcile(db,f1)
   self.assertEqual(a["live_total"],2)
   self.assertEqual(a["newly_visible"],2)
   b=mod.reconcile(db,f1)
   self.assertEqual(b["newly_visible"],0)
   self.assertEqual(b["no_longer_present"],0)
   c=mod.reconcile(db,[("/music/new.mp3",400000,2.0),("/music/new2.mp3",500000,3.0)])
   self.assertEqual(c["no_longer_present"],1)
   self.assertEqual(c["newly_visible"],1)
   rows=db.execute("SELECT path FROM track_live_index ORDER BY path").fetchall()
   self.assertEqual([x[0] for x in rows],["/music/new.mp3","/music/new2.mp3"])
   db.close()

 def test_first_bulk_scan_is_baseline_not_new_uploads(self):
  with tempfile.TemporaryDirectory() as temp:
   db=sqlite3.connect(Path(temp)/"a.db")
   mod.reconcile(db,[("/music/song.mp3",300000,1.0)])
   day=db.execute("SELECT first_seen FROM track_live_index").fetchone()[0]
   self.assertTrue(day.startswith("1970-01-01"))
   db.close()

 def test_empty_volume_does_not_delete_all_songs(self):
  with tempfile.TemporaryDirectory() as temp:
   db=sqlite3.connect(Path(temp)/"a.db")
   mod.reconcile(db,[("/music/song.mp3",300000,1.0)])
   with self.assertRaises(RuntimeError):
    mod.reconcile(db,[])
   self.assertEqual(db.execute("SELECT COUNT(*) FROM track_live_index").fetchone()[0],1)
   db.close()

 def test_modified_audio_invalidates_old_duration(self):
  with tempfile.TemporaryDirectory() as temp:
   db=sqlite3.connect(Path(temp)/"a.db")
   mod.reconcile(db,[("/music/song.mp3",300000,1.0)])
   db.execute("UPDATE track_live_index SET duration_seconds=222")
   db.commit()
   mod.reconcile(db,[("/music/song.mp3",333000,3.0)])
   self.assertIsNone(db.execute("SELECT duration_seconds FROM track_live_index").fetchone()[0])
   db.close()

if __name__=="__main__":
 unittest.main()
