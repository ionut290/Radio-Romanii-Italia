#!/usr/bin/env python3
"""Record only successfully published radio editions on the Oracle host."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
import tempfile
from pathlib import Path

DEFAULT_HISTORY = Path(os.environ.get("RDI_GEOPOLITICA_HISTORY", "/var/lib/rdi-geopolitica/broadcast-history.json"))
KEEP = 72


def record(manifest: dict, current: dict) -> dict:
    signatures = manifest.get("story_signatures", [])
    if not isinstance(signatures, list) or not all(isinstance(x, str) for x in signatures):
        raise ValueError("Invalid story signatures")
    if not signatures:
        raise ValueError("Empty edition must not be recorded")
    entries = current.get("editions", []) if isinstance(current, dict) else []
    entries = [x for x in entries if isinstance(x, dict) and x.get("edition_id") != manifest["edition_id"]]
    entries.append({
        "edition_id": manifest["edition_id"],
        "recorded_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "signatures": signatures,
        "source_urls": [item["url"] for item in manifest.get("sources", [])],
    })
    return {"schema_version": 1, "editions": entries[-KEEP:]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--history", default=str(DEFAULT_HISTORY))
    args = parser.parse_args()
    target = Path(args.history)
    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    current = json.loads(target.read_text(encoding="utf-8")) if target.is_file() else {}
    result = record(manifest, current)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".history-", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(result, out, ensure_ascii=False, indent=2)
            out.write("\n")
        os.replace(name, target)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    print(f"RDI_HISTORY_RECORDED={manifest['edition_id']}")


if __name__ == "__main__":
    main()
