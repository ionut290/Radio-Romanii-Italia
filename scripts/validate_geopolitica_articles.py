#!/usr/bin/env python3
"""Validate manually authored RDI geopolitical features; no OpenAI API is used."""
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

path=Path("data/geopolitica-articles.json")
doc=json.loads(path.read_text(encoding="utf-8"))
assert doc.get("schema_version")==1 and isinstance(doc.get("items"),dict)
for ident,entry in doc["items"].items():
    assert re.fullmatch(r"geo-[a-z0-9-]{8,80}",ident),ident
    assert entry.get("id")==ident
    assert entry.get("editorial_status") in ("ai_assisted_unreviewed","editorially_reviewed")
    url=entry.get("source_url","")
    assert urlsplit(url).scheme=="https" and urlsplit(url).netloc,ident
    assert entry.get("source_name") and entry.get("source_published")
    for lang in ("it","ro"):
        body=entry[lang]
        assert isinstance(body.get("title"),str) and len(body["title"])>=12
        assert isinstance(body.get("lead"),str) and len(body["lead"])>=35
        sections=body.get("sections")
        assert isinstance(sections,list) and len(sections)>=2
        alltext=[body["lead"]]
        for section in sections:
            assert len(section.get("heading",""))>=3
            assert isinstance(section.get("paragraphs"),list) and section["paragraphs"]
            assert all(isinstance(p,str) and len(p)>=40 for p in section["paragraphs"])
            alltext.extend(section["paragraphs"])
        alltext.append(body.get("conclusion",""))
        assert 200 <= len(" ".join(alltext).split()) <= 4000,(ident,lang)
    img=entry.get("image")
    if img:
        assert re.fullmatch(r"\\./data/geopolitica-images/geo-[a-z0-9-]+\\.png",img)
        assert Path(img[2:]).is_file(),img
print("Articoli RDI bilingui convalidati:",len(doc["items"]))
