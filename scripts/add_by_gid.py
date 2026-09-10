#!/usr/bin/env python3
"""구글 장소 번호(gid) 목록을 받아 매장으로 넣는다. 공주픽이 아니므로 로컬 아카이브(src=local)로 들어간다.
   python3 scripts/add_by_gid.py <후보파일.json> <넣을개수>
   후보파일은 [{"n","gu","addr","r","c","ty"}] 형태이며, 구글 상세를 다시 받아 채운다."""
import json, re, sys, subprocess, time

src, take = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 20
cands = json.load(open(src, encoding='utf-8'))
h = open('index.html', encoding='utf-8').read()
KEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
have = {re.sub(r'\s', '', p['n']) for p in P}
gids = {p.get('gid') for p in P if p.get('gid')}

SKIP = re.compile(r'성심당|김밥나라|본죽|한솥|компания')
CATMAP = [(r'카페|커피|제과|베이커리|디저트', ['카페', '디저트'], '카페·베이커리'),
          (r'중국', ['중식'], '중식'), (r'일본|초밥|스시|돈까스', ['일식'], '일식'),
          (r'이탈리아|양식|피자|파스타|스테이크', ['양식'], '양식'),
          (r'해산물|횟집|회', ['한식'], '횟집'), (r'술집|주점|바\b|포차', ['술집'], '술집'),
          (r'국수|칼국수|냉면|면', ['한식'], '국수·칼국수'), (r'분식|김밥|떡볶이', ['분식'], '분식'),
          (r'고기|갈비|삼겹|곱창', ['고기'], '고깃집')]
FIELDS = ('id,displayName,formattedAddress,location,rating,userRatingCount,nationalPhoneNumber,'
          'regularOpeningHours.weekdayDescriptions,priceLevel,parkingOptions,goodForGroups,reservable,'
          'takeout,outdoorSeating,allowsDogs,primaryTypeDisplayName,businessStatus,reviews.text.text')
STORE = {'freeParkingLot', 'freeGarageParking', 'valetParking'}

def detail(gid):
    out = subprocess.run(['curl', '-s', '-m', '25', f'https://places.googleapis.com/v1/places/{gid}?languageCode=ko',
        '-H', 'X-Goog-Api-Key: ' + KEY, '-H', 'Referer: https://soyeonna.github.io/',
        '-H', 'X-Goog-FieldMask: ' + FIELDS], capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return None

def hours_of(g):
    w = (g.get('regularOpeningHours') or {}).get('weekdayDescriptions') or []
    if not w: return None
    t = {x.split(': ', 1)[-1] for x in w}
    if len(t) == 1: return '매일 ' + list(t)[0].replace('오전 ', '').replace('오후 ', '').replace(' ~ ', '–')
    return ' · '.join(x.replace('요일', '') for x in w[:2]) + ' 등'

added = []
for c in cands:
    if len(added) >= take: break
    if SKIP.search(c['n']) or re.sub(r'\s', '', c['n']) in have: continue
    gid = c.get('id') or c.get('gid')
    if not gid:
        continue
    g = detail(gid)
    if not g or g.get('businessStatus') not in (None, 'OPERATIONAL'): continue
    ty = (g.get('primaryTypeDisplayName') or {}).get('text', '') + ' ' + (c.get('ty') or '')
    cats, cat = ['한식'], '한식'
    for pat, cs, cn in CATMAP:
        if re.search(pat, ty): cats, cat = cs, cn; break
    loc = g.get('location') or {}
    addr = c['addr']
    dong = (re.search(r'([가-힣]+[동읍면])', addr) or [None, ''])[1]
    po = g.get('parkingOptions') or {}
    fac = {}
    if po: fac['parking'] = bool(STORE & set(po))
    for gk, fk in (('goodForGroups', 'group'), ('reservable', 'reserve'), ('takeout', 'takeout'), ('allowsDogs', 'pet')):
        if gk in g: fac[fk] = bool(g[gk])
    p = {'n': c['n'], 'cat': cat, 'cats': cats,
         'area': (dong + ' ' + re.sub(r'^[가-힣]+[동읍면]\s*', '', re.sub(r'^(동구|중구|서구|유성구|대덕구)\s*', '', addr))).strip()[:36],
         'gu': c['gu'], 'hours': hours_of(g),
         'budget': {'PRICE_LEVEL_INEXPENSIVE': 1, 'PRICE_LEVEL_MODERATE': 2,
                    'PRICE_LEVEL_EXPENSIVE': 3, 'PRICE_LEVEL_VERY_EXPENSIVE': 4}.get(g.get('priceLevel')),
         'sit': ['가족', '친구모임'], 'fac': fac, 'cap': 4,
         'v': '', 'src': 'local', 'lat': loc.get('latitude'), 'lng': loc.get('longitude'),
         'gid': gid, 'gname': g['displayName']['text']}
    if g.get('nationalPhoneNumber'): p['phone'] = g['nationalPhoneNumber']
    if g.get('rating'): p['grating'] = g['rating']; p['gcount'] = g.get('userRatingCount', 0)
    if g.get('outdoorSeating'): p['mood'] = ['테라스']
    if po: p['gpark'] = [k for k in po if po[k]]
    P.append(p); have.add(re.sub(r'\s', '', c['n']))
    added.append((c['n'], c['gu'], cat, c['r'], c['c']))
    time.sleep(0.1)

print(f'넣은 곳 {len(added)}')
for a in added: print('  ✔', a[1], a[0], '|', a[2], '| ★', a[3], a[4])
h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
open('index.html', 'w', encoding='utf-8').write(h)
