#!/usr/bin/env python3
"""가격대(budget)가 비어 있는 매장을 채운다.   python3 scripts/fill_budget.py [--dry]
   1) 릴스 캡션·문구에 적힌 가격 → 평균으로   2) 없으면 카카오 업종 + 구글 가격단계로 추정
   자동으로 채운 곳은 budgetAuto:true 표시 → 소연님이 나중에 고치면 표시를 지운다.
   가격대: 1=1만원 이하 · 2=1–2만원 · 3=2–3만원 · 4=3–5만원 · 5=5만원 이상"""
import json, re, sys
dry = '--dry' in sys.argv
h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
def norm(s): return re.sub(r'\s', '', s or '')
R = json.load(open('data/reels_parsed.json', encoding='utf-8'))
reel_prices = {}
for r in R:
    if r.get('shop') and r.get('prices'):
        reel_prices.setdefault(norm(r['shop']), []).extend(x['p'] for x in r['prices'] if x.get('p'))
def from_prices(ps):
    ps = [p for p in ps if 1000 <= p <= 300000]
    if not ps: return None
    avg = sum(ps) / len(ps)
    for lim, b in ((10000, 1), (20000, 2), (35000, 3), (60000, 4)):
        if avg <= lim: return b
    return 5
CHEAP = '카페|디저트|제과|베이커리|분식|칼국수|냉면|순대|국밥|두부|찌개|전골|돈까스|우동|치킨|패스트푸드|간식|백반|국수|김밥|만두|떡|빵|죽|해장'
MID = '중식|중국|태국|아시아|퓨전|파스타|피자|양식|이탈리안|버거|덮밥|라멘|카레|족발|보쌈|닭요리|찜|탕'
PRICY = '육류|고기|삼겹|갈비|곱창|막창|회|해물|생선|초밥|롤|일식|스시|호프|요리주점|일본식주점|이자카야|포장마차|술집|칵테일|바|와인|스테이크|오리|장어|한정식'
TOP = '한우|오마카세|파인다이닝|코스요리'
SKIP = '문화시설|공원|관광|미술|박물관|공연|체험|나들이|숙소|쇼핑|뷰티|운동|문구|스포츠|패션|휴양림'
def guess(p):
    key = ' '.join([p.get('kcat') or '', p.get('cat') or '', ' '.join(p.get('cats') or []), p['n']])
    g = p.get('gprice') or ''
    if re.search(SKIP, key) and not re.search('카페|디저트|한식|고기|술집|일식|중식|양식|분식', key): return None, None
    if re.search(TOP, key): b, why = 4, '한우·오마카세'
    elif re.search(PRICY, key): b, why = 3, '고기·회·술집'
    elif re.search(CHEAP, key): b, why = 1, '카페·분식·국수'
    elif re.search(MID, key): b, why = 2, '중식·양식·아시아'
    elif '한식' in key: b, why = 2, '한식'
    else: return None, None
    if g == 'PRICE_LEVEL_INEXPENSIVE': b = max(1, b - 1); why += ' + 구글 저렴'
    elif g == 'PRICE_LEVEL_EXPENSIVE': b = min(5, b + 1); why += ' + 구글 비쌈'
    elif g == 'PRICE_LEVEL_VERY_EXPENSIVE': b = 5; why += ' + 구글 아주 비쌈'
    return b, why
filled, review, left = 0, [], []
for p in P:
    if p.get('budget'): continue
    b, why = None, None
    ps = reel_prices.get(norm(p['n'])) or next((v for k, v in reel_prices.items() if norm(p['n']) in k or k in norm(p['n'])), [])
    ps = ps + [int(x.replace(',', '')) for x in re.findall(r'([\d,]{4,7})\s*원', p.get('v') or '')]
    if ps: b = from_prices(ps); why = '가격 ' + '·'.join(f'{x:,}' for x in ps[:4])
    if not b: b, why = guess(p)
    if not b: left.append(p); continue
    p['budget'] = b; p['budgetAuto'] = True; filled += 1
    review.append({'n': p['n'], 'cat': p.get('cat'), 'budget': b, 'why': why})
print(f'가격대 채움 {filled}곳 · 못 채움 {len(left)}곳 (음식점 아님 등)')
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
    json.dump(review, open('data/budget-review.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('검토 목록: data/budget-review.json')
