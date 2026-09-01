#!/usr/bin/env python3
"""
오디픽 배포 빌드
- index.html 을 head 로 감싼다
- 사진 data URI 를 img/ 파일로 분리해 페이지를 가볍게 만든다
실행: python3 scripts/build_dist.py  → dist/ 갱신 후 넷리파이에 드래그
"""
import io, json, re, os, base64, shutil, sys

ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
src=io.open("index.html",encoding="utf-8").read()

HEAD='''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>오디픽 — 오늘은 어디 가지?</title>
<meta name="description" content="상황에 딱 맞는 곳 추천드려요">
<meta name="theme-color" content="#FF3F7F">
<meta name="format-detection" content="telephone=no">
<meta property="og:type" content="website">
<meta property="og:title" content="오디픽 — 오늘은 어디 가지?">
<meta property="og:description" content="상황에 딱 맞는 곳 추천드려요">
<meta property="og:locale" content="ko_KR">
<meta property="og:url" content="https://odipick.netlify.app">
<meta property="og:image" content="https://odipick.netlify.app/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://odipick.netlify.app/og.jpg">
<link rel="icon" href="favicon.png">
<link rel="apple-touch-icon" href="favicon.png">
<meta name="apple-mobile-web-app-title" content="오디픽">
<meta name="mobile-web-app-capable" content="yes">
<style>*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>
</head>
<body>
<script>window.__ODIPICK_DEPLOY__=true;</script>
'''

inner=re.sub(r'<title>[\s\S]*?</title>\s*','',src,count=1)

# 사진을 파일로 분리
shutil.rmtree("dist/img", ignore_errors=True)   # 안 쓰는 옛 사진이 쌓이지 않게
os.makedirs("dist/img",exist_ok=True)
os.makedirs("img",exist_ok=True)
m=re.search(r'(<script id="thumbs" type="application/json">\s*)(\{[\s\S]*?\})(\s*</script>)', inner)
T=json.loads(m.group(2))
paths={}
for k,v in T.items():
    if not v.startswith("data:image/"):
        # 이미 파일 경로면 그 파일을 dist 로 복사한다
        if v.startswith("img/") and os.path.exists(v):
            shutil.copy(v, f"dist/{v}")
        paths[k]=v; continue
    b64=v.split(",",1)[1]
    with open(f"dist/img/{k}.jpg","wb") as f: f.write(base64.b64decode(b64))
    paths[k]=f"img/{k}.jpg"
inner=inner[:m.start()]+m.group(1)+json.dumps(paths)+m.group(3)+inner[m.end():]

io.open("dist/index.html","w",encoding="utf-8").write(HEAD+inner+"\n</body>\n</html>\n")
shutil.copy("pin_clean.png","dist/favicon.png")
os.makedirs("dist/data",exist_ok=True)
if os.path.exists("img/princess-mark.png"):
    shutil.copy("img/princess-mark.png","dist/img/princess-mark.png")
if os.path.exists("data/public-places.json"):
    shutil.copy("data/public-places.json","dist/data/public-places.json")
size=os.path.getsize("dist/index.html")
imgs=sum(os.path.getsize(f"dist/img/{f}") for f in os.listdir("dist/img"))
print(f"dist/index.html {size//1024}KB · 이미지 {len(paths)}장 {imgs//1024//1024}MB (필요할 때만 받음)")
