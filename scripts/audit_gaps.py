#!/usr/bin/env python3
"""내용이 빈약한 곳을 찾아 docs/빈약한-내용-점검.md 로 정리한다.   python3 scripts/audit_gaps.py
   - 매장별로 빠진 정보(영업시간·가격대·전화·사진·좌표·설명)
   - '이 가게로 하루 코스 짜기'를 눌렀을 때 코스가 안 나오거나 1개뿐인 곳
   - 동네별 코스가 가능한 동네와 부족한 동네"""
import json, re, math, collections
h = open('index.html', encoding='utf-8').read()
P = json.loads(re.search(r'<script id="places" type="application/json">(.*?)</script>', h, re.S).group(1))
T = json.loads(re.search(r'<script id="thumbs" type="application/json">\s*(\{[\s\S]*?\})\s*</script>', h).group(1))
P = [p for p in P if not p.get('closed')]
def ptype(p):
    c = p.get('cats') or []
    if '뷰티' in c or '운동' in c: return 'beauty'
    if '숙소' in c: return 'travel'
    if '쇼핑' in c or p.get('cat') in ('쇼핑', '아울렛'): return 'shop'
    if '체험' in c or '나들이' in c: return 'play'
    food = any(x in c for x in ['한식', '중식', '일식', '분식', '양식', '고기'])
    if not food and ('카페' in c or '디저트' in c): return 'cafe'
    if not food and '술집' in c: return 'bar'
    return 'rest'
def role(p):
    t = ptype(p); c = p.get('cats') or []
    if t == 'cafe': return '디저트' if '디저트' in c else '카페'
    if t == 'bar' or '술집' in c: return '한잔'
    if t == 'rest': return '밥'
    if t == 'play': return '놀기'
    return None
def km(a, b): return math.hypot((a['lng'] - b['lng']) * 88.8, (a['lat'] - b['lat']) * 111.1)
def dong(p): return str(p.get('area') or '').split(' ')[0]
def has_photo(p): return bool(p.get('ph') and T.get(p['ph'])) or bool(p.get('cover') and T.get(p['cover'])) or bool(p.get('gphotos'))
# 1) 매장별 빠진 정보
rows = []
for p in P:
    miss = []
    if not p.get('hours') and not p.get('ghours'): miss.append('영업시간')
    if not p.get('budget') and ptype(p) in ('rest', 'cafe', 'bar'): miss.append('가격대')
    if not p.get('phone'): miss.append('전화')
    if not has_photo(p): miss.append('사진')
    if not p.get('lat'): miss.append('좌표')
    v = p.get('v') or ''
    if len(v) < 8 or '‼' in v or '❗' in v or v.endswith('!'): miss.append('설명(짧거나 릴스 후킹 문구)')
    if not p.get('sit'): miss.append('상황태그')
    if miss: rows.append((len(miss), p['n'], p.get('area'), p.get('src'), miss))
rows.sort(key=lambda r: (-r[0], r[1]))
cnt = collections.Counter(x for r in rows for x in r[4])
# 2) 가게별 하루 코스
pool = [p for p in P if p.get('src') != 'public' and p.get('lat') and role(p)]
def courses(anchor):
    near = [x for x in pool if x is not anchor and km(x, anchor) <= 1.3]
    by = lambda r: [x for x in near if role(x) == r]
    ar = role(anchor)
    rests = [anchor] if ar == '밥' else by('밥')
    cafes = [anchor] if ar in ('카페', '디저트') else by('카페') + by('디저트')
    bars = [anchor] if ar == '한잔' else by('한잔')
    plays = [anchor] if ar == '놀기' else by('놀기')
    out = []; used = set()
    for r in rests[:6]:
        if len(out) >= 3: break
        def pick(L):
            best = None
            for x in L:
                if x is r or x['n'] in used or km(x, r) > 1.3: continue
                if not best or km(x, r) < km(best, r): best = x
            return best
        legs = [x for x in (pick(cafes), pick(plays), r, pick(bars)) if x]
        if len(legs) < 2: continue
        used.update(x['n'] for x in legs); out.append(legs)
    return out
thin = []
for p in pool:
    n = len(courses(p))
    if n == 0: thin.append((n, p['n'], dong(p), role(p), p.get('src')))
thin.sort(key=lambda r: (r[0], r[2]))
# 3) 동네별 재료
dc = collections.defaultdict(collections.Counter)
for p in pool:
    d = dong(p)
    if re.search(r'동$|읍$|면$', d): dc[d][role(p)] += 1
weak = [(d, c) for d, c in dc.items() if sum(c.values()) >= 4 and (c['밥'] == 0 or (c['카페'] + c['디저트']) == 0)]
small = [(d, c) for d, c in dc.items() if 2 <= sum(c.values()) < 4]
L = ['# 빈약한 내용 점검', '', f'매장 {len(P)}곳 기준 (폐업 제외). `python3 scripts/audit_gaps.py` 로 다시 만들 수 있다.', '',
     '## 1. 빠진 정보 개수', '']
for k, v in cnt.most_common(): L.append(f'- {k}: {v}곳')
L += ['', '## 2. 빠진 게 많은 매장 (3개 이상)', '']
for c, n, a, s, miss in rows:
    if c >= 3: L.append(f"- **{n}** ({a or '?'}, {'👑' if s == 'reel' else '로컬'}) — {' · '.join(miss)}")
L += ['', f'## 3. "이 가게로 하루 코스 짜기"가 안 되는 곳 ({len(thin)}곳)', '', '근처 1.3km 안에 밥·카페·술집 짝이 없어서 그렇다. 그 동네 매장을 더 넣으면 풀린다.', '']
for n, name, d, r, s in thin: L.append(f"- {name} ({d}, {r}) — 코스 {n}개")
L += ['', '## 4. 동네별 코스 재료', '', '동네 코스는 매장 4곳 이상인 동네만 뜬다. 밥·카페 둘 중 하나가 없는 동네:', '']
for d, c in sorted(weak, key=lambda x: -sum(x[1].values())): L.append(f"- {d}: " + ' · '.join(f'{k} {v}' for k, v in c.items()))
L += ['', '4곳이 안 돼서 동네 코스에 못 뜨는 동네 (2–3곳):', '']
for d, c in sorted(small, key=lambda x: -sum(x[1].values())): L.append(f"- {d}: " + ' · '.join(f'{k} {v}' for k, v in c.items()))
open('docs/빈약한-내용-점검.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print('\n'.join(L[:12])); print('...'); print(f'코스 빈약 {len(thin)}곳 · 저장: docs/빈약한-내용-점검.md')
