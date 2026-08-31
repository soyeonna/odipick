#!/usr/bin/env python3
"""공공데이터(localdata.go.kr 인허가) → 오디픽 로컬 아카이브 확충.

일반음식점·휴게음식점 전국 CSV(월간 공개본)를 받아 대전 영업중만 골라 넣는다.
새로 넣는 곳은 src="public" — 공주픽과 절대 섞이지 않는다.

  python3 scripts/import_public_data.py            # 다운로드 + 반영
  python3 scripts/import_public_data.py --dry      # 뭐가 들어갈지만
"""
import csv, io, json, os, re, subprocess, sys, zipfile

URLS = [  # 업종코드: 07_24_04_P 일반음식점, 07_24_05_P 휴게음식점
    "https://www.localdata.go.kr/datafile/each/07_24_04_P_CSV.zip",
    "https://www.localdata.go.kr/datafile/each/07_24_05_P_CSV.zip",
]
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126"

def fetch(url, out):
    r=subprocess.run(["curl","-sSL","--fail","--max-time","600","-A",UA,url,"-o",out],
                     capture_output=True)
    return r.returncode==0 and os.path.getsize(out)>100000

def rows_from(zpath):
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"): continue
            raw=z.read(name)
            for enc in ("cp949","utf-8","euc-kr"):
                try: text=raw.decode(enc); break
                except: continue
            rd=csv.DictReader(io.StringIO(text))
            for row in rd: yield row

def main():
    dry="--dry" in sys.argv
    os.makedirs("data/public",exist_ok=True)
    picked=[]
    for url in URLS:
        out="data/public/"+url.rsplit("/",1)[1]
        if not os.path.exists(out):
            print("내려받는 중:",url)
            if not fetch(url,out):
                print("  실패 — 사이트가 닫혀 있거나 주소가 바뀜"); continue
        n=0
        for r in rows_from(out):
            addr=r.get("소재지전체주소") or r.get("도로명전체주소") or ""
            if not addr.startswith("대전"): continue
            if (r.get("영업상태명") or r.get("상세영업상태명") or "") not in ("영업","영업/정상","정상"): continue
            name=(r.get("사업장명") or "").strip()
            if not name: continue
            picked.append({
                "n":name,
                "addr":addr,
                "cat_raw":(r.get("업태구분명") or "").strip(),
                "opened":(r.get("인허가일자") or "").strip(),
                "phone":(r.get("소재지전화") or "").strip() or None,
                "x":r.get("좌표정보(x)") or r.get("좌표정보(X)"),
                "y":r.get("좌표정보(y)") or r.get("좌표정보(Y)"),
            }); n+=1
        print(f"  {url.rsplit('/',1)[1]} → 대전 영업중 {n}곳")
    if not picked:
        sys.exit("가져온 것이 없습니다.")
    json.dump(picked, open("data/public/daejeon_raw.json","w",encoding="utf-8"),
              ensure_ascii=False)
    print(f"원본 저장: data/public/daejeon_raw.json ({len(picked)}곳)")
    if dry: return

    # ── 사이트에 병합: 이미 있는 곳은 건너뛰고, 새 곳만 src=public 으로
    CATMAP=[ (r"카페|다방|커피|제과|떡|아이스크림",["카페","디저트"]),
        (r"일식|횟집|초밥|복어",["일식"]),(r"중국|중화",["중식"]),
        (r"경양식|양식|패스트|외국",["양식"]),(r"분식",["분식"]),
        (r"호프|주점|소주|막걸리|유흥",["술집"]),
        (r"식육|갈비|삼겹",["고기","한식"]),(r"한식|탕|국|냉면",["한식"]) ]
    h=open("index.html",encoding="utf-8").read()
    m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
    P=json.loads(m.group(1))
    have={re.sub(r"\s","",p["n"]) for p in P}
    add=[]
    for r in picked:
        k=re.sub(r"\s","",r["n"])
        if k in have: continue
        have.add(k)
        dong=re.search(r"대전\S*?구\s+(\S+동)", r["addr"])
        cats=next((c for pat,c in CATMAP if re.search(pat,r["cat_raw"])),["한식"])
        old=len(r["opened"])>=4 and r["opened"][:4].isdigit() and int(r["opened"][:4])<=2000
        add.append({"n":r["n"],"cat":r["cat_raw"] or None,"cats":cats+(["노포"] if old else []),
            "area":dong.group(1) if dong else "", "gu":(re.search(r"대전\S*?\s(\S+구)",r["addr"]) or [None,None])[1],
            "hours":None,"budget":None,"sit":[],"fac":{},"cap":None,"ig":None,"link":None,
            "v":None,"src":"public","phone":r["phone"],"opened":r["opened"][:8] or None})
    P+=add
    blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
    open("index.html","w",encoding="utf-8").write(h[:m.start()]+blk+h[m.end():])
    print(f"새로 추가 {len(add)}곳 → 총 {len(P)}곳")

if __name__=="__main__":
    main()
