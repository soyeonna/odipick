#!/usr/bin/env python3
"""소연님이 고른 스크린샷을 9:16 커버로 만들어 매장에 붙인다.

- 위아래 검은 띠(레터박스)를 잘라낸다
- 9:16 비율로 가운데를 자른다 (검은 화면 안 나오게)
- 사진 속 글자로 가게 이름을 읽어 자동으로 짝짓는다
"""
import io, json, os, re, subprocess, sys, glob
from PIL import Image, ImageChops

SRC="shots_pick"; OCR="/tmp/ocr/ocrtool"
W=540; H=int(W*16/9)

def norm(s): return re.sub(r"[\s'‘’\"“”&·,.\-()]","",str(s)).lower()

def trim_black(im):
    """가장자리 검은/흰 띠 제거"""
    g=im.convert("RGB")
    for bg in ((0,0,0),(255,255,255)):
        base=Image.new("RGB",g.size,bg)
        diff=ImageChops.difference(g,base)
        bbox=diff.getbbox()
        if bbox and (bbox[2]-bbox[0])>g.width*0.5 and (bbox[3]-bbox[1])>g.height*0.4:
            g=g.crop(bbox)
    return g

def to916(im):
    w,h=im.size
    tw,th=W,H
    sc=max(tw/w, th/h)
    im=im.resize((max(1,int(w*sc)),max(1,int(h*sc))), Image.LANCZOS)
    x=(im.width-tw)//2
    y=int((im.height-th)*0.5)
    return im.crop((x,y,x+tw,y+th))

def ocr(paths):
    out={}
    for i in range(0,len(paths),25):
        r=subprocess.run([OCR]+paths[i:i+25],capture_output=True,timeout=900)
        for line in r.stdout.decode("utf-8","ignore").splitlines():
            if "\t" in line:
                p,t=line.split("\t",1); out[p]=t
        print(f"  글자 읽는 중 {min(i+25,len(paths))}/{len(paths)}", flush=True)
    return out

def main():
    dry="--dry" in sys.argv
    paths=sorted([p for p in glob.glob(f"{SRC}/*") if os.path.splitext(p)[1].lower() in ('.png','.jpg','.jpeg','.heic')])
    print(f"고른 사진 {len(paths)}장")
    h=open("index.html",encoding="utf-8").read()
    m=re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h)
    P=json.loads(m.group(1))
    mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
    thumbs=json.loads(mt.group(1))

    names={}
    for p in P:
        if p.get("closed"): continue
        n=norm(p["n"])
        if len(n)>=2: names.setdefault(n,p)

    texts=ocr(paths)
    hits={}
    for path,txt in texts.items():
        t=norm(txt)
        if len(t)<3: continue
        best=None
        for n,p in names.items():
            if len(n)>=2 and n in t:
                if best is None or len(n)>len(best[0]): best=(n,p)
        if best: hits.setdefault(best[0],[]).append(path)
    print(f"가게 이름이 읽힌 사진 → {len(hits)}곳 매칭")
    if dry:
        for n,v in list(hits.items())[:40]: print(f"  · {names[n]['n']} ← {len(v)}장")
        left=[os.path.basename(p) for p in paths if not any(p in v for v in hits.values())]
        print(f"매칭 안 된 사진 {len(left)}장")
        return

    os.makedirs("img",exist_ok=True)
    got=0
    for n,files in hits.items():
        p=names[n]
        src=sorted(files, key=lambda f: -os.path.getsize(f))[0]
        try:
            im=to916(trim_black(Image.open(src)))
            code="pic"+re.sub(r"\W","",n)[:14]+str(abs(hash(p["n"]))%9999)
            im.save(f"img/{code}.webp","WEBP",quality=86,method=4)
            thumbs[code]=f"img/{code}.webp"
            p["ph"]=code; p.pop("noCardPhoto",None); p["photoSrc"]="대전공주"
            got+=1
        except Exception as e: print("  실패:",p["n"],e)
    print(f"커버 적용 {got}곳")
    blk='<script id="places" type="application/json">\n'+json.dumps(P,ensure_ascii=False,separators=(",",":"))+'\n</script>'
    h=h[:m.start()]+blk+h[m.end():]
    mt=re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>',h)
    blk2='<script id="thumbs" type="application/json">\n'+json.dumps(thumbs,ensure_ascii=False)+'\n</script>'
    open("index.html","w",encoding="utf-8").write(h[:mt.start()]+blk2+h[mt.end():])

if __name__=="__main__":
    main()
