"""RDI DJ AutoDJ integration: playlist preservation, rollback, safe activation.

No network calls, songs or real AzuraCast changes in tests.
"""
import importlib.util
import sys
from pathlib import Path
from unittest import TestCase, main
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location("rdi_music_azuracast_sync",ROOT/"rdi_music_azuracast_sync.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def rec(pid=77,enabled=False):
 return {"id":pid,"name":m.NAME,"type":"default","source":"songs",
  "order":"shuffle","is_enabled":enabled,"schedule_items":[],"is_jingle":False}

class Client:
 def __init__(self,playlist=True,n=10):
  self.playlist=rec() if playlist else None
  self.files={f"song-{i}.mp3":{"path":f"song-{i}.mp3",
    "id":i+10,"playlists":[{"id":13 if i%2 else 19}]} for i in range(n)}
  self.calls=[]
  self.break_batch=False
 def call(self,method,path,body=None):
  self.calls.append((method,path,body))
  if path=="/station/1/playlists" and method=="GET":
   return [self.playlist] if self.playlist else []
  if path=="/station/1/playlists" and method=="POST":
   assert body["is_enabled"] is False
   self.playlist=rec()
   return self.playlist
  if path=="/station/1/files" and method=="GET":
   return list(self.files.values())
  if path=="/station/1/files/batch" and method=="PUT":
   if self.break_batch: raise RuntimeError("Network failure after batch")
   for song in body["files"]:
    self.files[song]["playlists"]=[{"id":i} for i in body["playlists"]]
   return {"success":True}
  if path=="/station/1/playlist/77" and method=="PUT":
   self.playlist["is_enabled"]=body["is_enabled"]
   return self.playlist
  raise AssertionError((method,path,body))

def fake_plan(client,ours):
 paths=sorted(client.files)
 membership={p:m.ids(v["playlists"]) for p,v in client.files.items()}
 pid=m.validate_ours(ours)
 missing=[p for p in paths if pid not in membership[p]]
 return {"verified_total":len(paths),"api_matching":len(paths),"api_unmatched":0,
         "already_linked":len(paths)-len(missing),"to_link":len(missing),
         "playlist_id":pid,"_target_paths":missing,"_media":client.files,
         "_memberships":membership}

class SyncSafetyTests(TestCase):
 def test_union_never_replaces_existing_music_genres(self):
  client=Client()
  with patch.object(m,"snapshot",return_value=None):
   count=m.apply_batch(client,fake_plan(client,client.playlist),10)
  self.assertEqual(count,10)
  for i in range(10):
   self.assertEqual(m.ids(client.files[f"song-{i}.mp3"]["playlists"]),
                    {77,13 if i%2 else 19})
  self.assertFalse(client.playlist["is_enabled"])
  self.assertEqual(len([x for x in client.calls if x[1]=="/station/1/playlist/77"]),0)

 def test_failed_batch_does_not_enable_or_remove_old_associations(self):
  client=Client()
  client.break_batch=True
  with patch.object(m,"snapshot",return_value=None):
   with self.assertRaises(RuntimeError):
    m.apply_batch(client,fake_plan(client,client.playlist),5)
  self.assertFalse(client.playlist["is_enabled"])
  for i in range(10):
   self.assertEqual(m.ids(client.files[f"song-{i}.mp3"]["playlists"]),
                    {13 if i%2 else 19})

 def test_prepare_only_creates_empty_disabled_playlist(self):
  client=Client(playlist=False)
  m.run(client,"prepare")
  self.assertFalse(client.playlist["is_enabled"])
  self.assertEqual(len([x for x in client.calls if x[0]=="PUT"]),0)

 def test_enable_rejects_incomplete_catalogue(self):
  client=Client(n=430)
  with patch.object(m,"plan",return_value=fake_plan(client,client.playlist)):
   with self.assertRaises(RuntimeError):
    m.run(client,"enable")
  self.assertFalse(client.playlist["is_enabled"])

 def test_enable_only_when_all_verified_songs_are_linked(self):
  client=Client(n=430)
  for item in client.files.values():
   item["playlists"].append({"id":77})
  with patch.object(m,"plan",return_value=fake_plan(client,client.playlist)):
   m.run(client,"enable")
  self.assertTrue(client.playlist["is_enabled"])
  self.assertEqual(len([x for x in client.calls if x[0]=="PUT"]),1)

 def test_do_not_sync_when_playlist_already_live(self):
  client=Client(n=500)
  client.playlist["is_enabled"]=True
  with patch.object(m,"plan",return_value=fake_plan(client,client.playlist)):
   with self.assertRaises(RuntimeError):
    m.run(client,"sync",limit=40)

 def test_ambiguous_playlist_is_refused(self):
  client=Client()
  client.call=lambda method,path,body=None:[rec(),rec()]
  with self.assertRaises(RuntimeError):
   m.find_playlist(client)

 def test_playlist_id_parsing_must_be_unambiguous(self):
  self.assertEqual(m.ids([{"id":13},25]),{13,25})
  with self.assertRaises(ValueError):m.ids(None)
  with self.assertRaises(ValueError):m.ids([{"id":None}])

if __name__=="__main__":
 main()
