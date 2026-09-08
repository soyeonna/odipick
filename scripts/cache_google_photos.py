#!/usr/bin/env python3
"""구글 방문자 사진을 오디픽 안(img/)에 받아둔다.  python3 scripts/cache_google_photos.py [--dry]

왜: 사진을 그때그때 구글에서 불러오면 방문자가 볼 때마다 구글 요청이 나가 요금이 붙는다.
    미리 받아두면 방문자는 오디픽에서만 사진을 가져오므로 요금이 0원이 된다.
주의: 구글 약관상 사진은 30일까지만 보관할 수 있다 → 매일 자동 작업이 25일 지난 것만 다시 받는다.
"""
import json, re, os, io, sys, subprocess, datetime, concurrent.futures as cf
from PIL import Image

DRY = '--dry' in sys.argv
MAXAGE = 25          # 며칠 지난 사진을 다시 받을지 (구글 약관 30일보다 짧게)
PER_PLACE = 3        # 매장당 받을 장수
WIDTH = 480          # 저장 크기 (상세 화면 표시 크기에 맞춤)

h = open('index.html', encoding='utf-8').read()
KEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
mp = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
mt = re.search(r'(<script id="thumbs" type="application/json">\s*)(\{[\s\S]*?\})(\s*</script>)', h)
P = json.loads(mp.group(2))
T = json.loads(mt.group(2))
today = datetime.date.today()

def stale(p):
    d = p.get('gplAt')
    if not d: return True
    try: return (today - datetime.date.fromisoformat(d)).days >= MAXAGE
    except Exception: return True

todo = [p for p in P if p.get('gphotos') and not p.get('closed') and stale(p)]
print(f'구글 사진 있는 매장 중 새로 받을 곳 {len(todo)}곳 (총 {sum(min(PER_PLACE, len(p["gphotos"])) for p in todo)}장)')
if DRY: raise SystemExit

os.makedirs('img', exist_ok=True)
def slug(n): return re.sub(r'\W', '', n)[:14] + str(abs(hash(n)) % 9999)

def grab(args):
    name, path = args
    url = f'https://places.googleapis.com/v1/{name}/media?key={KEY}&maxWidthPx={WIDTH*2}'
    raw = subprocess.run(['curl', '-sL', '-m', '40', '-H', 'Referer: https://soyeonna.github.io/', url],
                         capture_output=True).stdout
    if len(raw) < 2000: return False
    try:
        im = Image.open(io.BytesIO(raw)).convert('RGB')
        if im.width > WIDTH: im = im.resize((WIDTH, round(im.height * WIDTH / im.width)), Image.LANCZOS)
        im.save(path, 'WEBP', quality=80, method=4)
        return True
    except Exception:
        return False

jobs, plan = [], {}
for p in todo:
    codes = []
    for i, g in enumerate(p['gphotos'][:PER_PLACE]):
        code = 'g' + slug(p['n']) + '_' + str(i)
        codes.append(code)
        jobs.append((g['name'], f'img/{code}.webp'))
    plan[p['n']] = codes

ok = {}
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for (name, path), good in zip(jobs, ex.map(grab, jobs)):
        ok[path] = good
done = 0
for p in todo:
    codes = [c for c in plan[p['n']] if ok.get(f'img/{c}.webp')]
    if not codes:
        continue
    for c in codes: T[c] = f'img/{c}.webp'
    p['gpl'] = codes
    p['gby'] = [g.get('by') for g in p['gphotos'][:len(codes)] if g.get('by')]
    p['gplAt'] = today.isoformat()
    done += 1
print(f'사진 받아둔 매장 {done}곳 · 파일 {sum(1 for v in ok.values() if v)}장')

h = h[:mt.start(2)] + json.dumps(T, ensure_ascii=False) + h[mt.end(2):]
mp = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
h = h[:mp.start(2)] + json.dumps(P, ensure_ascii=False) + h[mp.end(2):]
open('index.html', 'w', encoding='utf-8').write(h)
