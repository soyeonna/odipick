#!/usr/bin/env python3
"""모든 매장에 카카오 고유번호(kid)·지도링크(kurl)를 단다.

  python3 scripts/link_kakao_ids.py [--dry]

같은 kid = 같은 매장. 중복 통합과 정확한 지도 연결의 기준이 된다.

연결 기준 (소연님이 정한 것)
  · 상호만 일치            → 연결하지 않는다
  · 상호 + 동네 일치        → '후보'로만 적어둔다 (kidCandidates). 사람이 확정한다
  · 상호 + 동네 + 좌표 근접 → 자동 확정
  · 업종이 다르면(음식점인데 카페·학원)  → 연결하지 않는다
예전엔 '대전 {상호}' 검색만으로 자동 확정해서 엉뚱한 지점·카페가 붙은 적이 있다.
"""
import json, re, subprocess, sys, time, urllib.parse, math
DRY = "--dry" in sys.argv

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
def dist_m(a_lat,a_lng,b_lat,b_lng):
    return math.hypot((b_lng-a_lng)*88900, (b_lat-a_lat)*111000)

todo=[p for p in P if not p.get("kid")]
print(f"카카오 번호 없는 곳 {len(todo)}곳")
got=0; cand=0; skipped=0
FOOD={"한식","중식","일식","분식","양식","고기","술집","카페","디저트","면","해산물"}
for i,p in enumerate(todo,1):
    dong=re.match(r"(\S+동)", str(p.get("area") or ""))
    n=p["n"]; nn=norm(n)
    if not dong:                                   # 동네를 모르면 상호만으로는 절대 안 붙인다
        skipped+=1; continue
    docs=kakao(f"대전 {dong.group(1)} {n}")
    time.sleep(0.12)
    same_name=[d for d in docs if nn in norm(d["place_name"]) or norm(d["place_name"]) in nn]
    same_dong=[d for d in same_name if dong.group(1) in str(d.get("address_name") or "")]
    if not same_dong:
        # 상호는 맞는데 동네가 다르다 = 지점이 다르거나 우리 동네 정보가 틀린 것.
        # 붙이지는 않되, 사람이 볼 수 있게 '동네 불일치' 후보로 남긴다 (예: 은주 봉명동 vs 갈마동)
        p["kidCandidates"]=[{"id":d["id"],"name":d["place_name"],"addr":d.get("road_address_name") or d.get("address_name"),
                             "dist":None,"dongMismatch":True} for d in same_name[:3]]
        cand+=1; continue
    # 업종 검사: 음식점인데 카페·학원·부동산이면 제외 (카페는 카페끼리만)
    want_cafe = ("카페" in (p.get("cats") or [])) or ("디저트" in (p.get("cats") or []))
    def kind_ok(d):
        cn=str(d.get("category_name") or "")
        if FOOD & set(p.get("cats") or []):
            if want_cafe: return cn.startswith("음식점 > 카페") or cn.startswith("카페")
            return cn.startswith("음식점") and not cn.startswith("음식점 > 카페")
        return True
    same_dong=[d for d in same_dong if kind_ok(d)]
    if not same_dong:
        skipped+=1; continue
    box=(35.80,37.05,126.20,128.20) if p.get("gu")=="대전근교" else (36.15,36.55,127.20,127.60)
    same_dong=[d for d in same_dong if box[0]<=float(d["y"])<=box[1] and box[2]<=float(d["x"])<=box[3]]
    if not same_dong:
        skipped+=1; continue
    # 좌표가 있으면 150m 안에 있는 것만 확정. 좌표가 없거나 멀면 후보.
    confirmed=None
    if p.get("lat") and p.get("lng"):
        near=[d for d in same_dong if dist_m(p["lat"],p["lng"],float(d["y"]),float(d["x"]))<=150]
        if len(near)==1: confirmed=near[0]
    if confirmed:
        doc=confirmed
        p["kid"]=doc["id"]; p["kurl"]=doc.get("place_url")
        if not p.get("kcat"): p["kcat"]=doc.get("category_name")
        if not p.get("phone") and doc.get("phone"): p["phone"]=doc["phone"]
        p["kidHow"]="상호+동+좌표"
        got+=1
    else:
        # 확정 못 함 → 사람이 볼 후보만 적어둔다 (검수함)
        p["kidCandidates"]=[{"id":d["id"],"name":d["place_name"],"addr":d.get("road_address_name") or d.get("address_name"),
                             "dist":(round(dist_m(p["lat"],p["lng"],float(d["y"]),float(d["x"]))) if p.get("lat") else None)}
                            for d in same_dong[:3]]
        cand+=1
    if i%60==0: print(f"  {i}/{len(todo)} …",flush=True)
print(f"확정 {got}곳 · 후보만 남김 {cand}곳 · 건너뜀 {skipped}곳")
if cand:
    print("\n사람이 확인할 후보:")
    for p in todo:
        if p.get("kidCandidates") and not p.get("kid"):
            print("  ·", p["n"], "→", " / ".join(f'{c["name"]}({c["addr"]}{", "+str(c["dist"])+"m" if c["dist"] is not None else ""})' for c in p["kidCandidates"]))
if DRY:
    print("\n--dry 라서 파일은 그대로 뒀습니다."); sys.exit(0)
blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
open("index.html","w",encoding="utf-8").write(h[:m.start()]+blk+h[m.end():])
