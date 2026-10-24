#!/usr/bin/env python3
"""Read-only export of spot titles/durations; never exports audio or credentials."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

roots = [Path('/var/azuracast/stations')]
# Docker normally keeps station files in a named volume on the host.
# Inspect only mounts, never container environment variables or credentials.
containers = subprocess.run(['docker','ps','--format','{{.ID}}'],capture_output=True,text=True,check=True).stdout.split()
for container in containers:
    mounts = subprocess.run(['docker','inspect','--format','{{json .Mounts}}',container],capture_output=True,text=True,check=True)
    for mount in json.loads(mounts.stdout) or []:
        destination = mount.get('Destination','').rstrip('/')
        if destination == '/var/azuracast/stations':
            roots.append(Path(mount['Source']))
        elif destination == '/var/azuracast/stations/radio-romanii-italia':
            roots.append(Path(mount['Source']).parent)
candidates = [base/'radio-romanii-italia'/'media'/'spot' for base in roots]
root = next((candidate for candidate in candidates if candidate.is_dir()),None)
if root is None:
    sys.exit('Spot directory is unavailable in station mounts; existing catalog must be preserved.')
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
