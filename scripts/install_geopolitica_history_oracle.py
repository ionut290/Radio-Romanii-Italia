#!/usr/bin/env python3
"""Safely connect persistent broadcast history to the existing Oracle hourly job.

Run as root on the Oracle host after pulling this repository. Does not start,
stop or modify the timer, AzuraCast, or the radio.
"""
from __future__ import annotations

import pathlib
import shutil
import subprocess
import sys

SCRIPT = pathlib.Path("/usr/local/bin/rdi-geopolitica-hourly.sh")
STATE = pathlib.Path("/var/lib/rdi-geopolitica")
MARKER = 'scripts/record_geopolitica_history.py --manifest "$WORKDIR/manifest.json"'
NEEDLE = '        --php-helper scripts/rdi-geopolitica-auth.php\n  else'
INSERT = (
    '        --php-helper scripts/rdi-geopolitica-auth.php\n'
    '\n'
    '      # Persist history only after successful upload to AzuraCast.\n'
    '      "$PYTHON" scripts/record_geopolitica_history.py --manifest "$WORKDIR/manifest.json"\n'
    '  else'
)


def patch(text: str) -> str:
    if MARKER in text:
        return text
    if text.count(NEEDLE) != 1:
        raise ValueError("Oracle script differs from the expected version; no changes made")
    return text.replace(NEEDLE, INSERT, 1)


def main() -> int:
    if not SCRIPT.is_file():
        print(f"Missing hourly script: {SCRIPT}", file=sys.stderr)
        return 1
    original = SCRIPT.read_text(encoding="utf-8")
    try:
        modified = patch(original)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if modified != original:
        backup = SCRIPT.with_name(SCRIPT.name + ".before-history")
        if not backup.exists():
            shutil.copy2(SCRIPT, backup)
        SCRIPT.write_text(modified, encoding="utf-8")
        check = subprocess.run(["bash", "-n", str(SCRIPT)], check=False)
        if check.returncode:
            SCRIPT.write_text(original, encoding="utf-8")
            print("Bash syntax check failed; restored original script", file=sys.stderr)
            return check.returncode
    STATE.mkdir(parents=True, exist_ok=True)
    STATE.chmod(0o750)
    print("RDI_HISTORY_ORACLE=CONFIGURED")
    print("History will be recorded only after a successful AzuraCast publication.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
