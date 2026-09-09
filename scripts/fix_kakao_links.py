#!/usr/bin/env python3
"""잘못 연결된 카카오 매장(다른 지역·엉뚱한 업종)을 찾아 바로잡는다.
   python3 scripts/fix_kakao_links.py [--dry]

이름만 같은 타지역 매장은 절대 연결하지 않는다. 이름 + 동네 + 업종이 모두 맞아야 연결한다.
확신이 없으면 좌표를 지우고 docs/검토-매장연결.md 에 남긴다 (엉뚱한 위치를 보여주는 것보다 낫다).
"""
import json, re, subprocess, sys, time, urllib.parse, math

DRY = '--dry' in sys.argv
key = ''
for line in open('.env', encoding='utf-8'):
    if line.strip().startswith('KAKAO_REST_KEY'): key = line.split('=', 1)[1].strip()
if not key: sys.exit('KAKAO_REST_KEY 없음')

DJ = (36.15, 36.55, 127.20, 127.60)          # 대전 대략 범위
NEAR = (35.90, 37.00, 126.30, 128.10)        # 대전근교(공주·세종·보령 등)

def inbox(lat, lng, b): return b[0] <= lat <= b[1] and b[2] <= lng <= b[3]
def norm(s): return re.sub(r"[\s'’\"“”&·,.\-()]", '', str(s or '')).lower()
def km(a, b): return math.hypot((a[1]-b[1])*88.8, (a[0]-b[0])*111.1)

def kakao(q, code=None, x=None, y=None):
    p = {'size': 15, 'query': q}
    if code: p['category_group_code'] = code
    if x: p.update({'x': x, 'y': y, 'radius': 20000})
    u = 'https://dapi.kakao.com/v2/local/search/keyword.json?' + urllib.parse.urlencode(p)
    r = subprocess.run(['curl', '-sS', '--max-time', '15', '-H', f'Authorization: KakaoAK {key}', u], capture_output=True)
    try: return json.loads(r.stdout).get('documents', [])
    except Exception: return []

h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))

FOODCAT = {'한식','중식','일식','분식','양식','고기','술집','카페','디저트','노포','신상'}
def is_food(p): return bool(FOODCAT & set(p.get('cats') or []))
def bad_kcat(p):
    k = p.get('kcat') or ''
    return is_food(p) and k and not re.match(r'음식점|카페', k)

# 동 중심 좌표 (제대로 된 좌표만으로 계산)
centers = {}
for p in P:
    d = re.match(r'(\S+[동읍면])', str(p.get('area') or ''))
    if d and p.get('lat') and inbox(p['lat'], p['lng'], DJ):
        centers.setdefault(d.group(1), []).append((p['lat'], p['lng']))
for d, v in centers.items():
    centers[d] = (sorted(x[0] for x in v)[len(v)//2], sorted(x[1] for x in v)[len(v)//2])

fixed, cleared, review = [], [], []
for p in P:
    if not p.get('lat') and not p.get('kid'): continue
    box = NEAR if p.get('gu') == '대전근교' else DJ
    off = p.get('lat') and not inbox(p['lat'], p['lng'], box)
    if not off and not bad_kcat(p): continue      # 문제 없는 곳은 건드리지 않는다

    dong = re.match(r'(\S+[동읍면])', str(p.get('area') or ''))
    dong = dong.group(1) if dong else None
    ctr = centers.get(dong)
    nn = norm(p['n'])
    code = 'CE7' if (set(p.get('cats') or []) & {'카페', '디저트'} and not set(p.get('cats') or []) & {'한식','고기','일식','분식','양식','중식'}) else ('FD6' if is_food(p) else None)

    best = None
    queries = ([f"대전 {dong} {p['n']}"] if dong else []) + [f"대전 {p['n']}", p['n']]
    for q in queries:
        for d in kakao(q, code, str(ctr[1]) if ctr else None, str(ctr[0]) if ctr else None):
            la, lo = float(d['y']), float(d['x'])
            if not inbox(la, lo, box): continue                       # 다른 지역이면 제외
            dn = norm(d['place_name'])
            if not (nn in dn or dn in nn): continue                   # 이름이 달라도 제외
            if is_food(p) and not re.match(r'음식점|카페', d.get('category_name') or ''): continue
            addr = (d.get('road_address_name') or '') + ' ' + (d.get('address_name') or '')
            near = (dong and dong in addr) or (ctr and km((la, lo), ctr) <= 3.0)
            if not near: continue                                     # 동네가 달라도 제외
            sc = (2 if dong and dong in addr else 0) + (1 if dn == nn else 0)
            if not best or sc > best[0]: best = (sc, d, la, lo)
        if best: break
        time.sleep(0.1)

    if best:
        _, d, la, lo = best
        fixed.append((p['n'], p.get('area'), d['place_name'], d.get('road_address_name') or d.get('address_name')))
        p['kid'] = d['id']; p['kurl'] = d.get('place_url'); p['lat'] = la; p['lng'] = lo
        p['kcat'] = d.get('category_name') or p.get('kcat')
        if d.get('phone'): p['phone'] = d['phone']
        p.pop('needsLoc', None)
    else:
        why = '다른 지역 좌표' if off else '엉뚱한 업종'
        cleared.append((p['n'], p.get('area'), why, p.get('kcat')))
        for k in ('lat', 'lng', 'kid', 'kurl', 'kcat'): p.pop(k, None)
        p['needsLoc'] = True
        review.append(p)

print(f'바로잡음 {len(fixed)}곳 · 확인 못 해 좌표 지움 {len(cleared)}곳')
for f in fixed: print('  ✔', f[0], '·', f[1], '→', f[2], '·', f[3])
for c in cleared: print('  ✖', c[0], '·', c[1], '·', c[2], c[3] or '')

if not DRY:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
    L = ['# 검토 필요 — 매장 연결', '', '이름·동네·업종이 모두 맞는 카카오 매장을 못 찾아 위치를 비워둔 곳이다.',
         '카카오맵에서 직접 찾아 주소를 알려주시면 넣는다.', '']
    for c in cleared: L.append(f'- **{c[0]}** ({c[1] or "동네 모름"}) — {c[2]}' + (f' · 전에 연결됐던 업종: {c[3]}' if c[3] else ''))
    open('docs/검토-매장연결.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
    print('검토 목록: docs/검토-매장연결.md')
