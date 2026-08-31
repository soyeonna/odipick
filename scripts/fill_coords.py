#!/usr/bin/env python3
"""좌표(lat/lng)가 없는 가게를 카카오 검색으로 채운다. 지도 핀이 늘어난다."""
import json, os, re, subprocess, sys, time, urllib.parse

key=""
for line in open(".env",encoding="utf-8"):
    if line.strip().startswith("KAKAO_REST_KEY"): key=line.split("=",1)[1].strip()
if not key: sys.exit("KAKAO_REST_KEY 없음")

def kakao(q):
    u="https://dapi.kakao.com/v2/local/search/keyword.json?size=3&query="+urllib.parse.quote(q)
    r=subprocess.run(["curl","-sS","--max-time","15","-H",f"Authorization: KakaoAK {key}",u],capture_output=True)
    try: return json.loads(r.stdout).get("documents",[])
    except: return []

h=open("index.html",encoding="utf-8").read()
m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
P=json.loads(m.group(1))
todo=[p for p in P if not p.get("lat") and not p.get("closed")]
print(f"좌표 없는 곳 {len(todo)}곳")
got=0
for i,p in enumerate(todo,1):
    dong=re.match(r"(\S+동)", str(p.get("area") or ""))
    q=(f"대전 {dong.group(1)} {p['n']}" if dong else f"대전 {p['n']}")
    docs=kakao(q) or kakao(f"대전 {p['n']}")
    if docs:
        d=docs[0]
        # 동이 있으면 주소가 그 동과 맞는 결과만 믿는다 (엉뚱한 지점 방지)
        addr=(d.get("road_address_name") or d.get("address_name") or "")
        if dong and dong.group(1) not in (d.get("address_name") or ""):
            alt=next((x for x in docs if dong.group(1) in (x.get("address_name") or "")),None)
            d=alt or None
        if d:
            p["lat"]=float(d["y"]); p["lng"]=float(d["x"]); got+=1
    if i%60==0: print(f"  {i}/{len(todo)} …",flush=True)
    time.sleep(0.2)
print(f"좌표 채움 {got}곳")
blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
open("index.html","w",encoding="utf-8").write(h[:m.start()]+blk+h[m.end():])
