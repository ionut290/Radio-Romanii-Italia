"""No-network contract tests for dedicated 18:00 RDI TG scheduling."""
from __future__ import annotations
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("deploy_tg_oracle",ROOT/"scripts/deploy-tg-sera-oracle.py")
tg=importlib.util.module_from_spec(spec)
spec.loader.exec_module(tg)
ROME=ZoneInfo("Europe/Rome")
NOW=dt.datetime(2026,10,30,16,42,tzinfo=ROME)

def fixtures(folder:Path):
    edition="20261030"
    filename="RDI-TG-SERA-IT-"+edition+".mp3"
    clips=[{"kind":"jingle","start_seconds":0,"end_seconds":10},
           {"kind":"intro","start_seconds":10,"end_seconds":30}]
    for i in range(4):
        clips.append({"kind":"story","start_seconds":30+i*60,
                     "end_seconds":90+i*60,"title":"Notizia","source_url":"https://a.it/article"})
    clips.extend([{"kind":"outro","start_seconds":270,"end_seconds":289},
                  {"kind":"end-jingle","start_seconds":289,"end_seconds":300}])
    articles=[{"id":str(n),"sources":["https://a.it/story","https://b.it/story"]} for n in range(4)]
    manifest={"schema_version":1,"language":"it","synthetic_voice":"it-IT-ElsaNeural",
        "edition_id":edition,"edition_date":"2026-10-30","cutoff_at":"2026-10-30T16:00:00+01:00",
        "generated_at":"2026-10-30T16:15:00+01:00",
        "track_title":"RDI-TG-SERA-IT-"+edition,"audio_filename":filename,
        "story_count":4,"articles":articles,"audio_duration_seconds":300,"timeline":clips}
    tv={"schema_version":1,"type":"rdi-daily-tg","language":"it",
        "edition_id":edition,"track_title":manifest["track_title"],
        "audio_duration_seconds":300,"timeline":clips}
    mp3=folder/filename; mp3.write_bytes(b"X"*220_000)
    m=folder/"manifest.json";m.write_text(json.dumps(manifest))
    t=folder/"tv-timing.json";t.write_text(json.dumps(tv))
    return m,mp3,t,manifest,tv


class SafeScheduleTests(unittest.TestCase):
    def test_schedule_exists_only_for_edition_date(self):
        s=tg.expected_schedule("2026-10-30")
        self.assertEqual((s["start_time"],s["end_time"]),(1800,1859))
        self.assertEqual(s["start_date"],s["end_date"])
        self.assertEqual(s["days"],[1,2,3,4,5,6,7])
        self.assertTrue(s["loop_once"])
        self.assertTrue(tg.verify_schedule([{**s,"id":99}], "2026-10-30"))
        self.assertFalse(tg.verify_schedule([s],"2026-10-31"))
        self.assertFalse(tg.verify_schedule([{}],"2026-10-30"))

    def test_playlist_is_disabled_during_preparation_and_isolated(self):
        s=tg.plan_for("2026-10-30")
        self.assertFalse(s["is_enabled"])
        self.assertEqual(s["type"],"once_per_hour")
        self.assertIn("interrupt",s["backend_options"])
        self.assertIn("single_track",s["backend_options"])
        self.assertNotIn("Geopolitica",s["name"])
        self.assertEqual(s["play_per_hour_minute"],0)

    def test_complete_manifest_is_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            files=fixtures(Path(temp))
            out,path=tg.validate(*files[:3],now=NOW)
            self.assertEqual(out["story_count"],4)
            self.assertTrue(path.endswith(files[1].name))

    def test_stale_or_late_episode_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            files=fixtures(Path(temp))
            for now in [dt.datetime(2026,10,31,16,35,tzinfo=ROME),
                        dt.datetime(2026,10,30,17,52,tzinfo=ROME),
                        dt.datetime(2026,10,30,15,59,tzinfo=ROME)]:
                with self.assertRaises(ValueError):
                    tg.validate(*files[:3],now=now)

    def test_invalid_timing_never_reaches_azuracast(self):
        with tempfile.TemporaryDirectory() as temp:
            files=fixtures(Path(temp))
            bad=dict(files[4]);bad["timeline"]=bad["timeline"][:-1]
            files[2].write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                tg.validate(*files[:3],now=NOW)

    def test_too_few_stories_never_go_live(self):
        with tempfile.TemporaryDirectory() as temp:
            files=fixtures(Path(temp))
            bad=dict(files[3]);bad["story_count"]=2;bad["articles"]=bad["articles"][:2]
            files[0].write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                tg.validate(*files[:3],now=NOW)

    def test_audio_filename_must_match_exact_broadcast_track(self):
        with tempfile.TemporaryDirectory() as temp:
            files=fixtures(Path(temp))
            bad=dict(files[3]);bad["track_title"]="Other station MP3"
            files[0].write_text(json.dumps(bad))
            with self.assertRaises(ValueError):
                tg.validate(*files[:3],now=NOW)

if __name__=="__main__":
    unittest.main()
