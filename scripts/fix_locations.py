#!/usr/bin/env python3
"""다른 지역 좌표가 붙은 매장을 구글 지도로 바로잡고, 카카오 연결도 다시 맞춘다.
   python3 scripts/fix_locations.py [--dry]

이름만 같은 타지역 매장은 절대 쓰지 않는다 — 대전(또는 근교) 범위 안 + 이름이 닮은 곳만 인정.
못 찾으면 좌표를 비우고 docs/검토-매장연결.md 에 남긴다.
"""
import json, re, subprocess, sys, time, math, difflib, urllib.parse

DRY = '--dry' in sys.argv
h = open('index.html', encoding='utf-8').read()
GKEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
KKEY = [l.split('=', 1)[1].strip() for l in open('.env', encoding='utf-8') if l.startswith('KAKAO_REST_KEY')][0]

DJ   = (36.15, 36.55, 127.20, 127.60)
NEAR = (35.80, 37.05, 126.20, 128.20)
def inbox(la, lo, b): return b[0] <= la <= b[1] and b[2] <= lo <= b[3]
def norm(s):
    t = re.sub(r"[\s'’\"“”&·,.\-()]", '', str(s or '')).lower()
    return t
def subseq(short, long):
    it = iter(long)
    return all(c in it for c in short)
def nobranch(t):
    m2 = re.match(r"^(.{2,}?)(본점|직영점|[가-힣a-z]{2,6}점)$", t)   # '행운대전월평점' → '행운'
    return m2.group(1) if m2 else t
def sim1(a, b):
    if not a or not b: return 0
    if a == b: return 1.0
    if a in b or b in a: return 0.95
    s, l = (a, b) if len(a) <= len(b) else (b, a)
    if len(s) >= 3 and subseq(s, l): return 0.85
    if len(s) >= 2 and l.startswith(s): return 0.82
    return 0
def sim(a, b):
    """이름이 같은 가게인지. 글자가 순서대로 들어있거나 지점명만 다른 경우를 인정한다.
       '봉달이김밥'⊂'봉달이명품김밥' 인정 · '행운삼겹살'↔'행운 대전월평점' 인정 · '을지면옥'↔'양지면옥' 불인정."""
    a, b = norm(a), norm(b)
    return max(sim1(a, b), sim1(a, nobranch(b)), sim1(nobranch(a), b))
def km(a, b): return math.hypot((a[1]-b[1])*88.8, (a[0]-b[0])*111.1)

def gsearch(q, box, _try=0):
    body = {'textQuery': q, 'languageCode': 'ko', 'pageSize': 10,
            'locationRestriction': {'rectangle': {'low': {'latitude': box[0], 'longitude': box[2]},
                                                   'high': {'latitude': box[1], 'longitude': box[3]}}}}
    out = subprocess.run(['curl', '-s', '-m', '30', '-X', 'POST',
        'https://places.googleapis.com/v1/places:searchText', '-H', 'Content-Type: application/json',
        '-H', 'X-Goog-Api-Key: ' + GKEY, '-H', 'Referer: https://soyeonna.github.io/',
        '-H', 'X-Goog-FieldMask: places.id,places.displayName,places.formattedAddress,places.location,places.primaryTypeDisplayName',
        '-d', json.dumps(body, ensure_ascii=False)], capture_output=True, text=True).stdout
    try:
        r = json.loads(out)
    except Exception:
        return []
    if 'error' in r: print('  ! 구글 응답 오류:', str(r['error'])[:90])
    got = r.get('places', [])
    if not got and _try < 2:          # 응답이 비면 잠깐 쉬고 다시 물어본다
        time.sleep(1.2)
        return gsearch(q, box, _try + 1)
    return got

def kakao(q, x=None, y=None, code=None):
    p = {'size': 15, 'query': q}
    if code: p['category_group_code'] = code
    if x: p.update({'x': str(x), 'y': str(y), 'radius': 3000, 'sort': 'distance'})
    u = 'https://dapi.kakao.com/v2/local/search/keyword.json?' + urllib.parse.urlencode(p)
    r = subprocess.run(['curl', '-sS', '--max-time', '15', '-H', f'Authorization: KakaoAK {KKEY}', u], capture_output=True)
    try: return json.loads(r.stdout).get('documents', [])
    except Exception: return []

m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
FOOD = {'한식','중식','일식','분식','양식','고기','술집','카페','디저트'}
NOTFOOD = re.compile(r'^(교육|부동산|가정,생활|의료|금융|서비스,산업)')

