#!/usr/bin/env python3
"""Build 70 editorial photographic WebP thumbnails from openly licensed Wikimedia Commons photographs.
Never use a photo as evidence that it documents the article displayed beside it.
Writes ONLY category WebPs plus photo attribution manifest.
"""
import io,json,re,html,random,time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from PIL import Image,ImageOps,UnidentifiedImageError

ROOT=Path(__file__).resolve().parents[1]/"data/geopolitica-images/categories"
TOPICS={
"conflicte":["humanitarian aid relief camp","war damaged buildings Ukraine","humanitarian aid truck","refugees humanitarian shelter","United Nations peacekeepers","Ukraine damaged bridge","Red Cross humanitarian relief","peace dove","conflict reconstruction","humanitarian supplies"],
"europa":["European Union flag Brussels","European Parliament Strasbourg interior","European Central Bank Frankfurt","European Commission Brussels","European Council Brussels building","European Union border flags","Brussels European quarter","European Parliament plenary","European Union city skyline","European flags international meeting"],
"economie":["container ship port logistics","world stock market trading floor","cargo freight train","financial district skyscrapers","industrial factory production line","shipping containers crane","international financial market","commercial cargo plane","agriculture wheat harvest","banknotes euro money"],
"energie":["oil pumpjack landscape","natural gas pipeline facility","liquefied natural gas tanker","wind turbines renewable energy","solar power photovoltaic field","offshore oil platform","power transmission pylon","hydroelectric dam","hydrogen energy industrial plant","petroleum refinery"],
"securitate":["NATO flags headquarters","military aircraft fighter jet","naval military ship","peacekeeping troops patrol","coast guard helicopter","radar military surveillance","NATO military exercise","security surveillance camera","civil protection emergency response","cybersecurity operations center"],
"tehnologie":["artificial intelligence robot laboratory","satellite earth orbit","data center server racks","semiconductor microchip close up","robotics industrial factory","space telescope observatory","scientist working laboratory","quantum computing cryostat","rocket launch space technology","radio telescope satellite dishes"],
"clima":["drought cracked earth","glacier melting ice","wildfire forest","flooded village climate","hurricane satellite","polar bear arctic ice","coral reef ocean","forest landscape sunlight","coastal erosion waves","seedling hands soil"],
}
USER_AGENT="RadioRomaniiGeopolitica/1.0 (editorial contact: https://radioromanii.duckdns.org)"
API="https://commons.wikimedia.org/w/api.php"
def fetch(url,timeout=25):
  req=Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json,image/*;q=0.8,*/*;q=0.5"})
  with urlopen(req,timeout=timeout) as response:
    return response.read()
def candidate(query):
  params={"action":"query","format":"json","generator":"search","gsrsearch":"filetype:bitmap "+query,
   "gsrnamespace":6,"gsrlimit":20,"prop":"imageinfo","iiprop":"url|size|mime|extmetadata",
   "iiurlwidth":1400,"iiextmetadatafilter":"LicenseShortName|LicenseUrl|Artist|Credit|UsageTerms"}
  data=json.loads(fetch(API+"?"+urlencode(params)))
  rows=[]
  for page in data.get("query",{}).get("pages",{}).values():
    i=(page.get("imageinfo") or [{}])[0]
    if i.get("mime") not in ("image/jpeg","image/png","image/webp"):continue
    if i.get("width",0)<600 or i.get("height",0)<350:continue
    meta=i.get("extmetadata") or {}
    license=meta.get("LicenseShortName",{}).get("value","")
    if not re.search(r"CC[ -]?BY|CC0|Public domain",license,re.I):continue
    url=i.get("thumburl") or i.get("url")
    if not url:continue
    rows.append({"title":page["title"],"url":url,"source":i.get("descriptionurl",""),
     "license":license,"license_url":meta.get("LicenseUrl",{}).get("value",""),
     "artist":re.sub("<[^>]+>"," ",html.unescape(meta.get("Artist",{}).get("value",""))).strip()[:250]})
  return sorted(rows,key=lambda x:x["title"])
def main():
  manifest={}
  used=set()
  for topic,queries in TOPICS.items():
    output=ROOT/topic
    output.mkdir(parents=True,exist_ok=True)
    manifest[topic]=[]
    for index,query in enumerate(queries,1):
      result=None
      search_queries=[query,query.split()[0:2]]
      for search in search_queries:
        try:
          q=" ".join(search) if isinstance(search,list) else search
          options=candidate(q)
          for x in options:
            if x["source"] in used:continue
            try:
              raw=fetch(x["url"])
              with Image.open(io.BytesIO(raw)) as pic:
                if pic.width<600 or pic.height<350:continue
                frame=ImageOps.fit(pic.convert("RGB"),(1200,675),Image.Resampling.LANCZOS,centering=(.5,.5))
                target=output/f"{index:02}.webp"
                frame.save(target,"WEBP",quality=79,method=5)
                if target.stat().st_size>550_000:
                  frame.save(target,"WEBP",quality=67,method=5)
              used.add(x["source"])
              result={"number":index,"search":query,**{k:v for k,v in x.items() if k!="url"}}
              print(topic,index,x["title"],target.stat().st_size,flush=True)
              break
            except Exception as e:
              print("image rejected",type(e).__name__,flush=True)
          if result:break
        except Exception as e:print("search error",topic,index,type(e).__name__,str(e)[:100],flush=True)
        time.sleep(1)
      if not result:
        raise RuntimeError(f"Could not obtain a freely licensed photograph for {topic}/{index:02}; no partial image commit")
      manifest[topic].append(result)
  (ROOT/"PHOTO-CREDITS.json").write_text(json.dumps({"description":"Editorial illustrative photos; photos do not document the specific article next to them.","categories":manifest},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print("Prepared",len(used),"photographs",flush=True)
if __name__=="__main__":main()
