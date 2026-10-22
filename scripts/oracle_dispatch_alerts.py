#!/usr/bin/env python3
"""Trigger GitHub RDI health alerts using the existing limited Oracle token."""
import pathlib
import urllib.request

root = pathlib.Path("/home/ubuntu/rdi-monitor")
token = (root / "github-token").read_text(encoding="utf-8").strip()
url = "https://api.github.com/repos/ionut290/Radio-Romanii-Italia/actions/workflows/rdi-health-alerts.yml/dispatches"
req = urllib.request.Request(
    url,
    data=b'{"ref":"main"}',
    method="POST",
    headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "RDI-Health-Oracle",
        "X-GitHub-Api-Version": "2022-11-28",
    },
)
with urllib.request.urlopen(req, timeout=20) as response:
    print("Monitor allarmi RDI richiesto:", response.status)
