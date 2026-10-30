#!/usr/bin/env python3
"""Read-only presence check for RDI's existing OpenAI editorial credential.

Never prints, copies, hashes or exports the credential value. This detects
whether a usable credential is already installed locally on Oracle.
"""
import os
from pathlib import Path
import re

KEY = re.compile(r"(?m)^\s*(?:export\s+)?OPENAI_API_KEY\s*=\s*['\"]?\s*(sk-[a-zA-Z0-9_-]{15,}|[a-zA-Z0-9_-]{28,})")
ROOTS=(Path("/home/ubuntu/rdi-geopolitica"), Path("/home/ubuntu/rdi-geopolitica-staging"),
       Path("/home/ubuntu"), Path("/etc/rdi-geopolitica"))
FILES=(".env",".env.local",".env.production","env","openai.env",".bashrc",".profile")
hits=[]
for root in ROOTS:
    for name in FILES:
        p=root/name
        try:
            if not p.is_file() or p.stat().st_size>2_000_000:continue
            data=p.read_text(encoding="utf-8",errors="replace")
            if KEY.search(data):
                hits.append(str(p))
        except (OSError,PermissionError):
            continue
print("ORACLE_ENV_OPENAI_KEY="+str(bool(os.getenv("OPENAI_API_KEY"))).lower())
print("ORACLE_RDI_ENVFILE_OPENAI_KEY="+str(bool(hits)).lower())
print("ORACLE_RDI_KEY_LOCATIONS="+str(len(hits)))
# Never print filenames: they could reveal information about system structure.
