#!/usr/bin/env python3
"""즐겨찾기 버튼(북마클릿)으로 보내둔 릴스 커버 주소를 받아 img/<code>.webp 로 저장하고 썸네일·카드 커버에 붙인다.
   daily-care 에서 매일 돈다. 주소는 며칠이면 만료되므로 빨리 받는다.   python3 scripts/pull_reel_covers.py"""
import json, re, os, io, subprocess
from PIL import Image

env = dict(l.strip().split('=', 1) for l in open('.env') if '=' in l and not l.startswith('#'))
U = (env.get('SUPABASE_URL') or 'https://ntmzjsozgxjepwhxsniu.supabase.co').strip().strip('"')
K = env.get('SUPABASE_SERVICE_KEY', '').strip().strip('"')
if not K:
    print('SUPABASE_SERVICE_KEY 없음'); raise SystemExit
rows = json.loads(subprocess.run(['curl', '-s', '-m', '30',
    U + '/rest/v1/recommendation_logs?select=id,parsed_conditions,created_at&query=eq.__cover__&order=created_at.desc&limit=500',
    '-H', 'apikey: ' + K, '-H', 'Authorization: Bearer ' + K], capture_output=True, text=True).stdout or '[]')
seen = {}
for r in rows:
    pc = r.get('parsed_conditions') or {}
    if pc.get('code') and pc.get('url') and pc['code'] not in seen:
        seen[pc['code']] = pc['url']
print('보내둔 커버', len(seen))

h = open('index.html', encoding='utf-8').read()
mt = re.search(r'<script id="thumbs" type="application/json">([\s\S]*?)</script>', h)
T = json.loads(mt.group(1))
UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36'

def crop916(raw, out):
    im = Image.open(io.BytesIO(raw)).convert('RGB'); w, hh = im.size; tw, th = 540, 960
    if w / hh > tw / th:
        nw = int(hh * tw / th); im = im.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, hh))
    else:
        nh = int(w * th / tw); im = im.crop((0, (hh - nh) // 2, w, (hh - nh) // 2 + nh))
    im.resize((tw, th), Image.LANCZOS).save(out, 'WEBP', quality=84)

new = 0; fail = []
os.makedirs('img', exist_ok=True)
for code, url in seen.items():
    out = 'img/' + code + '.webp'
    if os.path.exists(out) and T.get(code) == out and os.path.getsize(out) > 20000:
        continue   # 이미 진짜 커버 있음
    r = subprocess.run(['curl', '-s', '-L', '-m', '30', '-A', UA, url], capture_output=True)
    if len(r.stdout) < 5000:
        fail.append(code); continue
    try:
        crop916(r.stdout, out); T[code] = out; new += 1
    except Exception:
        fail.append(code)

h = h[:mt.start()] + '<script id="thumbs" type="application/json">\n' + json.dumps(T, ensure_ascii=False) + '\n</script>' + h[mt.end():]
i = h.find('<script id="places"'); i = h.find('>', i) + 1; j = h.find('</script>', i)
P = json.loads(h[i:j]); n = 0
for p in P:
    codes = (p.get('igs') or []) + ([p['ig']] if p.get('ig') else [])
    real = [c for c in codes if T.get(c) == 'img/' + c + '.webp' and c in seen]
    if real and p.get('cover') != real[0]:
        p['cover'] = real[0]; p['photoSrc'] = '대전공주'; p.pop('noCardPhoto', None); n += 1
open('index.html', 'w', encoding='utf-8').write(h[:i] + json.dumps(P, ensure_ascii=False, separators=(',', ':')) + h[j:])
print('새로 받은 커버', new, '| 카드 커버 갱신', n, '| 실패(만료)', len(fail))
