#!/usr/bin/env python3
"""가게 이름 목록을 받아 구글 지도에서 정보를 찾아 오디픽에 넣는다.
   python3 scripts/add_cafes.py "오브떼르" "플라네 178" ...
   사진은 구글 방문자 사진만 쓴다. 남의 게시물 사진은 쓰지 않는다.
   공주픽이 아니므로 src='local' (로컬 아카이브) 로 들어간다.
"""
import json, re, sys, subprocess, time, difflib

NAMES = sys.argv[1:]
if not NAMES: sys.exit('가게 이름을 넣어주세요')
h = open('index.html', encoding='utf-8').read()
GKEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
DJ = (36.15, 36.55, 127.20, 127.60)

def norm(s): return re.sub(r"[\s'’\"“”&·,.\-()]|본점|직영점|\d*호?점$", '', str(s or '')).lower()
def subseq(s, l):
    it = iter(l); return all(c in it for c in s)
def same(a, b):
    a, b = norm(a), norm(b)
    if not a or not b: return 0
    if a == b: return 1.0
    if a in b or b in a: return 0.95
    s, l = (a, b) if len(a) <= len(b) else (b, a)
    if len(s) >= 2 and subseq(s, l): return 0.85
    return 0

FIELDS = ('places.id,places.displayName,places.formattedAddress,places.location,places.rating,'
          'places.userRatingCount,places.nationalPhoneNumber,places.regularOpeningHours.weekdayDescriptions,'
          'places.priceLevel,places.parkingOptions,places.goodForGroups,places.reservable,places.takeout,'
          'places.outdoorSeating,places.allowsDogs,places.primaryTypeDisplayName,places.businessStatus')
def gsearch(q):
    body = {'textQuery': q, 'languageCode': 'ko', 'pageSize': 5,
            'locationRestriction': {'rectangle': {'low': {'latitude': DJ[0], 'longitude': DJ[2]},
                                                   'high': {'latitude': DJ[1], 'longitude': DJ[3]}}}}
    out = subprocess.run(['curl', '-s', '-m', '30', '-X', 'POST',
        'https://places.googleapis.com/v1/places:searchText', '-H', 'Content-Type: application/json',
        '-H', 'X-Goog-Api-Key: ' + GKEY, '-H', 'Referer: https://soyeonna.github.io/',
        '-H', 'X-Goog-FieldMask: ' + FIELDS,
        '-d', json.dumps(body, ensure_ascii=False)], capture_output=True, text=True).stdout
    try: return json.loads(out).get('places', [])
    except Exception: return []

def gu_of(addr):
    m = re.search(r'(동구|중구|서구|유성구|대덕구)', addr or '')
    return m.group(1) if m else None
def dong_of(addr):
    m = re.search(r'([가-힣]+[동읍면])', addr or '')
    return m.group(1) if m else ''
def budget_of(pl):
    return {'PRICE_LEVEL_INEXPENSIVE': 1, 'PRICE_LEVEL_MODERATE': 1,
            'PRICE_LEVEL_EXPENSIVE': 2, 'PRICE_LEVEL_VERY_EXPENSIVE': 3}.get(pl, 1)
def hours_of(g):
    w = (g.get('regularOpeningHours') or {}).get('weekdayDescriptions') or []
    if not w: return None
    times = set()
    for line in w:
        t = line.split(': ', 1)[-1]
        times.add(t)
    if len(times) == 1:
        return '매일 ' + list(times)[0].replace('오전 ', '').replace('오후 ', '')
    return ' · '.join(x.replace('요일', '') for x in w[:2]) + ' 등'

m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
existing = {norm(p['n']) for p in P}
added, skipped = [], []
STORE = {'freeParkingLot', 'freeGarageParking', 'valetParking'}

for name in NAMES:
    if norm(name) in existing: skipped.append((name, '이미 있음')); continue
    best = None
    for q in [f'대전 {name} 카페', f'대전 {name}', name]:
        for g in gsearch(q):
            loc = g.get('location') or {}
            la, lo = loc.get('latitude'), loc.get('longitude')
            if la is None: continue
            s = same(name, g['displayName']['text'])
            if s < 0.8: continue
            if g.get('businessStatus') and g['businessStatus'] != 'OPERATIONAL': continue
            if not best or s > best[0]: best = (s, g, la, lo)
        if best and best[0] >= 0.95: break
        time.sleep(0.2)
    if not best:
        skipped.append((name, '구글에서 못 찾음')); continue
    _, g, la, lo = best
    addr = g.get('formattedAddress', '').replace('대한민국 대전광역시 ', '')
    po = g.get('parkingOptions') or {}
    fac = {'parking': bool(STORE & set(po)) or True}      # 주차 되는 카페 목록에서 온 곳이라 주차는 있음
    for gk, fk in (('goodForGroups', 'group'), ('reservable', 'reserve'), ('takeout', 'takeout'), ('allowsDogs', 'pet')):
        if gk in g: fac[fk] = bool(g[gk])
    p = {'n': name, 'cat': '카페', 'cats': ['카페'], 'area': (dong_of(addr) + ' ' + re.sub(r'^[가-힣]+[동읍면]\s*', '', addr)).strip()[:40],
         'gu': gu_of(g.get('formattedAddress', '')), 'hours': hours_of(g),
         'budget': budget_of(g.get('priceLevel')), 'sit': ['데이트', '친구모임'],
         'fac': fac, 'cap': 8, 'mood': ['넓은'],
         'v': '주차 편한 대형 카페', 'src': 'local',
         'lat': la, 'lng': lo, 'gid': g['id'], 'gname': g['displayName']['text'],
         'facLock': True}
    if g.get('nationalPhoneNumber'): p['phone'] = g['nationalPhoneNumber']
    if g.get('rating'): p['grating'] = g['rating']; p['gcount'] = g.get('userRatingCount', 0)
    if g.get('outdoorSeating'): p['mood'].append('테라스')
    if po: p['gpark'] = [k for k in po if po[k]]
    P.append(p); existing.add(norm(name))
    added.append((name, g['displayName']['text'], addr[:34], g.get('rating'), g.get('userRatingCount')))

print(f'넣은 곳 {len(added)} · 건너뛴 곳 {len(skipped)}')
for a in added: print('  ✔', a[0], '→', a[1], '|', a[2], '| ★', a[3], a[4])
for s in skipped: print('  ✖', s[0], '—', s[1])
h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
open('index.html', 'w', encoding='utf-8').write(h)
