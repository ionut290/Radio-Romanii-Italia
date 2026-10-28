#!/usr/bin/env python3
"""RDI: deterministically build ten lightweight editorial WebP covers per topic.
Graphics are symbolic illustrations, not photographs of reported events.
Only writes to data/geopolitica-images/categories/<topic>/.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, random

BASE = Path(__file__).resolve().parents[1] / "data/geopolitica-images/categories"
W, H = 1200, 675
TOPICS = {
 "conflicte": ("CONFLITTI & PACE", (28, 42, 64), (207, 116, 71), "peace"),
 "europa": ("UE & EUROPA", (19, 51, 103), (91, 161, 225), "europe"),
 "economie": ("ECONOMIA GLOBALE", (21, 54, 60), (73, 190, 158), "economy"),
 "energie": ("ENERGIA & RISORSE", (56, 49, 38), (237, 165, 72), "energy"),
 "securitate": ("SICUREZZA", (34, 43, 70), (128, 153, 201), "security"),
 "tehnologie": ("TECNOLOGIA", (29, 37, 74), (129, 103, 226), "technology"),
 "clima": ("CLIMA & AMBIENTE", (24, 71, 62), (91, 192, 146), "climate"),
}
def mix(a,b,t): return tuple(int(a[i]*(1-t)+b[i]*t) for i in range(3))
def font(size):
 for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"]:
  if Path(f).exists(): return ImageFont.truetype(f,size)
 return ImageFont.load_default()
def image_for(topic, index, entry):
 title, dark, accent, icon = entry
 rng = random.Random(topic + str(index))
 base = Image.new("RGB",(W,H)); p=base.load()
 for y in range(H):
  for x in range(W):
   t = min(1,max(0,0.13 + .65*x/W + .22*y/H))
   noise = rng.randrange(-7,8)
   a=mix(dark,accent,t)
   p[x,y]=tuple(max(0,min(255,v+noise)) for v in a)
 d=ImageDraw.Draw(base,"RGBA")
 for i in range(16):
  x=rng.randrange(-120,W+120); y=rng.randrange(-150,H+150)
  r=rng.randrange(70,280)
  d.ellipse((x-r,y-r,x+r,y+r),outline=(255,255,255,rng.randrange(14,40)),width=rng.randrange(1,5))
 for i in range(12):
  y=rng.randrange(70,H-30)
  pts=[]
  for x in range(-30,W+50,20):
   pts.append((x,y+30*math.sin(x/115 + index*.53+i*.31)))
  d.line(pts,fill=(255,255,255,18),width=2)
 cx,cy=820+rng.randint(-55,55),310+rng.randint(-45,45)
 white=(245,251,255,225); pale=(248,252,255,110)
 if icon=="peace":
  d.ellipse((cx-155,cy-155,cx+155,cy+155),outline=white,width=15)
  d.line((cx,cy-149,cx,cy+150),fill=white,width=14)
  d.line((cx,cy+25,cx-113,cy+112),fill=white,width=14)
  d.line((cx,cy+25,cx+113,cy+112),fill=white,width=14)
 elif icon=="europe":
  for k in range(12):
   a=2*math.pi*k/12-index*.07
   x=cx+128*math.cos(a);y=cy+128*math.sin(a)
   d.ellipse((x-14,y-14,x+14,y+14),fill=white)
  d.ellipse((cx-78,cy-78,cx+78,cy+78),outline=pale,width=7)
 elif icon=="economy":
  bars=[rng.randrange(80,230) for _ in range(6)]
  for k,h in enumerate(bars):
   x=cx-183+k*70
   d.rounded_rectangle((x,cy+158-h,x+46,cy+158),radius=9,fill=(255,255,255,75+k*16))
  d.line([(cx-186,cy-58),(cx-97,cy-115),(cx+10,cy-25),(cx+106,cy-135),(cx+185,cy-166)],fill=white,width=12,joint="curve")
 elif icon=="energy":
  pts=[(cx+int(145*math.cos(2*math.pi*k/8)),cy+int(145*math.sin(2*math.pi*k/8))) for k in range(8)]
  d.line(pts+[pts[0]],fill=white,width=10)
  d.polygon([(cx+40,cy-170),(cx-95,cy+10),(cx+12,cy+10),(cx-48,cy+164),(cx+120,cy-37),(cx+14,cy-37)],fill=white)
 elif icon=="security":
  path=[(cx,cy-180),(cx+150,cy-125),(cx+125,cy+86),(cx,cy+182),(cx-125,cy+86),(cx-150,cy-125)]
  d.polygon(path,outline=white,width=12)
  d.line([(cx-74,cy+4),(cx-15,cy+64),(cx+85,cy-70)],fill=white,width=16,joint="curve")
 elif icon=="technology":
  for k in range(7):
   a=2*math.pi*k/7+index*.12
   x=cx+157*math.cos(a); y=cy+157*math.sin(a)
   d.line((cx,cy,x,y),fill=pale,width=8)
   d.ellipse((x-19,y-19,x+19,y+19),fill=white)
  d.ellipse((cx-53,cy-53,cx+53,cy+53),fill=white)
 elif icon=="climate":
  d.arc((cx-150,cy-150,cx+150,cy+150),15,350,fill=white,width=12)
  d.ellipse((cx-52,cy-48,cx+52,cy+55),outline=white,width=9)
  d.line([(cx,cy+93),(cx,cy-91)],fill=white,width=11)
  d.arc((cx-90,cy-125,cx+15,cy-12),315,118,fill=white,width=10)
  d.arc((cx-15,cy-8,cx+102,cy+101),140,305,fill=white,width=10)
 d.rounded_rectangle((50,45,348,96),radius=15,fill=(3,16,30,120))
 d.text((72,55),"RDI  /  GEOPOLITICA",font=font(25),fill=(255,255,255,235))
 d.line((55,520,1145,520),fill=(255,255,255,95),width=2)
 d.text((55,547),title,font=font(51),fill=(255,255,255,245))
 d.text((1106,572),f"{index:02}",font=font(39),fill=(255,255,255,180),anchor="ra")
 return base
def main():
 for topic,entry in TOPICS.items():
  folder=BASE/topic;folder.mkdir(parents=True,exist_ok=True)
  for index in range(1,11):
   path=folder/f"{index:02}.webp"
   image_for(topic,index,entry).save(path,"WEBP",quality=76,method=6)
   print(f"{path.relative_to(BASE)} {path.stat().st_size} bytes")
if __name__=="__main__":main()
