#!/usr/bin/env python3
"""릴스 썸네일을 받아 작게 줄여 저장한다. 로그인·토큰 불필요."""
import json, os, re, subprocess, sys, time, html as H, io, base64

CODES="data/reel-codes.txt"; OUT="data/reel-thumbs.json"
BOT="facebookexternalhit/1.1"
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
W=540          # 카드가 150px로 보이므로 고화질(3배) 기준
from PIL import Image

got=json.load(open(OUT,encoding='utf-8')) if os.path.exists(OUT) else {}
codes=[c.strip() for c in open(CODES,encoding='utf-8') if c.strip()]
todo=[c for c in codes if c not in got]
print(f"받을 썸네일 {len(todo)}개", flush=True)
fail=0
for i,c in enumerate(todo,1):
    try:
        b=subprocess.run(["curl","-sS","--max-time","20","-A",BOT,
                          f"https://www.instagram.com/p/{c}/"],capture_output=True).stdout.decode('utf-8','ignore')
        m=re.search(r'og:image[^>]*content="([^"]*)"',b)
        if not m: fail+=1; continue
        url=H.unescape(m.group(1))
        raw=subprocess.run(["curl","-sS","--max-time","25","-A",UA,url],capture_output=True).stdout
        im=Image.open(io.BytesIO(raw)).convert("RGB")
        w,h=im.size
        if w>W: im=im.resize((W,int(h*W/w)), Image.LANCZOS)   # 원본이 작으면 늘리지 않는다
        buf=io.BytesIO(); im.save(buf,"JPEG",quality=88,optimize=True,subsampling=0)
        got[c]="data:image/jpeg;base64,"+base64.b64encode(buf.getvalue()).decode()
    except Exception:
        fail+=1
    if i%25==0:
        json.dump(got,open(OUT,'w',encoding='utf-8'),ensure_ascii=False)
        print(f"  {i}/{len(todo)} …", flush=True)
    time.sleep(0.5)
json.dump(got,open(OUT,'w',encoding='utf-8'),ensure_ascii=False)
print(f"끝. 썸네일 {len(got)}개, 실패 {fail}개")
