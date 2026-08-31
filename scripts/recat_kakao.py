#!/usr/bin/env python3
"""분류를 카카오 공식 카테고리로 다시 잡는다.

캡션 낱말 추측 대신, 카카오 지도가 가게마다 갖고 있는 분류 경로
(예: 음식점 > 카페 > 제과,베이커리 / 서비스,산업 > 미용 > 피부관리)를 쓴다.
결과는 kcat 필드에 원문도 남겨 나중에 검증할 수 있게 한다.
"""
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

def cats_from(kcat, name):
    """카카오 분류 경로 → 오디픽 카테고리."""
    k=kcat
    if re.search(r"미용|피부|에스테틱|마사지|네일|두피|왁싱|스파", k): return ["뷰티"]
    if re.search(r"제과|베이커리|떡|도넛|케이크|디저트|빙수|아이스크림", k): return ["디저트","카페"]
    if re.search(r"카페|커피|찻집", k): return ["카페"]
    if re.search(r"육류|고기|갈비|삼겹|곱창|막창|족발|보쌈|치킨", k):
        out=["고기"]
        if re.search(r"주점|호프", k): out.append("술집")
        return out
    if re.search(r"술집|호프|요리주점|칵테일|와인|포장마차|오뎅바|이자카야", k): return ["술집"]
    if re.search(r"일식|초밥|회|돈까스|라면|우동|소바", k): return ["일식"]
    if re.search(r"중식|중국", k): return ["중식"]
    if re.search(r"양식|이탈리안|피자|햄버거|멕시칸|스테이크|브런치", k): return ["양식"]
    if re.search(r"분식|떡볶이|김밥", k): return ["분식"]
    if re.search(r"한식|국수|국밥|찌개|냉면|한정식|샤브|죽|백반", k): return ["한식"]
    return []

def main():
    dry="--dry" in sys.argv
    h=open("index.html",encoding="utf-8").read()
    m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
    P=json.loads(m.group(1))
    changed=beauty=nf=0
    for i,p in enumerate(P,1):
        dong=re.match(r"(\S+동)", str(p.get("area") or ""))
        docs=kakao(f"대전 {dong.group(1)} {p['n']}" if dong else f"대전 {p['n']}")
        # 이름이 실제로 일치하는 결과만 (다른 가게 분류 가져오는 사고 방지)
        nm=re.sub(r"\s","",p["n"])
        doc=next((d for d in docs if nm in re.sub(r"\s","",d["place_name"]) or
                  re.sub(r"\s","",d["place_name"]) in nm), None)
        if not doc:
            nf+=1
        else:
            p["kcat"]=doc["category_name"]
            new=cats_from(doc["category_name"], p["n"])
            if new:
                keep=[c for c in (p.get("cats") or []) if c in ("노포","신상")]
                merged=new+[c for c in keep if c not in new]
                if merged!=p.get("cats"):
                    p["cats"]=merged; changed+=1
                if "뷰티" in new: beauty+=1
        if i%60==0: print(f"  {i}/{len(P)} …",flush=True); 
        time.sleep(0.2)
    print(f"분류 갱신 {changed}곳 · 뷰티 {beauty}곳 · 카카오에서 못 찾음 {nf}곳")
    if dry: return
    blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
    open("index.html","w",encoding="utf-8").write(h[:m.start()]+blk+h[m.end():])

if __name__=="__main__":
    main()
