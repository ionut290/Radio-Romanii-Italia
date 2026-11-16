#!/usr/bin/env python3
"""Check the inline JavaScript used by the RDI radio and AI Music players."""
from html.parser import HTMLParser
from pathlib import Path
import subprocess


class InlineScripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.scripts = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "script":
            attributes = dict(attrs)
            self.current = [] if "src" not in attributes else None

    def handle_data(self, data):
        if self.current is not None:
            self.current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.current is not None:
            self.scripts.append("".join(self.current))
            self.current = None


def check_page(path):
    page = Path(path).read_text(encoding="utf-8")
    parser = InlineScripts()
    parser.feed(page)
    if not parser.scripts:
        raise AssertionError(f"{path}: no inline JS found")
    for index, source in enumerate(parser.scripts, 1):
        if not source.strip():
            continue
        result = subprocess.run(
            ["node", "--check"], input=source, capture_output=True, text=True, timeout=20
        )
        if result.returncode:
            raise AssertionError(f"{path}: JS block {index}: {result.stderr}")
    print(f"OK {path}: checked {len(parser.scripts)} inline scripts")
    return page


homepage = check_page("index.html")
spotlight = check_page("spotlight-ai.html")
# Prevent recurrence of the initial-audio temporal dead zone issue.
assert homepage.index("let castConnected=false;") < homepage.index("let castConnected=false;startRadio();") + len("let castConnected=false;")
assert "let castConnected=false;startRadio();" in homepage
assert "radioStartupTimer" in homepage and "scheduleRadioRetry" in homepage
assert "aiScheduleRetry" in spotlight and "aiStartWatchdog" in spotlight
assert "playlistAudio.onended" in spotlight
print("OK: radio/AI Music recovery controls present")
