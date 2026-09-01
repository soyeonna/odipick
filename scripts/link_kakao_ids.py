#!/usr/bin/env python3
"""모든 매장에 카카오 고유번호(kid)·지도링크(kurl)를 단다.

같은 kid = 같은 매장. 중복 통합과 정확한 지도 연결의 기준이 된다.
이름+동네가 실제로 일치하는 결과만 믿는다.
"""
import json, re, subprocess, sys, time, urllib.parse

key=""
for line in open(".env",encoding="utf-8"):
    if line.strip().startswith("KAKAO_REST_KEY"): key=line.split("=",1)[1].strip()
if not key: sys.exit("KAKAO_REST_KEY 없음")

def kakao(q):
    u="https://dapi.kakao.com/v2/local/search/keyword.json?size=5&query="+urllib.parse.quote(q)
    r=subprocess.run(["curl","-sS","--max-time","15","-H",f"Authorization: KakaoAK {key}",u],capture_output=True)
    try: return json.loads(r.stdout).get("documents",[])
    except: return []

def norm(s): return re.sub(r"[\s'‘’\"“”&·,.-]","",str(s)).lower()

h=open("index.html",encoding="utf-8").read()
m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
P=json.loads(m.group(1))
todo=[p for p in P if not p.get("kid")]
print(f"카카오 번호 없는 곳 {len(todo)}곳")
got=0
for i,p in enumerate(todo,1):
    dong=re.match(r"(\S+동)", str(p.get("area") or ""))
    n=p["n"]; nn=norm(n)
    doc=None
    for q in ([f"대전 {dong.group(1)} {n}"] if dong else [])+[f"대전 {n}", n]:
        docs=kakao(q)
        doc=next((d for d in docs if nn in norm(d["place_name"]) or norm(d["place_name"]) in nn), None)
        if doc: break
        time.sleep(0.12)
    if not doc: continue
    p["kid"]=doc["id"]; p["kurl"]=doc.get("place_url")
    if not p.get("lat") and doc.get("y"): p["lat"]=float(doc["y"]); p["lng"]=float(doc["x"])
    if not p.get("kcat"): p["kcat"]=doc.get("category_name")
    if not p.get("phone") and doc.get("phone"): p["phone"]=doc["phone"]
    got+=1
    if i%60==0: print(f"  {i}/{len(todo)} …",flush=True)
    time.sleep(0.12)
print(f"고유번호 단 곳 {got}곳 · 미확인 {len(todo)-got}곳")
blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
open("index.html","w",encoding="utf-8").write(h[:m.start()]+blk+h[m.end():])
