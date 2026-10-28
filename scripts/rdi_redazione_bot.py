#!/usr/bin/env python3
"""RDI editorial control: read-only checks, safe for hourly unattended runs."""
import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]

def check(name, ok, detail):
    return {"name": name, "ok": bool(ok), "detail": str(detail)[:300]}

def run():
    checks = []
    for filename in ("data/war-zone-news.json", "data/geopolitica-news.json", "data/geopolitica-articles.json"):
        path = ROOT / filename
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            checks.append(check(filename, isinstance(data, (dict, list)), "JSON valido"))
        except (OSError, ValueError) as exc:
            checks.append(check(filename, False, type(exc).__name__))
    try:
        from zoneinfo import ZoneInfo
        sys.path.insert(0, str(ROOT / "scripts"))
        from build_geopolitica_bulletin import available_items, read_json
        now = dt.datetime.now(ZoneInfo("Europe/Rome"))
        available = available_items(now, "it", read_json(ROOT / "data/war-zone-news.json"),
                                    read_json(ROOT / "data/geopolitica-radio-verified.json"))
        checks.append(check("radio_editorial_supply", bool(available),
                            f"{len(available)} notizie verificate recenti disponibili (senza storico Oracle)"))
    except Exception as exc:
        checks.append(check("radio_editorial_supply", False, type(exc).__name__))
    return {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "checks": checks, "healthy": all(c["ok"] for c in checks)}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = run()
    payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        path = pathlib.Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(payload, encoding="utf-8")
    print(payload)
    sys.exit(0 if result["healthy"] else 1)
