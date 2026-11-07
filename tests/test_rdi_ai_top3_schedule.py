"""Regression for four AzuraCast daily Top3 windows."""
import importlib.util
import pathlib
import unittest
file=pathlib.Path(__file__).resolve().parents[1]/"scripts"/"deploy-rdi-ai-top3-oracle.py"
spec=importlib.util.spec_from_file_location("rdi_top3",file)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class ScheduleTests(unittest.TestCase):
    def test_four_slots(self):
        day="2026-11-08"
        slots=mod.schedule(day)
        self.assertEqual([(s["start_time"],s["end_time"]) for s in slots],
                         [(930,1010),(1330,1410),(1730,1810),(2030,2110)])
        self.assertTrue(mod.valid_schedule(slots,day))
    def test_reject_missing_extra_or_wrong_day(self):
        day="2026-11-08"
        slots=mod.schedule(day)
        self.assertFalse(mod.valid_schedule(slots[:3],day))
        self.assertFalse(mod.valid_schedule(slots+[slots[0]],day))
        self.assertFalse(mod.valid_schedule(slots,"2026-11-09"))
        altered=[dict(x) for x in slots];altered[1]["loop_once"]=False
        self.assertFalse(mod.valid_schedule(altered,day))
if __name__=="__main__":unittest.main()
