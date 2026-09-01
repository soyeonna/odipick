#!/usr/bin/env python3
"""한국관광공사 공식 사진을 여행·명소 매장에 연결한다 (공공누리, 출처표시 조건).

승인 직후에는 키 반영에 시간이 걸려 실패할 수 있다. --loop 로 기다렸다 재시도.
"""
import io, json, os, re, subprocess, sys, time, urllib.parse
from PIL import Image

BASE="http://apis.data.go.kr/B551011/KorService2"
W=540
K=""
for line in open(".env",encoding="utf-8"):
    if line.strip().startswith("DATA_GO_KR_KEY"): K=line.split("=",1)[1].strip()

def call(path, **kw):
    p={"serviceKey":K,"MobileOS":"ETC","MobileApp":"odipick","_type":"json"}
    p.update(kw)
    u=f"{BASE}/{path}?"+"&".join(f"{k}={urllib.parse.quote(str(v))}" for k,v in p.items())
    b=subprocess.run(["curl","-sS","--max-time","30",u],capture_output=True).stdout.decode("utf-8","ignore")
    if "SERVICE_KEY_IS_NOT_REGISTERED" in b: return "wait"
    try: return json.loads(b)["response"]["body"]
    except Exception: return None

def norm(s): return re.sub(r"[\s'‘’\"“”&·,.-]","",str(s)).lower()

def harvest():
    """대전(areaCode 3) 관광지·음식점 사진 목록"""
    got={}
    for ct in (12,14,39,28):          # 관광지·문화시설·음식점·레포츠
        page=1
        while page<=8:
            b=call("areaBasedList2", areaCode=3, contentTypeId=ct,
                   numOfRows=100, pageNo=page, arrange="A")
            if b=="wait": return "wait"
            if not b: break
            items=(b.get("items") or {}).get("item") or []
            if isinstance(items,dict): items=[items]
            for it in items:
                img=it.get("firstimage") or it.get("firstimage2")
                if img and it.get("title"): got[norm(it["title"])]=(it["title"], img)
            if page*100 >= int(b.get("totalCount") or 0): break
            page+=1
            time.sleep(0.4)
    return got

def main():
    loop="--loop" in sys.argv
    while True:
        data=harvest()
        if data=="wait":
            print("아직 키가 반영되지 않았습니다 (승인 후 몇 분~몇 시간)", flush=True)
            if not loop: return
            time.sleep(600); continue
        if not data:
            print("가져온 사진이 없습니다"); return
        print(f"관광공사 사진 {len(data)}건 확보", flush=True)
        break

    h=open("index.html",encoding="utf-8").read()
    m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
    P=json.loads(m.group(1))
    mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
    thumbs=json.loads(mt.group(1))
    os.makedirs("img",exist_ok=True)

    # 사진 없는 여행·명소·노포부터
    def needs(p):
        if p.get("closed"): return False
        if p.get("igs") or p.get("ph"): return False       # 릴스 표지 있으면 그대로
        return bool(p.get("travel")) or "노포" in (p.get("cats") or []) \
               or "나들이" in (p.get("cats") or []) or "체험" in (p.get("cats") or [])
    todo=[p for p in P if needs(p)]
    print(f"사진 붙일 후보 {len(todo)}곳")

    got=0
    for p in todo:
        key=norm(p["n"])
        hit=data.get(key) or next((v for k,v in data.items()
              if len(key)>=3 and (key in k or k in key)), None)
        if not hit: continue
        title,url=hit
        raw=subprocess.run(["curl","-sS","--max-time","30",url],capture_output=True).stdout
        try:
            im=Image.open(io.BytesIO(raw)).convert("RGB")
            w,hh=im.size
            # 릴스 표지와 같은 세로 3:4로 가운데를 잘라 통일
            tw,th=W,int(W*4/3)
            sc=max(tw/w, th/hh)
            im=im.resize((int(w*sc),int(hh*sc)), Image.LANCZOS)
            x=(im.width-tw)//2; y=(im.height-th)//2
            im=im.crop((x,y,x+tw,y+th))
            code=f"kto{abs(hash(p['n']))%10**10}"
            im.save(f"img/{code}.webp","WEBP",quality=84,method=4)
            thumbs[code]=f"img/{code}.webp"
            p["ph"]=code; p["photoSrc"]="한국관광공사"
            got+=1
        except Exception: pass
        time.sleep(0.2)
    print(f"사진 연결 {got}곳")

    blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
    h=h[:m.start()]+blk+h[m.end():]
    mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
    blk2='<script id="thumbs" type="application/json">\n'+json.dumps(thumbs,ensure_ascii=False)+'\n</script>'
    h=h[:mt.start()]+blk2+h[mt.end():]
    open("index.html","w",encoding="utf-8").write(h)

if __name__=="__main__":
    main()