fixed, cleared, relinked = [], [], []
for p in P:
    box = NEAR if p.get('gu') == '대전근교' else DJ
    off = p.get('lat') and not inbox(p['lat'], p['lng'], box)
    if not off: continue
    dong = re.match(r'(\S+[동읍면리])', str(p.get('area') or ''))
    dong = dong.group(1) if dong else ''
    best = None
    for q in [f"대전 {dong} {p['n']}".replace('  ', ' '), f"대전 {p['n']}", f"{dong} {p['n']}".strip(), p['n']]:
        for g in gsearch(q, box):
            loc = g.get('location') or {}
            la, lo = loc.get('latitude'), loc.get('longitude')
            if la is None or not inbox(la, lo, box): continue
            s = sim(p['n'], g['displayName']['text'])
            if s < 0.8: continue                       # 이름이 확실히 같아야 한다 (봉달이김밥↔동글이김밥 같은 오연결 방지)
            addr = g.get('formattedAddress', '')
            bonus = 0.3 if dong and dong in addr else 0
            if not best or s + bonus > best[0]: best = (s + bonus, g, la, lo)
        if best and best[0] >= 1.2: break
        time.sleep(0.15)
    if best and p.get('gu') == '대전근교' and best[0] < 1.25:
        best = None          # 근교는 동네 이름까지 맞아야 인정 (같은 이름 타지역 지점 방지)
    if not best and dong:    # 구글에서 못 찾으면 카카오로 한 번 더 (동네를 아는 곳만)
        for q in [f"대전 {dong} {p['n']}".strip(), f"{dong} {p['n']}".strip(), f"대전 {p['n']}"]:
            for d in kakao(q):
                la, lo = float(d['y']), float(d['x'])
                if not inbox(la, lo, box) or sim(p['n'], d['place_name']) < 0.8: continue
                addr = (d.get('road_address_name') or '') + ' ' + (d.get('address_name') or '')
                if dong and dong not in addr: continue
                best = (1.0, {'id': None, 'displayName': {'text': d['place_name']}, 'formattedAddress': addr.strip()}, la, lo)
                p['kid'] = d['id']; p['kurl'] = d.get('place_url'); p['kcat'] = d.get('category_name')
                if d.get('phone'): p['phone'] = d['phone']
                break
            if best: break
            time.sleep(0.1)
    if best:
        _, g, la, lo = best
        fixed.append((p['n'], p.get('area'), g['displayName']['text'], g.get('formattedAddress', '')[:40]))
        p['lat'], p['lng'] = la, lo
        if g['id']: p['gid'] = g['id']; p['gname'] = g['displayName']['text']
        p.pop('gAt', None)                                  # 구글 정보 다시 받게
        if g['id']:
            for k in ('kid', 'kurl', 'kcat'): p.pop(k, None)    # 옛 카카오 연결은 버린다
        p.pop('needsLoc', None)
    else:
        cleared.append((p['n'], p.get('area'), '대전 안에서 같은 이름을 못 찾음'))
        for k in ('lat', 'lng', 'kid', 'kurl', 'kcat', 'gid', 'gname', 'gAt'): p.pop(k, None)
        p['needsLoc'] = True

# 음식점인데 학원·부동산·문구 같은 데 연결된 곳: 좌표 근처에서 다시 찾는다
for p in P:
    if not p.get('lat') or not (FOOD & set(p.get('cats') or [])): continue
    if not (p.get('kcat') and NOTFOOD.match(p['kcat'])): continue
    got = None
    for d in kakao(p['n'], p['lng'], p['lat'], 'FD6') + kakao(p['n'], p['lng'], p['lat'], 'CE7'):
        if sim(p['n'], d['place_name']) >= 0.6 and km((float(d['y']), float(d['x'])), (p['lat'], p['lng'])) <= 1.0:
            got = d; break
    if got:
        relinked.append((p['n'], got['place_name'], got['category_name']))
        p['kid'] = got['id']; p['kurl'] = got.get('place_url'); p['kcat'] = got.get('category_name')
        if got.get('phone'): p['phone'] = got['phone']
    else:
        relinked.append((p['n'], '(연결 끊음)', p['kcat']))
        for k in ('kid', 'kurl', 'kcat'): p.pop(k, None)

print(f'좌표 바로잡음 {len(fixed)}곳 · 못 찾아 비움 {len(cleared)}곳 · 업종 재연결 {len(relinked)}곳')
for f in fixed:    print('  ✔', f[0], '·', f[1], '→', f[2], '·', f[3])
for c in cleared:  print('  ✖', c[0], '·', c[1], '·', c[2])
for r in relinked: print('  ↻', r[0], '→', r[1], '·', r[2])

if not DRY:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
    L = ['# 검토 필요 — 매장 위치', '', '대전 안에서 같은 이름을 못 찾아 위치를 비워둔 곳이다.',
         '엉뚱한 위치를 보여주는 것보다 낫다고 판단해 비웠다. 카카오맵 주소를 알려주시면 넣는다.', '']
    for c in cleared: L.append(f'- **{c[0]}** ({c[1] or "동네 모름"}) — {c[2]}')
    open('docs/검토-매장연결.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
