#!/usr/bin/env python3
"""RDI health checks: one GitHub issue per unresolved pipeline incident."""
import datetime as dt
import json
import os
import urllib.error
import urllib.parse
import urllib.request

REPO = os.environ["GITHUB_REPOSITORY"]
TOKEN = os.environ["GH_TOKEN"]
API = f"https://api.github.com/repos/{REPO}"
NOW = dt.datetime.now(dt.timezone.utc)
FLOWS = {"news.yml": ("Notizie generali", 75), "editorial.yml": ("Editoriali", 180), "events.yml": ("Eventi", 180), "translate-news.yml": ("Traduzioni", 180)}

def api(path, method="GET", data=None):
    request = urllib.request.Request(
        API + path,
        data=json.dumps(data).encode() if data is not None else None,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "RDI-health",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        raw = response.read()
        return json.loads(raw) if raw else None

def parsed(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

for workflow, (label, maximum) in FLOWS.items():
    try:
        runs = api("/actions/workflows/" + workflow + "/runs?per_page=20")["workflow_runs"]
        successes = [r for r in runs if r.get("conclusion") == "success"]
        last = max((parsed(r["created_at"]) for r in successes), default=None)
        age = int((NOW - last).total_seconds() / 60) if last else None
        recent_failures = [r for r in runs[:3] if r.get("status") == "completed" and r.get("conclusion") in ("failure", "timed_out")]
        active = any(r.get("status") != "completed" and (NOW - parsed(r["created_at"])).total_seconds() < 2400 for r in runs[:5])
        failing = (age is None or age > maximum or len(recent_failures) >= 2) and not active
        title = "[RDI Monitor] " + label + " - problema di pubblicazione"
        q = urllib.parse.urlencode({"state": "all", "per_page": 100})
        issues = api("/issues?" + q)
        matches = [x for x in issues if x.get("title") == title and "pull_request" not in x]
        open_issues = [x for x in matches if x["state"] == "open"]
        details = f"Workflow: {workflow}\\nUltima esecuzione riuscita: {last.isoformat() if last else 'non trovata'}\\nMinuti dall'ultima esecuzione riuscita: {age}\\nEsecuzioni fallite nelle ultime tre: {len(recent_failures)}\\nControllo UTC: {NOW.isoformat()}"
        if failing and not open_issues:
            if matches:
                api("/issues/" + str(matches[0]["number"]), "PATCH", {"state": "open", "body": details})
            else:
                api("/issues", "POST", {"title": title, "body": details})
            print(label + ": ALLARME, issue aperta")
        elif not failing and open_issues:
            for issue in open_issues:
                api("/issues/" + str(issue["number"]) + "/comments", "POST", {"body": "Monitor RDI: esecuzioni nuovamente regolari. Chiusura automatica."})
                api("/issues/" + str(issue["number"]), "PATCH", {"state": "closed"})
            print(label + ": RIPRISTINATO, issue chiusa")
        else:
            print(label + (": ALLARME già segnalato" if failing else ": OK") + f" (ultima riuscita {age} min)")
    except (urllib.error.URLError, ValueError, KeyError, TypeError) as exc:
        print(label + ": errore di monitoraggio: " + str(exc))
        raise
