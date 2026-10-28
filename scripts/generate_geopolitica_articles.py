#!/usr/bin/env python3
"""Create clearly AI-labelled bilingual RDI analyses only from retrievable source text.

Requires OPENAI_API_KEY as GitHub secret. Optional RDI_ENABLE_AI_IMAGES=1 generates
illustrative images. Never invent event details when the source cannot be read.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen

NEWS=Path("data/geopolitica-news.json")
OUT=Path("data/geopolitica-articles.json")
IMG_DIR=Path("data/geopolitica-images")
API="https://api.openai.com/v1"
MAX_NEW=max(0,min(int(os.getenv("RDI_ARTICLES_PER_RUN","2")),4))
KEY=os.getenv("OPENAI_API_KEY","")
MODEL=os.getenv("RDI_ARTICLE_MODEL","gpt-4.1-mini")
MAX_WORDS=4000

def get_json(url, body=None, headers=None, timeout=45):
    h={"User-Agent":"RDI-Editorial/1.0",**(headers or {})}
    if body is not None: h["Content-Type"]="application/json"
    req=Request(url,data=json.dumps(body).encode() if body is not None else None,headers=h)
    with urlopen(req,timeout=timeout) as resp:return json.loads(resp.read())

def collect_text(url):
    """Best effort extraction of article main text, without RSS snippets as evidence."""
    from bs4 import BeautifulSoup
    from trafilatura import extract
    if not url.startswith("https://"):return ""
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; RDI/1.0)"})
    with urlopen(req,timeout=18) as response:
        final=response.geturl()
        if urlparse(final).scheme!="https":return ""
        raw=response.read(1200000).decode("utf-8","replace")
    article=extract(raw,include_comments=False,include_tables=False,output_format="txt") or ""
    if not article:
        soup=BeautifulSoup(raw,"html.parser")
        for bad in soup(["script","style","nav","footer","header"]):bad.decompose()
        candidate=soup.find("article") or soup.find("main")
        article=candidate.get_text(" ",strip=True) if candidate else ""
    article=re.sub(r"\\s+"," ",article).strip()
    return article[:22000] if len(article)>=1000 else ""

def create_article(item,source_text):
    prompt="""You are the bilingual editorial analyst of Radio Românii din Italia.
Return ONLY a JSON object with fields it and ro. Each is an object with title, lead,
sections (array of {heading, paragraphs: array of paragraph strings}), and conclusion.
Write original, informative, readable, in-depth analysis (target 1100-2200 words per
language if evidence permits, never above 4000 words per language). Use the material
below exclusively as factual evidence for this event; do not invent quotes, casualties,
dates, motives, figures, outcomes, secondary sources or firsthand reporting.
Clearly attribute reported claims; distinguish factual report, context and analysis.
If source is thin, write a shorter piece rather than filling space or repeating text.
No citations beyond the provided source. No markdown, no HTML. Report uncertainty.
Never mention that you visited or verified a source independently. Label it as AI
assisted analysis from a published external article, not original reporting by RDI.
"""
    user=json.dumps({"headline":item["title"],"publisher":item["source"],"published":item["published"],"source_url":item["url"],"retrieved_article_text":source_text},ensure_ascii=False)
    data=get_json(API+"/chat/completions",{"model":MODEL,"response_format":{"type":"json_object"},
        "messages":[{"role":"system","content":prompt},{"role":"user","content":user}],
        "temperature":0.2,"max_completion_tokens":11500},
        {"Authorization":"Bearer "+KEY},timeout=160)
    result=json.loads(data["choices"][0]["message"]["content"])
    if not all(isinstance(result.get(lang),dict) and isinstance(result[lang].get("sections"),list) and result[lang].get("sections") for lang in ("it","ro")):
        raise ValueError("invalid bilingual article")
    for lang in ("it","ro"):
        obj=result[lang]
        text=" ".join(str(p) for s in obj["sections"] for p in s.get("paragraphs",[]))
        words=len(text.split())
        if words<180 or words>MAX_WORDS:raise ValueError(f"article length out of bounds {lang}: {words}")
    return result

def generate_image(item):
    """Optional paid image generation; always labels images as illustrations."""
    import base64
    prompt=("Professional original conceptual geopolitical editorial illustration, not a real "
            "photograph, not documentary evidence. No portraits of identifiable people, "
            "no fake war scenes, no text, no logos, 16:9 landscape with deep blue cinematic "
            "news design. Topic: "+item["category"]+". Related headline: "+item["title"][:180])
    result=get_json(API+"/images/generations",{"model":"gpt-image-1","prompt":prompt,
        "size":"1536x1024","quality":"low","n":1},
        {"Authorization":"Bearer "+KEY},timeout=160)
    encoded=result["data"][0].get("b64_json")
    if not encoded:raise ValueError("missing image bytes")
    IMG_DIR.mkdir(exist_ok=True,parents=True)
    target=IMG_DIR/(item["id"]+".png")
    target.write_bytes(base64.b64decode(encoded))
    return "./"+str(target)

def main():
    if not KEY:
        print("OPENAI_API_KEY missing: no AI articles or paid images generated.")
        return
    news=json.loads(NEWS.read_text(encoding="utf-8")).get("items",[])
    try:db=json.loads(OUT.read_text(encoding="utf-8"))
    except (OSError,ValueError):db={"schema_version":1,"items":{}}
    items=db.setdefault("items",{})
    generated=0
    for item in news:
        if generated>=MAX_NEW:break
        ident=item.get("id")
        if not ident or ident in items or not item.get("title_it") or not item.get("title_ro"):continue
        try:
            source=collect_text(item.get("url",""))
            if not source:
                print("Skip: source article not available",ident)
                continue
            article=create_article(item,source)
            record={"id":ident,"source_url":item["url"],"source_name":item["source"],
                    "source_published":item["published"],"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(),
                    "editorial_status":"ai_assisted_unreviewed","it":article["it"],"ro":article["ro"]}
            if os.getenv("RDI_ENABLE_AI_IMAGES")=="1":
                try:record["image"]=generate_image(item)
                except Exception as exc:print("Image unavailable",ident,type(exc).__name__,str(exc)[:160])
            items[ident]=record
            OUT.parent.mkdir(exist_ok=True,parents=True)
            OUT.write_text(json.dumps(db,ensure_ascii=False,indent=2)+"\\n",encoding="utf-8")
            generated+=1
            print("Generated",ident)
        except Exception as exc:
            print("Article skipped",ident,type(exc).__name__,str(exc)[:250])
        time.sleep(1)
    print("New articles:",generated,"archive:",len(items))

if __name__=="__main__":main()
