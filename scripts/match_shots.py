#!/usr/bin/env python3
"""사진첩에서 내보낸 스크린샷을 읽어 가게별 대표사진으로 연결한다.

맥 내장 글자 인식으로 사진 속 상호명을 읽고, 등록된 매장과 맞춰본다.
글자가 안 읽히거나 매칭이 안 되면 그냥 버린다 (추측하지 않음).
"""
import io, json, os, re, subprocess, sys, glob
from PIL import Image

SHOTS="shots"
OCR="/tmp/ocr/ocrtool"
W=540

def norm(s): return re.sub(r"[\s'‘’\"“”&·,.\-()]","",str(s)).lower()

def ocr(paths):
    out={}
    for i in range(0,len(paths),25):
        chunk=paths[i:i+25]
        r=subprocess.run([OCR]+chunk,capture_output=True,timeout=600)
        for line in r.stdout.decode("utf-8","ignore").splitlines():
            if "\t" in line:
                p,t=line.split("\t",1); out[p]=t
        print(f"  글자 읽는 중 {min(i+25,len(paths))}/{len(paths)}", flush=True)
    return out

def main():
    dry="--dry" in sys.argv
    if not os.path.exists(OCR): sys.exit("글자 인식 도구가 없습니다")
    paths=sorted(glob.glob(f"{SHOTS}/*.PNG"))+sorted(glob.glob(f"{SHOTS}/*.png"))
    if not paths: sys.exit("shots 폴더가 비어 있습니다")
    print(f"스크린샷 {len(paths)}장")

    h=open("index.html",encoding="utf-8").read()
    m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
    P=json.loads(m.group(1))
    mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
    thumbs=json.loads(mt.group(1))

    # 사진이 필요한 매장 (카드 사진이 없거나 표지가 아닌 곳)
    need={}
    for p in P:
        if p.get("closed"): continue
        if p.get("noCardPhoto") or not (p.get("ph") or p.get("igs")):
            n=norm(p["n"])
            if len(n)>=2: need.setdefault(n,p)
    print(f"사진 필요한 매장 {len(need)}곳")

    texts=ocr(paths)
    hits={}
    for path,txt in texts.items():
        t=norm(txt)
        if len(t)<4: continue
        best=None
        for n,p in need.items():
            if len(n)>=3 and n in t:
                if best is None or len(n)>len(best[0]): best=(n,p)
        if best: hits.setdefault(best[0],[]).append(path)

    print(f"이름이 읽힌 매장 {len(hits)}곳")
    if dry:
        for n,v in list(hits.items())[:20]: print(f"  · {need[n]['n']} ← {len(v)}장")
        return

    os.makedirs("img",exist_ok=True)
    got=0
    for n,files in hits.items():
        p=need[n]
        src=sorted(files, key=lambda f: -os.path.getsize(f))[0]
        try:
            im=Image.open(src).convert("RGB")
            w,hh=im.size
            tw,th=W,int(W*4/3)
            sc=max(tw/w, th/hh)
            im=im.resize((int(w*sc),int(hh*sc)), Image.LANCZOS)
            x=(im.width-tw)//2; y=int((im.height-th)*0.35)
            im=im.crop((x,y,x+tw,y+th))
            code="shot"+re.sub(r"\W","",norm(p["n"]))[:14]+str(abs(hash(p["n"]))%9999)
            im.save(f"img/{code}.webp","WEBP",quality=84,method=4)
            thumbs[code]=f"img/{code}.webp"
            p["ph"]=code; p.pop("noCardPhoto",None); p["photoSrc"]="사진첩"
            got+=1
        except Exception: pass
    print(f"대표사진 연결 {got}곳")

    blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
    h=h[:m.start()]+blk+h[m.end():]
    mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
    blk2='<script id="thumbs" type="application/json">\n'+json.dumps(thumbs,ensure_ascii=False)+'\n</script>'
    h=h[:mt.start()]+blk2+h[mt.end():]
    open("index.html","w",encoding="utf-8").write(h)

if __name__=="__main__":
    main()
