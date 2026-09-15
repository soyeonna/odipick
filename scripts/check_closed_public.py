#!/usr/bin/env python3
"""공공데이터(localdata.go.kr 인허가) 영업상태로 폐업·휴업을 대조한다.

  python3 scripts/check_closed_public.py            # 내려받기(월 1회) + 대조
  python3 scripts/check_closed_public.py --no-fetch # 받아둔 파일로만

원칙
 - 자동으로 내리지 않는다. 폐업/휴업으로 나온 곳은 근거(상태·날짜·인허가 주소)와 함께
   data/review_queue.json 과 docs/검수함.md 에 쌓고, 사이트에는 closedSuspect 표시만 한다.
 - 상호 + 동(洞)이 같아야 같은 가게로 본다. 상호만 같으면 후보로만 적는다.
 - 소연님이 확인한 값(ownerCheckedAt)은 건드리지 않는다.
"""
import csv, io, json, os, re, sys, zipfile, subprocess, datetime, time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__))); os.chdir(ROOT)
URLS=["https://www.localdata.go.kr/datafile/each/07_24_04_P_CSV.zip",
      "https://www.localdata.go.kr/datafile/each/07_24_05_P_CSV.zip"]
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126"
TODAY=datetime.date.today().isoformat()

def fetch(url,out):
    r=subprocess.run(["curl","-sSL","--fail","--max-time","900","-A",UA,url,"-o",out],capture_output=True)
    return r.returncode==0 and os.path.getsize(out)>100000

def rows(zpath):
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():
            if not name.lower().endswith(".csv"): continue
            raw=z.read(name)
            for enc in ("cp949","utf-8","euc-kr"):
                try: text=raw.decode(enc); break
                except Exception: continue
            for row in csv.DictReader(io.StringIO(text)): yield row

def norm(s): return re.sub(r'[\s\-·,.()&]|주식회사|\(주\)|본점|대전점|둔산점|직영점','',str(s or '')).lower()

def main():
    os.makedirs("data/public",exist_ok=True)
    daejeon=[]
    for url in URLS:
        out="data/public/"+url.rsplit("/",1)[1]
        stale=(not os.path.exists(out)) or (time.time()-os.path.getmtime(out)>27*86400)
        if stale and "--no-fetch" not in sys.argv:
            print("내려받는 중:",url,flush=True)
            if not fetch(url,out): print("  실패"); continue
        if not os.path.exists(out): continue
        for r in rows(out):
            addr=(r.get("소재지전체주소") or r.get("도로명전체주소") or "")
            if not addr.startswith("대전"): continue
            daejeon.append({"n":(r.get("사업장명") or "").strip(),"addr":addr,
                "road":r.get("도로명전체주소") or "","status":(r.get("영업상태명") or r.get("상세영업상태명") or "").strip(),
                "closedAt":(r.get("폐업일자") or "").strip(),"cat":(r.get("업태구분명") or "").strip()})
    if not daejeon: sys.exit("공공데이터를 못 읽었습니다.")
    json.dump(daejeon,open("data/public/daejeon_status.json","w",encoding="utf-8"),ensure_ascii=False)
    print(f"대전 인허가 {len(daejeon)}건 (영업·폐업 포함)")
    by={}
    for r in daejeon: by.setdefault(norm(r["n"]),[]).append(r)

    H=open("index.html",encoding="utf-8").read()
    m=re.search(r'(<script id="places" type="application/json">)\s*(\[.*?\])\s*(</script>)',H,re.S); P=json.loads(m.group(2))
    queue=[]; flagged=0
    for p in P:
        if p.get("src")=="public" or p.get("closed"): continue
        cands=by.get(norm(p["n"])) or []
        if not cands: continue
        dong=(re.search(r'([가-힣]+동)',str(p.get("addr") or p.get("area") or "")) or [None,None])[1]
        same=[c for c in cands if dong and dong in c["addr"]] if dong else []
        pool=same or cands
        alive=[c for c in pool if c["status"].startswith("영업") or c["status"] in ("정상","영업/정상")]
        dead=[c for c in pool if re.search(r"폐업|휴업|취소|말소",c["status"])]
        if dead and not alive:
            c=sorted(dead,key=lambda x:x["closedAt"],reverse=True)[0]
            level="확정후보" if same else "상호만일치"
            p["closedSuspect"]={"source":"localdata.go.kr","status":c["status"],"closedAt":c["closedAt"],"addr":c["addr"],"level":level,"checkedAt":TODAY}
            queue.append({"n":p["n"],"area":p.get("area"),"status":c["status"],"closedAt":c["closedAt"],"publicAddr":c["addr"],"level":level,"owner":p.get("ownerCheckedAt")}); flagged+=1
        elif p.get("closedSuspect") and p["closedSuspect"].get("source")=="localdata.go.kr" and alive:
            p.pop("closedSuspect",None)
    H=H[:m.start(2)]+json.dumps(P,ensure_ascii=False)+H[m.end(2):]; open("index.html","w",encoding="utf-8").write(H)
    json.dump({"updatedAt":TODAY,"items":queue},open("data/review_queue.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
    lines=["# 검수함 — 인허가 폐업·휴업 의심 ("+TODAY+")","","자동으로 내리지 않았습니다. 확인 후 폐업이면 `scripts/apply_owner_fixes.py` 로 내려주세요.","",
           "| 가게 | 동네 | 인허가 상태 | 날짜 | 인허가 주소 | 신뢰 |","|---|---|---|---|---|---|"]
    for q in sorted(queue,key=lambda x:(x["level"]!="확정후보",x["n"])):
        lines.append(f"| {q['n']} | {q['area'] or ''} | {q['status']} | {q['closedAt']} | {q['publicAddr']} | {q['level']} |")
    open("docs/검수함.md","w",encoding="utf-8").write("\n".join(lines)+"\n")
    print(f"폐업·휴업 의심 {flagged}곳 → docs/검수함.md, data/review_queue.json")
    for q in queue[:40]: print(f"  · {q['n']:<18} {q['status']} {q['closedAt']} [{q['level']}]")

if __name__=="__main__": main()
