#!/usr/bin/env python3
"""릴스 표지(커버)를 인스타 프로필 그리드 기준으로 조금씩 받아온다.

미리보기용 이미지는 영상 중간 장면이 잡히는 일이 많아, 소연님이 만든 진짜 표지가
나오도록 프로필 피드 정보를 쓴다. 인스타가 한 번에 많이 안 주므로 이어받기 방식.

  python3 scripts/fetch_covers.py          # 몇 쪽 받고 종료 (이어받기)
  python3 scripts/fetch_covers.py --loop   # 다 받을 때까지 쉬어가며 반복
"""
import json, os, subprocess, sys, time, io
from PIL import Image

UID="64351397359"
UA=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36")
STATE="data/cover-state.json"
W=540
PAGES_PER_RUN=3

def api(url):
    r=subprocess.run(["curl","-sS","--max-time","30","-A",UA,
                      "-H","x-ig-app-id: 936619743392459",url],capture_output=True)
    try: return json.loads(r.stdout)
    except Exception: return None

def load():
    if os.path.exists(STATE):
        return json.load(open(STATE,encoding="utf-8"))
    return {"covers":{}, "next":None, "done":False}

def save(st):
    os.makedirs("data",exist_ok=True)
    json.dump(st, open(STATE,"w",encoding="utf-8"), ensure_ascii=False)

def collect(st):
    """표지 주소를 몇 쪽만 더 받는다. 제한에 걸리면 False."""
    for _ in range(PAGES_PER_RUN):
        u=f"https://www.instagram.com/api/v1/feed/user/{UID}/?count=33"
        if st["next"]: u+="&max_id="+st["next"]
        d=api(u)
        if not d or d.get("status")=="fail" or not d.get("items"):
            return False
        for it in d["items"]:
            c=it.get("code")
            cands=(it.get("image_versions2") or {}).get("candidates") or []
            if c and cands: st["covers"][c]=cands[0]["url"]
        if not d.get("next_max_id"):
            st["done"]=True; return True
        st["next"]=d["next_max_id"]
        time.sleep(2)
    return True

def download(st):
    want=[c.strip() for c in open("data/reel-codes.txt",encoding="utf-8") if c.strip()]
    done=set(json.load(open("data/cover-done.json",encoding="utf-8"))) \
        if os.path.exists("data/cover-done.json") else set()
    os.makedirs("img",exist_ok=True)
    got=0
    for c in want:
        if c in done: continue
        u=st["covers"].get(c)
        if not u: continue
        raw=subprocess.run(["curl","-sS","--max-time","30","-A",UA,u],capture_output=True).stdout
        try:
            im=Image.open(io.BytesIO(raw)).convert("RGB")
            w,h=im.size
            if w>W: im=im.resize((W,int(h*W/w)), Image.LANCZOS)
            im.save(f"img/{c}.webp","WEBP",quality=84,method=4)
            done.add(c); got+=1
        except Exception: pass
        time.sleep(0.2)
    json.dump(sorted(done), open("data/cover-done.json","w",encoding="utf-8"))
    return got, len(want)-len(done)

def main():
    loop="--loop" in sys.argv
    while True:
        st=load()
        ok=collect(st)
        save(st)
        got,left=download(st)
        print(f"표지 주소 {len(st['covers'])}장 · 이번에 교체 {got}장 · 남은 릴스 {left}개"
              + ("" if ok else " (인스타 제한 — 잠시 쉼)"), flush=True)
        if st.get("done") and left==0: print("전부 완료"); break
        if not loop: break
        time.sleep(240 if ok else 420)

if __name__=="__main__":
    main()
