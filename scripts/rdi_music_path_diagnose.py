#!/usr/bin/env python3
"""Read-only identification of Oracle AzuraCast media mount (no song names)."""
import json
import os
import pathlib
import subprocess

p="/var/lib/docker/volumes/azuracast_station_data/_data/radio-romanii-italia/media"
print("OLD_MEDIA_DIRECTORY_EXISTS="+str(os.path.isdir(p)))
for i,cmd in enumerate((
 ["sudo","-n","find",p,"-type","f","-print0"],
 ["sudo","-n","stat","-c","%s","--",p],
 ["sudo","-n","docker","volume","inspect","azuracast_station_data"]
)):
 try:
  r=subprocess.run(cmd,capture_output=True,timeout=16,check=False)
  error=r.stderr.decode("utf-8","replace").lower()
  print(f"CHECK_{i}_CODE="+str(r.returncode))
  print(f"CHECK_{i}_NO_SUCH_FILE="+str("no such file" in error))
  print(f"CHECK_{i}_PERMISSION_DENIED="+str("permission denied" in error or "not allowed" in error))
  print(f"CHECK_{i}_SUDO_ERROR="+str("sudo:" in error))
  if i==0 and r.returncode==0:
   print("ORIGINAL_DIRECTORY_AUDIO_COUNT="+str(r.stdout.count(b"\0")))
  if i==2 and r.returncode==0:
   data=json.loads(r.stdout)
   print("AZURACAST_STATION_DATA_MOUNT="+str(data[0].get("Mountpoint","")))
 except Exception as exc:
  print(f"CHECK_{i}_EXCEPTION="+type(exc).__name__)
