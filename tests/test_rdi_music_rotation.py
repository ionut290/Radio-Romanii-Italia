"""Offline acceptance checks: 24h simulator must never modify AzuraCast."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("rdi_music_rotation",ROOT/"rdi_music_rotation.py")
rot=importlib.util.module_from_spec(spec)
spec.loader.exec_module(rot)

def track(n,energy="media",title=None,src="ast_gtzan_ai_stima"):
    return {
      "id":f"{n:016x}",
      "title":title or f"StudioSong_{n:08d}",
      "artist":f"Artista {n%180}",
      "energy_estimate":energy,"bpm_candidate":100.0,
      "beat_confidence":0.66,"lufs":-15.0,
      "genre":"dance","genre_source":src,
      "voice":"non_verificato", "ready_for_autodj":False
    }

def album(count=1050):
    energies=("tranquilla","media","ritmata")
    return {"read_only":True,"playlist_writes":0,
            "tracks":[track(i,energy=energies[i%3]) for i in range(count)]}

class RotationSafetyTests(unittest.TestCase):
    def test_24_hour_blocks_no_time_gap_and_no_track_repetition(self):
        p=rot.simulate(album(),"2026-10-30")
        self.assertEqual(p["kind"],"rdi-dj-dry-run")
        self.assertTrue(p["covers_all_24h_in_blocks"])
        self.assertEqual(p["blocks"][0]["dalle"],"00:00")
        self.assertEqual(p["blocks"][-1]["alle"],"24:00")
        self.assertEqual(p["duplicate_tracks"],0)
        self.assertEqual(p["duplicate_titles"],0)
        ids=[x["id"] for block in p["blocks"] for x in block["brani"]]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertFalse(p["automatic_broadcast_enabled"])
        self.assertFalse(p["ready_for_live"])
        self.assertEqual(p["playlist_writes"],0)
        self.assertTrue(p["full_draft"])

    def test_same_music_day_is_reproducible(self):
        x=album()
        a=rot.simulate(x,"2026-10-30")
        b=rot.simulate(x,"2026-10-30")
        self.assertEqual(a,b)
        c=rot.simulate(x,"2026-10-31")
        self.assertNotEqual(a["blocks"][0]["brani"][0]["id"],
                            c["blocks"][0]["brani"][0]["id"])

    def test_excludes_news_spots_and_uncertain_bpm(self):
        items=[
            track(1,title="RDI Geopolitica - la giornata"),
            track(2,title="Spot promozionale"),
            track(3,title="Una canzone normale"),
            track(4,title="Brano senza ritmo"),
        ]
        items[3]["beat_confidence"]=.10
        plan=rot.simulate({"read_only":True,"playlist_writes":0,"tracks":items})
        self.assertEqual(plan["available_analyzed_tracks"],1)
        self.assertEqual(plan["missing_tracks_estimated"]>0,True)
        self.assertFalse(plan["full_draft"])
        self.assertEqual(plan["total_unique_tracks"],1)

    def test_ai_genre_is_not_considered_verified(self):
        p=rot.simulate({"read_only":True,"playlist_writes":0,"tracks":[track(1)]})
        title=p["blocks"][0]["brani"][0]
        self.assertEqual(title["genre_verificato"],"sconosciuto")
        self.assertFalse(title["approvato"])

    def test_only_metadata_genre_can_be_used_as_verified(self):
        t=track(1,src="metadati_file")
        p=rot.simulate({"read_only":True,"playlist_writes":0,"tracks":[t]})
        self.assertEqual(p["blocks"][0]["brani"][0]["genre_verificato"],"dance")

    def test_duplicate_export_suffix_is_not_replayed(self):
        t1=track(1,title="midnight magnet_168870015074305")
        t2=track(2,title="midnight magnet_168870015074306")
        p=rot.simulate({"read_only":True,"playlist_writes":0,"tracks":[t1,t2]})
        self.assertEqual(p["total_unique_tracks"],1)
        self.assertEqual(p["duplicate_titles"],0)

    def test_live_catalogue_is_never_trusted(self):
        for data in ({"read_only":False,"playlist_writes":0,"tracks":[]},
                     {"read_only":True,"playlist_writes":1,"tracks":[]},
                     {"read_only":True,"playlist_writes":0}):
            with self.assertRaises(ValueError):
                rot.simulate(data)

    def test_protected_radio_content_never_inserted(self):
        t=track(44,title="Radio jingle di apertura")
        p=rot.simulate({"read_only":True,"playlist_writes":0,"tracks":[t]})
        self.assertEqual(p["total_unique_tracks"],0)
        self.assertIn("AzuraCast",p["reason"])
        self.assertTrue(any("TG" in s for s in p["protected_programmes"]))

if __name__=="__main__":
    unittest.main()
