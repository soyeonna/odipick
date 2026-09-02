#!/usr/bin/env python3
"""소연님이 번호로 지정한 사진을 매장에 붙인다 (없으면 매장도 새로 등록)."""
import io, json, os, re, subprocess, sys, glob, urllib.parse
from PIL import Image, ImageChops
W=540; H=int(W*16/9)

def norm(s): return re.sub(r"[\s'‘’\"“”&·,.\-()]","",str(s)).lower()
def trim(im):
    g=im.convert("RGB")
    for bg in ((0,0,0),(255,255,255)):
        d=ImageChops.difference(g,Image.new("RGB",g.size,bg)); b=d.getbbox()
        if b and (b[2]-b[0])>g.width*.5 and (b[3]-b[1])>g.height*.4: g=g.crop(b)
    return g
def to916(im):
    w,h=im.size; sc=max(W/w,H/h)
    im=im.resize((max(1,int(w*sc)),max(1,int(h*sc))),Image.LANCZOS)
    return im.crop(((im.width-W)//2,(im.height-H)//2,(im.width-W)//2+W,(im.height-H)//2+H))

key=""
for l in open(".env",encoding="utf-8"):
    if l.strip().startswith("KAKAO_REST_KEY"): key=l.split("=",1)[1].strip()
def kakao(q):
    u="https://dapi.kakao.com/v2/local/search/keyword.json?size=5&query="+urllib.parse.quote(q)
    r=subprocess.run(["curl","-sS","--max-time","15","-H",f"Authorization: KakaoAK {key}",u],capture_output=True)
    try: return json.loads(r.stdout).get("documents",[])
    except: return []

spec=json.load(open(sys.argv[1],encoding="utf-8"))
h=open("index.html",encoding="utf-8").read()
m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
P=json.loads(m.group(1))
mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
thumbs=json.loads(mt.group(1))
byname={norm(p["n"]):p for p in P}
added=updated=0
for s in spec:
    f=glob.glob(f"shots_left/{s['no']}_*")
    if not f: print("사진 없음:",s["no"]); continue
    p=byname.get(norm(s["n"]))
    if not p:
        docs=kakao(f"대전 {s.get('area') or ''} {s['n']}") or kakao(s["n"])
        d=docs[0] if docs else None
        p={"n":s["n"],"cat":s.get("cat"),"cats":s.get("cats") or [],
           "area":s.get("area"),"gu":s.get("gu"),"hours":None,"budget":None,"cap":4,
           "sit":s.get("sit") or [],"fac":{},"v":s.get("note"),"src":"local"}
        if d:
            p.update({"kid":d["id"],"kurl":d.get("place_url"),
                      "lat":float(d["y"]),"lng":float(d["x"]),
                      "phone":d.get("phone") or None,"kcat":d.get("category_name")})
            if not p["cat"]: p["cat"]=d["category_name"].split(">")[-1].strip()
        P.append(p); byname[norm(s["n"])]=p; added+=1
    else: updated+=1
    for k in ("area","gu","cat"):
        if s.get(k): p[k]=s[k]
    if s.get("cats"): p["cats"]=sorted(set((p.get("cats") or [])+s["cats"]))
    if s.get("sit"):  p["sit"]=sorted(set((p.get("sit") or [])+s["sit"]))[:5]
    if s.get("travel"): p["travel"]=1
    if s.get("top"): p["jjin"]=1
    if s.get("note") and not p.get("v"): p["v"]=s["note"]
    code="pic"+re.sub(r"\W","",norm(s["n"]))[:14]+str(abs(hash(s["n"]))%9999)
    to916(trim(Image.open(f[0]))).save(f"img/{code}.webp","WEBP",quality=86,method=4)
    thumbs[code]=f"img/{code}.webp"; p["ph"]=code; p.pop("noCardPhoto",None); p["photoSrc"]="대전공주"
print(f"새로 등록 {added}곳 · 기존 갱신 {updated}곳")
blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
h=h[:m.start()]+blk+h[m.end():]
mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
blk2='<script id="thumbs" type="application/json">\n'+json.dumps(thumbs,ensure_ascii=False)+'\n</script>'
open("index.html","w",encoding="utf-8").write(h[:mt.start()]+blk2+h[mt.end():])
