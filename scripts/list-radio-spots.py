#!/usr/bin/env python3
"""Read-only export of spot titles/durations; never exports audio or credentials."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

root = Path('/var/azuracast/stations/radio-romanii-italia/media/spot')
if not root.is_dir():
    sys.exit('Spot directory is unavailable; existing catalog must be preserved.')
items = []
for path in sorted(root.rglob('*')):
    if not path.is_file() or path.suffix.lower() not in {'.wav','.mp3','.m4a','.flac','.ogg','.aac','.opus'}:
        continue
    result = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration:format_tags=title,artist','-of','json',str(path)],capture_output=True,text=True,timeout=15,check=True)
    audio = json.loads(result.stdout).get('format', {})
    tags = {k.lower(): v for k,v in audio.get('tags', {}).items()}
    items.append({'key':hashlib.sha256(str(path.relative_to(root)).encode()).hexdigest()[:20], 'file_name':path.name, 'title':tags.get('title') or path.stem.replace('_',' '), 'artist':tags.get('artist',''), 'duration':round(float(audio.get('duration',0)),2)})
if not items:
    sys.exit('No audio spots found; existing catalog must be preserved.')
print(json.dumps({'updated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'items':items},ensure_ascii=False,indent=2))
