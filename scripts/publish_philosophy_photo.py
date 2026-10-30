#!/usr/bin/env python3
"""Switch RDI daily photo only after checking that the new original file exists."""
import datetime,json,pathlib,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
DATE=(sys.argv[1] if len(sys.argv)>1 else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"))
image=ROOT/"calendario-filosofico"/DATE[:4]/(DATE+".jpg")
if not image.is_file() or image.stat().st_size<10000:raise SystemExit("Photo missing or suspiciously small; pointer untouched")
source=ROOT/"data"/"calendario-filosofico-2026.json"
archive=json.loads(source.read_text())
item=next((x for x in archive["days"] if x["date"]==DATE),None)
if not item:raise SystemExit("No approved quote for "+DATE)
current={"date":DATE,"quote":item["quote"],"image":"/"+image.relative_to(ROOT).as_posix(),"image_source":"Originale RDI: generazione IA da zero","status":"verified_file_in_repository"}
pointer=ROOT/"data"/"calendario-filosofico-oggi.json"
pointer.write_text(json.dumps(current,ensure_ascii=False,indent=2)+"\n")
print("Updated pointer for",DATE,"image",current["image"])
