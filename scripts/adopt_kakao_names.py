#!/usr/bin/env python3
"""매장 이름을 카카오 공식 명칭으로 맞춘다 (캡션 추출 이름은 2순위).

소연님이 직접 정한 이름은 건드리지 않는다.
"""
import json, re, subprocess, sys, time, urllib.parse
key=""
for line in open(".env",encoding="utf-8"):
    if line.strip().startswith("KAKAO_REST_KEY"): key=line.split("=",1)[1].strip()
PROTECT={'단소','명현만간장게장','하트티라미수','참치정육점','타마','육식문화','손수베이커리',
         '왔다떡방','동백야시장','나만의휴일','은주','온천집','백송한우','워크업','드림김밥',
         '친친양꼬치','부산오뎅','런던스테이지'}
def kakao(q):
    u="https://dapi.kakao.com/v2/local/search/keyword.json?size=5&query="+urllib.parse.quote(q)
    r=subprocess.run(["curl","-sS","--max-time","15","-H",f"Authorization: KakaoAK {key}",u],capture_output=True)
    try: return json.loads(r.stdout).get("documents",[])
    except: return []
def norm(s): return re.sub(r"[\s'‘’\"“”&·,.-]","",str(s)).lower()

h=open("index.html",encoding="utf-8").read()
m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
P=json.loads(m.group(1))
changed=[]
for i,p in enumerate(P,1):
    if not p.get('kid') or p['n'] in PROTECT: continue
    dong=re.match(r"(\S+동)", str(p.get("area") or ""))
    docs=kakao(f"대전 {dong.group(1)} {p['n']}" if dong else f"대전 {p['n']}")
    doc=next((d for d in docs if d['id']==p['kid']), None)
    if not doc: continue
    official=doc['place_name']
    off=re.sub(r"\s*(대전)?\S{0,7}(본점|지점|점)\s*$","",official).strip() or official
    if norm(off)!=norm(p['n']) and len(off)>=2:
        changed.append(f"{p['n']} → {off}")
        p['n']=off
    if i%80==0: print(f"  {i}/{len(P)} …",flush=True)
    time.sleep(0.12)
print(f"공식 이름으로 교체 {len(changed)}곳")
for c in changed[:25]: print("  ·",c)
blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
open("index.html","w",encoding="utf-8").write(h[:m.start()]+blk+h[m.end():])
