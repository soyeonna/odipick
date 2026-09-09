#!/usr/bin/env python3
"""가격대(budget)를 채운다.  python3 scripts/fill_budget.py [--dry]
   1순위: 실제 메뉴 가격 (1인 식사 기준 평균)   2순위: 업종별 추정 (구글 가격단계는 보조로만)
   확실하지 않으면 비워둔다 — 틀린 가격대를 보여주는 것보다 '가격 확인 필요'가 낫다.
   가격대 1=1만원 이하 · 2=1–2만원 · 3=2–3만원 · 4=3–5만원 · 5=5만원 이상"""
import json, re, sys
dry = '--dry' in sys.argv
h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
def nm(s): return re.sub(r'\s', '', s or '')
R = json.load(open('data/reels_parsed.json', encoding='utf-8'))
rp = {}
for r in R:
    if r.get('shop') and r.get('prices'):
        rp.setdefault(nm(r['shop']), []).extend(x['p'] for x in r['prices'] if x.get('p'))

def band(avg):
    for lim, b in ((10000, 1), (20000, 2), (30000, 3), (50000, 4)): 
        if avg <= lim: return b
    return 5
# 1인분 값이 아닌 것(2인 세트·모듬)은 빼고 본다
def from_prices(ps):
    ps = [x for x in ps if 3000 <= x <= 120000]
    if not ps: return None
    ps = sorted(ps)
    mid = ps[len(ps)//2]                      # 평균보다 중앙값이 덜 흔들린다
    return band(mid)

# 1인 식사 기준 — 대표메뉴(cat)를 먼저 보고, 없으면 분류(cats)로 본다
T1 = r'분식|떡볶이|김밥|만두|국수|칼국수|냉면|소바|우동|메밀|국밥|해장국|순대|백반|죽|토스트|샌드위치|제과|베이커리|빵|디저트|카페|커피|빙수|도넛|와플|간식|버거|찐빵|호두과자|케익|케이크'
T2 = r'돈까스|카츠|텐동|덮밥|카레|라멘|짬뽕|짜장|중식|중국|태국|베트남|아시아|퓨전|파스타|피자|양식|이탈리안|리조또|찌개|전골|두부|닭|치킨|족발|보쌈|수육|정식|한정식|주물럭|두루치기|비빔밥|돌솥'
T3 = r'육류|고기|삼겹|갈비|곱창|막창|양꼬치|장어|오리|회\b|해물|생선|수산|초밥|스시|이자카야|술집|호프|주점|포차|칵테일|와인|위스키|샤브|막걸리|맥주'
T4 = r'한우|오마카세|파인다이닝|코스요리|참치|대게|킹크랩|스테이크'
CATS_TIER = [({'카페','디저트'}, 1), ({'분식'}, 1), ({'고기'}, 3), ({'술집'}, 3),
             ({'일식'}, 2), ({'중식'}, 2), ({'양식'}, 2), ({'한식'}, 2)]

def guess(p):
    cats = set(p.get('cats') or [])
    if cats & {'체험', '나들이', '숙소', '쇼핑', '뷰티', '운동'}: return None, None
    cat = (p.get('cat') or '') + ' ' + p['n']
    b = why = None
    for pat, tier, label in ((T4, 4, '한우·오마카세'), (T1, 1, '면·분식·카페'), (T2, 2, '밥집·양식'), (T3, 3, '고기·회·술집')):
        if re.search(pat, cat): b, why = tier, label + ' 대표메뉴'; break
    if not b:
        for s2, tier in CATS_TIER:
            if cats & s2: b, why = tier, '/'.join(s2) + ' 분류'; break
    if not b: return None, None
    g = p.get('gprice') or ''
    if g == 'PRICE_LEVEL_INEXPENSIVE' and b > 1: b -= 1; why += ' + 구글 저렴'
    elif g == 'PRICE_LEVEL_VERY_EXPENSIVE': b = min(5, b + 2); why += ' + 구글 아주 비쌈'
    elif g == 'PRICE_LEVEL_EXPENSIVE': b = min(5, b + 1); why += ' + 구글 비쌈'
    return b, why

for p in P:                                   # 앞서 자동으로 넣은 값은 지우고 다시 계산
    if p.pop('budgetAuto', None): p.pop('budget', None)
filled, guessed, left, review = 0, 0, [], []
for p in P:
    if p.get('budget') or p.get('closed'): continue
    ps = list(rp.get(nm(p['n'])) or [])
    ps += [int(x.replace(',', '')) for x in re.findall(r'([\d,]{4,7})\s*원', p.get('v') or '')]
    b = from_prices(ps)
    if b:
        p['budget'] = b; filled += 1
        review.append({'n': p['n'], 'budget': b, 'why': '메뉴 가격 ' + '·'.join(f'{x:,}' for x in sorted(ps)[:4]), 'auto': False})
        continue
    b, why = guess(p)
    if not b: left.append(p['n']); continue
    p['budget'] = b; p['budgetAuto'] = True; guessed += 1
    review.append({'n': p['n'], 'budget': b, 'why': why, 'auto': True})
print(f'메뉴 가격으로 확정 {filled}곳 · 업종으로 추정 {guessed}곳 · 비워둠 {len(left)}곳')
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
    json.dump(review, open('data/budget-review.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
