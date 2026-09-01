#!/usr/bin/env python3
"""공공데이터(소상공인 상가정보) → 대전 음식점·카페 로컬 아카이브.

결과는 dist 에 함께 배포되는 data/public-places.json 으로 저장.
사이트가 필요할 때 내려받아 검색 범위를 넓힌다. 공주픽과는 절대 안 섞임(src=public).
"""
import json, os, re, subprocess, sys, time

K=""
for line in open(".env",encoding="utf-8"):
    if line.strip().startswith("DATA_GO_KR_KEY"): K=line.split("=",1)[1].strip()
if not K: sys.exit("DATA_GO_KR_KEY 없음")

BASE="http://apis.data.go.kr/B553077/api/open/sdsc2/storeListInDong"
def page(no, rows=1000):
    u=f"{BASE}?serviceKey={K}&pageNo={no}&numOfRows={rows}&divId=ctprvnCd&key=30&type=json"
    for _ in range(3):
        b=subprocess.run(["curl","-sS","--max-time","40",u],capture_output=True).stdout
        try:
            d=json.loads(b)
            if 'body' in d: return d['body']
        except Exception: pass
        time.sleep(2)
    return None

b=page(1,10)
total=b['totalCount']
print(f"대전 전체 상가 {total}개 — 받는 중", flush=True)
rows=[]
pages=(total//1000)+2
for i in range(1,pages):
    b=page(i)
    if not b: print(f"  {i}쪽 실패"); continue
    items=b.get('items') or []
    if not items: break
    rows+=items
    if i%10==0: print(f"  {i}/{pages-1}쪽 · {len(rows)}개", flush=True)
print(f"수신 {len(rows)}개")

CATMAP=[
 (r"커피|카페|다방",["카페"]),(r"제과|베이커리|떡|도넛|아이스크림|디저트",["디저트","카페"]),
 (r"횟집|일식|초밥|수산|참치",["일식"]),(r"중국|중식",["중식"]),
 (r"경양식|양식|패스트푸드|피자|치킨|버거|외국",["양식"]),(r"분식",["분식"]),
 (r"호프|맥주|소주|주점|막걸리|와인|칵테일",["술집"]),
 (r"갈비|삼겹|곱창|족발|보쌈|육류|고기|구이",["고기","한식"]),
 (r"한식|국|탕|찌개|백반|냉면|국수|칼국수",["한식"]),
]
out=[]
for r in rows:
    if r.get('ctprvnNm')!='대전광역시': continue
    lcls=r.get('indsLclsNm') or ''
    if '음식' not in lcls: continue          # 음식 대분류만
    scls=(r.get('indsSclsNm') or r.get('indsMclsNm') or '').strip()
    if re.search(r'유흥|단란|노래|룸살롱|무도|구내|급식', scls): continue
    name=(r.get('bizesNm') or '').strip()
    if re.search(r'구내|급식|연구소|연구원|사업소|공장|어린이집|유치원|학교|병원|청사|복지관|수련원', name): continue
    if FR and re.search(FR, name, re.I): continue          # 프랜차이즈 제외
    if not name or len(name)>25: continue
    cats=next((c for pat,c in CATMAP if re.search(pat, scls+' '+(r.get('indsMclsNm') or ''))), ["한식"])
    dong=(r.get('bjdongNm') or r.get('ldongNm') or '').strip() or (r.get('adongNm') or '').strip()
    gu=(r.get('signguNm') or '').strip() or None
    try: lat=float(r.get('lat')); lng=float(r.get('lon'))
    except: lat=lng=None
    out.append({"n":name,"cat":scls or None,"cats":cats,"area":dong,"gu":gu,
                "lat":lat,"lng":lng,"src":"public","cap":4})
print(f"음식점·카페로 추린 것 {len(out)}개")
os.makedirs("data",exist_ok=True)
json.dump(out, open("data/public-places.json","w",encoding="utf-8"),
          ensure_ascii=False, separators=(",",":"))
sz=os.path.getsize("data/public-places.json")//1024//1024
print(f"저장: data/public-places.json ({sz}MB)")
