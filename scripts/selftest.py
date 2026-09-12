#!/usr/bin/env python3
"""오디픽 자가진단 — 사람이 눌러보지 않아도 잡히는 오류를 한 번에 확인한다.

  python3 scripts/selftest.py

AI를 전혀 쓰지 않으므로 몇 번을 돌려도 요금이 들지 않는다.
문제가 하나도 없으면 '이상 없음'만 찍고 끝난다.
"""
import json, re, os, sys
from collections import Counter, defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()

def jblock(idname):
    m = re.search(r'<script id="%s" type="application/json">(.*?)</script>' % idname, H, re.S)
    return json.loads(m.group(1)) if m else None

def jvar(name):
    m = re.search(r'var %s\s*=\s*(\{.*?\});' % name, H, re.S)
    return json.loads(m.group(1)) if m else None

P     = jblock('places') or []
SHAPE = jvar('GU_SHAPES') or {}
PROJ  = jvar('GU_PROJ') or {}

problems = []   # (심각도, 제목, 자세히)
def bad(t, d):  problems.append(('심각', t, d))
def warn(t, d): problems.append(('확인', t, d))

# ── 1. 지도: 핀이 자기 구 안에 찍히나 ─────────────────────────
def pts(d): return [tuple(map(float, m)) for m in re.findall(r'([-\d.]+),([-\d.]+)', d)]
def inside(p, poly):
    x, y = p; n = len(poly); c = False; j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi): c = not c
        j = i
    return c

if SHAPE and PROJ:
    polys = {g: pts(d) for g, d in SHAPE.items()}
    off = defaultdict(list)
    tested = 0
    for p in P:
        if not (p.get('lat') and p.get('gu')) or p['gu'] == '대전근교':
            continue
        tested += 1
        x = (p['lng'] - PROJ['minx']) * PROJ['sx'] * PROJ['cos']
        y = PROJ['h'] - (p['lat'] - PROJ['miny']) * PROJ['sx']
        hit = [g for g in polys if inside((x, y), polys[g])]
        if hit and p['gu'] not in hit:
            off[(p['gu'], hit[0])].append(p['n'])
    n_off = sum(len(v) for v in off.values())
    if tested and n_off / tested > 0.05:
        lines = ['%s 로 돼있는데 지도에선 %s 자리 : %d곳 (예: %s)'
                 % (a, b, len(v), ', '.join(v[:3])) for (a, b), v in
                 sorted(off.items(), key=lambda kv: -len(kv[1]))[:6]]
        bad('지도 구 경계가 실제와 안 맞음',
            ['%d곳 중 %d곳(%.0f%%)이 엉뚱한 구 영역에 찍힙니다.' % (tested, n_off, n_off / tested * 100)] + lines)

# ── 2. 공주픽에 릴스가 연결돼 있나 ─────────────────────────────
# 뱃지 자체는 src='reel' 로 붙으므로 이건 신뢰도 문제가 아니다.
# 릴스 코드가 없으면 '이 가게 릴스 보기' 버튼과 커버 사진이 안 나온다.
noig = [p['n'] for p in P if p.get('src') == 'reel' and not (p.get('ig') or p.get('igs'))]
if noig:
    warn('공주픽인데 릴스가 연결 안 된 곳',
         ['%d곳 — 상세화면에 "이 가게 릴스 보기" 버튼이 안 나옵니다.' % len(noig),
          ', '.join(noig[:6]) + (' 외' if len(noig) > 6 else '')])

# ── 3. 폐업인데 아직 보이는지 / 폐업 표시 상태 ────────────────
closed = [p for p in P if p.get('closed')]
unconfirmed = [p['n'] for p in closed if not p.get('closedConfirmed') and not p.get('closedWhy')]
if unconfirmed:
    warn('폐업으로 내려놨는데 근거가 안 적힌 곳',
         ['%d곳 — %s' % (len(unconfirmed), ', '.join(unconfirmed[:6]))])

# ── 4. 검색·필터가 걸릴 만한 빈 값 ───────────────────────────
live = [p for p in P if not p.get('closed') and p.get('src') != 'public']
nolat = [p['n'] for p in live if not p.get('lat')]
if nolat:
    warn('좌표가 없어 지도·코스에서 빠지는 곳', ['%d곳 — %s' % (len(nolat), ', '.join(nolat[:6]))])
nocat = [p['n'] for p in live if not p.get('cat')]
if nocat:
    warn('분류가 비어 검색에 안 걸리는 곳', ['%d곳 — %s' % (len(nocat), ', '.join(nocat[:6]))])

dup = [n for n, c in Counter(p['n'] for p in live).items() if c > 1]
if dup:
    warn('이름이 겹치는 가게', ['%d개 — %s' % (len(dup), ', '.join(dup[:6]))])

# ── 5. 돌림판·코스가 돌아갈 만큼 후보가 있나 ──────────────────
pool = [p for p in live if p.get('lat')]
if len(pool) < 30:
    bad('돌림판·코스 후보가 너무 적음', ['현재 %d곳 — 30곳 밑이면 같은 집만 계속 나옵니다.' % len(pool)])
by_gu = Counter(p.get('gu') for p in pool if p.get('gu'))
thin = ['%s %d곳' % (g, c) for g, c in by_gu.items() if c < 10]
if thin:
    warn('그 지역만 고르면 결과가 거의 없는 구', [', '.join(thin) + ' — 지역 필터를 쓰면 허전해 보입니다.'])

# ── 6. 링크 ────────────────────────────────────────────────
httpish = [p['n'] for p in live if str(p.get('kurl') or '').startswith('http://')]
if httpish:
    warn('보안 없는 주소(http)로 된 지도 링크',
         ['%d곳 — 화면에서는 https 로 바꿔 내보내고 있지만, 데이터도 정리해두면 좋습니다.' % len(httpish)])

# ── 7. 상세화면이 얼마나 비어 보이나 ─────────────────────────
n = len(live) or 1
for key, label in [('reserve', '예약'), ('group', '단체석'), ('pet', '반려동물')]:
    miss = sum(1 for p in live if (p.get('fac') or {}).get(key) is None)
    if miss / n > 0.5:
        warn('%s 정보가 거의 비어 있음' % label,
             ['%d곳 중 %d곳(%.0f%%)이 값 없음 — 상세화면이 허전해 보입니다.' % (n, miss, miss / n * 100)])

# ── 결과 ───────────────────────────────────────────────────
print('=' * 46)
print('오디픽 자가진단   ·   가게 %d곳 검사' % len(P))
print('=' * 46)
if not problems:
    print('\n이상 없음.')
    sys.exit(0)

for level in ('심각', '확인'):
    rows = [p for p in problems if p[0] == level]
    if not rows:
        continue
    print('\n■ %s %d건' % ('바로 고쳐야 할 것' if level == '심각' else '확인해두면 좋은 것', len(rows)))
    for _, title, detail in rows:
        print('\n  · ' + title)
        for d in detail:
            print('      ' + d)

print('\n(이 검사는 AI를 쓰지 않아 몇 번을 돌려도 요금이 들지 않습니다.)')
sys.exit(1 if any(p[0] == '심각' for p in problems) else 0)
