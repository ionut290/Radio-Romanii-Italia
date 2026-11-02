#!/usr/bin/env python3
"""Register one Oriflame advert in the existing RDI spot rotation; never restart radio."""
import base64,hashlib,importlib.util,json,pathlib,re,subprocess,sys,tempfile,time,unicodedata,urllib.request
ROOT=pathlib.Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('rdi_backend',ROOT/'deploy-geopolitica-oracle.py');backend=importlib.util.module_from_spec(spec);spec.loader.exec_module(backend)
VIDEO='https://cdn.creativeclaw.co/u/d1fc9b13/videos/b9240cfe-512d-4d8c-93db-2aaf0a44d9a6.mp4'
SHA='a5e1f13098e515c2cbe139db6ab9a208f9af2541efd7075a54623ebdbc18e01f'
PATH='spot/Spot_Oriflame_Italia_Magda_Niculae.mp3'
def normalize(value):return ''.join(c for c in unicodedata.normalize('NFD',str(value or '').lower()) if not unicodedata.combining(c)).strip()
def memberships(row):return {int(p['id'] if isinstance(p,dict) else p) for p in row.get('playlists',[])}
def main():
 helper=(ROOT/'rdi-geopolitica-auth.php').read_bytes();token=''
 try:
  token=backend.azura_php(helper,'create');client=backend.Client(token)
  playlists=client.call('GET','/station/1/playlists')
  candidates=[p for p in playlists if normalize(p.get('name')) in {'spot','spots','spoturi','publicitate','pubblicita','advertisements'} and p.get('is_enabled') and p.get('source')=='songs']
  if len(candidates)!=1:raise RuntimeError('Expected one enabled existing spot playlist; no scheduling changes made. Candidates='+str([(p.get('id'),p.get('name'),p.get('is_enabled')) for p in playlists if 'spot' in normalize(p.get('name'))]))
  playlist=candidates[0];pid=int(playlist['id']);print('EXISTING_SPOT_PLAYLIST='+str(pid),flush=True)
  rows=client.call('GET','/station/1/files');matching=[r for r in rows if r.get('path')==PATH]
  if not matching:
   other=[r for r in rows if 'oriflame' in normalize(r.get('path'))]
   if other:raise RuntimeError('An Oriflame audio already exists under a different path; refusing duplicate. Paths='+str([r.get('path') for r in other]))
   with tempfile.TemporaryDirectory(prefix='rdi-oriflame-') as folder:
    source=pathlib.Path(folder)/'spot.mp4';audio=pathlib.Path(folder)/'spot.mp3'
    with urllib.request.urlopen(VIDEO,timeout=90) as response:source.write_bytes(response.read(30_000_001))
    if hashlib.sha256(source.read_bytes()).hexdigest()!=SHA:raise RuntimeError('Video identity mismatch')
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(source),'-vn','-c:a','libmp3lame','-b:a','192k','-metadata','title=Spot Oriflame Italia - Magda Niculae','-metadata','artist=RDI',str(audio)],check=True,timeout=90)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(audio)]));duration=float(probe['format']['duration'])
    if not 50<duration<52:raise RuntimeError('Unexpected audio duration')
    client.call('POST','/station/1/files',{'path':PATH,'file':base64.b64encode(audio.read_bytes()).decode()});print('ORIFLAME_AUDIO_UPLOADED=YES',flush=True)
   for attempt in range(10):
    rows=client.call('GET','/station/1/files');matching=[r for r in rows if r.get('path')==PATH]
    if matching:break
    time.sleep(3)
  if len(matching)!=1:raise RuntimeError('Audio index not ready; spot playlist unchanged')
  before=memberships(matching[0]);target=before|{pid}
  if target!=before:
   result=client.call('PUT','/station/1/files/batch',{'do':'playlist','playlists':sorted(target),'files':[PATH],'dirs':[]})
   if isinstance(result,dict) and result.get('errors'):raise RuntimeError('Playlist assignment rejected')
  checked=next(r for r in client.call('GET','/station/1/files') if r.get('path')==PATH)
  if memberships(checked)!=target:raise RuntimeError('Playlist assignment verification failed')
  after=next(p for p in client.call('GET','/station/1/playlists') if int(p['id'])==pid)
  for key in ['type','order','is_enabled','schedule_items','play_per_minutes','play_per_songs','play_per_hour_minute']:
   if playlist.get(key)!=after.get(key):raise RuntimeError('Existing spot schedule changed during deployment')
  print('ORIFLAME_SPOT_IN_EXISTING_ROTATION=YES',flush=True)
  print('ORIFLAME_TRACK_TITLE='+str(checked.get('title') or checked.get('song',{}).get('title') or 'Spot Oriflame Italia - Magda Niculae'),flush=True)
  print('EXISTING_SPOT_SCHEDULE_PRESERVED=YES',flush=True)
 finally:
  if token:backend.azura_php(helper,'revoke',token.split(':',1)[0])
if __name__=='__main__':main()
