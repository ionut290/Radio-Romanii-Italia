"""24h shadow rotation: all validated media joins bank; different day => different order."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(ROOT))
s=importlib.util.spec_from_file_location("rdi_music_rotation",ROOT/"rdi_music_rotation.py")
rot=importlib.util.module_from_spec(s);s.loader.exec_module(rot)

def track(n,energy="media",title=None):
 return {"id":f"{n:016x}","title":title or f"StudioSong {n}",
    "artist":f"Artista {n%180}","energy_estimate":energy,
    "bpm_candidate":100,"beat_confidence":.66,"lufs":-15,
    "duration_seconds":210,"genre_source":"ast_gtzan_ai_stima",
    "genre":"dance","newly_added":n>400}

def catalog(count=414):
 return {"read_only":True,"playlist_writes":0,"live_index_verified":True,
    "tracks":[track(i,("tranquilla","media","ritmata")[i%3]) for i in range(count)]}

class RotationTests(unittest.TestCase):
 def test_all_414_join_rotation_pool_even_if_not_on_today(self):
  p=rot.simulate(catalog(414),"2026-10-30")
  self.assertEqual(p["pool_tracks_total"],414)
  self.assertEqual(len(p["pool_tracks"]),414)
  self.assertEqual(p["new_tracks_in_pool"],13)
  self.assertEqual(p["total_unique_tracks"]+p["pool_excluded_from_today"],414)
  self.assertEqual(p["duplicate_tracks"],0)
  self.assertFalse(p["ready_for_live"])
  self.assertFalse(p["automatic_broadcast_enabled"])
  self.assertEqual(p["playlist_writes"],0)
  self.assertTrue(p["covers_all_24h_in_blocks"])

 def test_order_changes_each_day_and_unused_songs_reenter(self):
  x=catalog(550)
  a=rot.simulate(x,"2026-10-30")
  b=rot.simulate(x,"2026-10-31")
  self.assertNotEqual(a["blocks"][0]["brani"][0]["id"],
                      b["blocks"][0]["brani"][0]["id"])
  self.assertEqual(a,rot.simulate(x,"2026-10-30"))
  self.assertEqual(a["pool_tracks_total"],550)
  self.assertEqual(b["pool_tracks_total"],550)
  # The bank remains complete regardless of today's available airtime.
  self.assertEqual(len(a["pool_tracks"]),550)
  ids_a={t["id"] for block in a["blocks"] for t in block["brani"]}
  ids_b={t["id"] for block in b["blocks"] for t in block["brani"]}
  self.assertGreater(len(ids_b-ids_a),0)

 def test_invalid_stale_audio_never_enters_bank(self):
  x=catalog(10)
  x["tracks"][1]["duration_seconds"]=None
  x["tracks"][2]["beat_confidence"]=0.1
  x["tracks"][3]["title"]="RDI Geopolitica notiziario"
  p=rot.simulate(x)
  self.assertEqual(p["pool_tracks_total"],8)
  self.assertEqual(p["pool_waiting_for_analysis"],1)
  self.assertEqual(p["pool_audio_profiled"],7)
  self.assertEqual(p["total_unique_tracks"],8)

 def test_live_index_is_mandatory(self):
  x=catalog(10);x["live_index_verified"]=False
  p=rot.simulate(x)
  self.assertEqual(p["pool_tracks_total"],0)
  self.assertFalse(p["full_draft"])

 def test_song_pending_audio_is_already_in_complete_bank(self):
  x=catalog(414)
  x["tracks"][100]["beat_confidence"]=0.10
  p=rot.simulate(x,"2026-10-30")
  self.assertEqual(p["pool_tracks_total"],414)
  self.assertEqual(p["pool_waiting_for_analysis"],1)
  self.assertEqual(p["pool_ready_for_rotation"],414)
  self.assertEqual(p["pool_audio_profiled"],413)
  self.assertFalse(next(t for t in p["pool_tracks"] if t["id"]==x["tracks"][100]["id"])["analisi_audio_completa"])

 def test_new_music_auto_joins_when_indexed_and_analyzed(self):
  c=catalog(10)
  c["tracks"].append(track(99))
  p=rot.simulate(c)
  self.assertEqual(p["pool_tracks_total"],11)
  self.assertEqual(p["total_unique_tracks"],11)

 def test_repeated_export_title_is_not_duplicated(self):
  a=track(1,title="same song_168870015074305")
  b=track(2,title="same song_168870015074306")
  p=rot.simulate({"read_only":True,"playlist_writes":0,
     "live_index_verified":True,"tracks":[a,b]})
  # Two recordings may legitimately share a title; keep both.
  self.assertEqual(p["pool_tracks_total"],2)
  self.assertEqual(p["total_unique_tracks"],2)
  self.assertEqual(p["duplicate_tracks"],0)

 def test_romanian_chinese_and_non_latin_song_titles_are_supported(self):
  c=catalog(3)
  c["tracks"][0]["title"]="Cântec fără sfârșit"
  c["tracks"][1]["title"]="世界之光"
  c["tracks"][2]["title"]="Письмо любви"
  plan=rot.simulate(c,"2026-10-30")
  self.assertEqual(plan["pool_tracks_total"],3)
  self.assertEqual(plan["total_unique_tracks"],3)
  self.assertEqual(rot._title_key("世界之光"),"世界之光")
  self.assertEqual(rot._title_key("Cântec fără sfârșit"),"cântec fără sfârșit")

 def test_only_verified_metadata_genre_is_reported(self):
  x=catalog(1)
  p=rot.simulate(x)
  self.assertEqual(p["blocks"][0]["brani"][0]["genere_verificato"],"sconosciuto")
  x["tracks"][0]["genre_source"]="metadati_file"
  p=rot.simulate(x)
  self.assertEqual(p["blocks"][0]["brani"][0]["genere_verificato"],"dance")

 def test_no_station_access_granted(self):
  for a in ({"read_only":False,"playlist_writes":0,"tracks":[]},
            {"read_only":True,"playlist_writes":1,"tracks":[]}):
   with self.assertRaises(ValueError):
    rot.simulate(a)
  self.assertTrue(any("TG" in x for x in rot.PROTECTED))
  with self.assertRaises(ValueError):
   rot.simulate({"read_only":True,"playlist_writes":0})

if __name__=="__main__":
 unittest.main()
