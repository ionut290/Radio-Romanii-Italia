#!/usr/bin/env python3
"""Install 15-minute systemd sync for existing RDI hourly playlists.

Does not change any AzuraCast playlist setting or restart broadcasting.
Run on Oracle with sudo after hourly_sync.py has passed a complete audit.
"""
from pathlib import Path
import subprocess
import sys
SERVICE=Path("/etc/systemd/system/rdi-autodj-hourly-sync.service")
TIMER=Path("/etc/systemd/system/rdi-autodj-hourly-sync.timer")
SCRIPT=Path("/opt/rdi-music-dj/rdi_autodj_hourly_sync.py")
HELPER=Path("/opt/rdi-music-dj/rdi-geopolitica-auth.php")
LOCK="/run/lock/rdi-dj-sync.lock"

def main():
    if not SCRIPT.is_file() or not HELPER.is_file():
        raise RuntimeError("RDI synchronization program/helper missing")
    subprocess.run([sys.executable,"-m","py_compile",str(SCRIPT)],check=True)
    # Dry run before installing. Fail closed if schedules, playlists,
    # local music inventory, or API availability fail the checks.
    subprocess.run(["flock","-w","120",LOCK,sys.executable,"-u",str(SCRIPT),
                    "--php-helper",str(HELPER)],check=True,timeout=240)
    if SERVICE.exists() or TIMER.exists():
        raise RuntimeError("Service/timer already exist: inspect manually before replacing")
    SERVICE.write_text("""[Unit]
Description=RDI AutoDJ hourly playlist synchronization (adds missing music only)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/bin/flock -w 180 /run/lock/rdi-dj-sync.lock /usr/bin/python3 -u /opt/rdi-music-dj/rdi_autodj_hourly_sync.py --apply --limit 150 --php-helper /opt/rdi-music-dj/rdi-geopolitica-auth.php
TimeoutStartSec=900
NoNewPrivileges=true
ProtectSystem=full
PrivateTmp=true
""")
    TIMER.write_text("""[Unit]
Description=RDI AutoDJ hourly playlist sync every 15 minutes

[Timer]
OnCalendar=*:03,18,33,48
Persistent=true
RandomizedDelaySec=90
Unit=rdi-autodj-hourly-sync.service

[Install]
WantedBy=timers.target
""")
    SERVICE.chmod(0o644)
    TIMER.chmod(0o644)
    subprocess.run(["systemctl","daemon-reload"],check=True)
    subprocess.run(["systemctl","enable","--now",TIMER.name],check=True)
    subprocess.run(["systemctl","is-enabled",TIMER.name],check=True)
    subprocess.run(["systemctl","is-active",TIMER.name],check=True)
    subprocess.run(["systemctl","list-timers","--all",TIMER.name],check=True)
    print("RDI_HOURLY_15MIN_TIMER_ENABLED=true",flush=True)
if __name__=="__main__":main()
