#!/usr/bin/env python3
"""릴스 표지(커버)를 인스타 프로필 그리드 기준으로 받아온다.

캡션 미리보기용 이미지(og:image)는 영상 중간 장면이 잡히는 경우가 많아,
소연님이 만든 진짜 표지가 나오도록 프로필 피드 정보를 쓴다.
"""
import json, os, subprocess, sys, time, io, base64
from PIL import Image

UID="64351397359"
UA=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126 Safari/537.36")
W=540

def api(url):
    r=subprocess.run(["curl","-sS","--max-time","30","-A",UA,
                      "-H","x-ig-app-id: 936619743392459",url],capture_output=True)
    try: return json.loads(r.stdout)
    except Exception: return None

covers={}
nxt=None
for page in range(45):
    u=f"https://www.instagram.com/api/v1/feed/user/{UID}/?count=33"
    if nxt: u+="&max_id="+nxt
    d=api(u)
    if not d or not d.get("items"): break
    for it in d["items"]:
        c=it.get("code")
        cands=(it.get("image_versions2") or {}).get("candidates") or []
        if c and cands: covers[c]=cands[0]["url"]
    if page%5==0: print(f"  {page+1}쪽 · {len(covers)}장", flush=True)
    if not d.get("next_max_id"): break
    nxt=d["next_max_id"]
    time.sleep(0.6)
print(f"표지 주소 {len(covers)}장 확보")

want=[c.strip() for c in open("data/reel-codes.txt",encoding="utf-8") if c.strip()]
os.makedirs("img",exist_ok=True)
got=miss=0
for c in want:
    u=covers.get(c)
    if not u: miss+=1; continue
    raw=subprocess.run(["curl","-sS","--max-time","30","-A",UA,u],capture_output=True).stdout
    try:
        im=Image.open(io.BytesIO(raw)).convert("RGB")
        w,h=im.size
        if w>W: im=im.resize((W,int(h*W/w)), Image.LANCZOS)
        im.save(f"img/{c}.webp","WEBP",quality=84,method=4)
        got+=1
    except Exception:
        miss+=1
    if got%40==0 and got: print(f"  내려받음 {got}장", flush=True)
    time.sleep(0.25)
print(f"표지 교체 {got}장 · 못 받음 {miss}장")
