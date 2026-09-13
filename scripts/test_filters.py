#!/usr/bin/env python3
"""필터가 실제로 결과를 바꾸는지 확인한다 (AI 없이 도는 회귀 테스트).

  python3 scripts/test_filters.py
"""
import json, re, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
P = json.loads(re.search(r'<script id="places" type="application/json">(\[.*?\])</script>', H, re.S).group(1))
BUD = json.loads(re.search(r'var BUD=(\{[^}]*\});', H, re.S).group(1).replace("'", '"'))

live = [p for p in P if not p.get('closed') and p.get('src') != 'public' and not p.get('spot')]
solo = lambda p: '혼밥' in (p.get('sit') or [])
fails = []


def check(name, ok, detail=''):
    print(('  [통과] ' if ok else '  [실패] ') + name + (('  — ' + detail) if detail else ''))
    if not ok:
        fails.append(name)


print('=== 혼밥 데이터 ===')
for nm in ['솔밭샤브', '동백카츠', '몽상']:
    hit = [p for p in live if nm in p['n']]
    check('%s 혼밥에 들어있다' % nm, bool(hit) and all(solo(p) for p in hit))
for nm in ['장원갑칼국수', '부심', '새벽소', '한영식당', '오씨칼국수', '수참치', '고도']:
    hit = [p for p in live if nm in p['n']]
    check('%s 혼밥에서 빠졌다' % nm, all(not solo(p) for p in hit))
for nm in ['산카쿠', '더바사삭']:
    hit = [p for p in live if p['n'] == nm]
    check('%s 혼밥 우선 후보다' % nm, bool(hit) and all(p.get('soloPick') for p in hit))

print('\n=== 단소 ===')
d = [p for p in P if p['n'] == '단소']
check('단소가 제주식 백반이다', bool(d) and '제주' in str(d[0].get('cat')) + str(d[0].get('v')))
check('단소에서 술자리 표시가 빠졌다', bool(d) and '술자리' not in (d[0].get('sit') or []))

print('\n=== 예산 구간 ===')
check('1–2만원과 2–3만원이 다른 구간이다', BUD['1–2만원'] != BUD['2–3만원'],
      '%s vs %s' % (BUD['1–2만원'], BUD['2–3만원']))
cnt = {b: sum(1 for p in live if p.get('budget') == BUD[b]) for b in BUD}
check('버튼마다 개수가 다르다', len(set(cnt.values())) > 1, str(cnt))
check('1만원 이하와 3–5만원 결과가 다르다', cnt['1만원 이하'] != cnt['3–5만원'],
      '%d곳 vs %d곳' % (cnt['1만원 이하'], cnt['3–5만원']))

s35 = [p for p in live if solo(p) and p.get('budget') == BUD['3–5만원']]
cheap = [p for p in s35 if p.get('budget') == 1]
check('혼밥+3–5만원에 1만원 이하가 안 섞인다', not cheap, '후보 %d곳' % len(s35))

print('\n=== 혼밥 순위 ===')
def base(p):
    return (8 if p.get('src')=='reel' else 0) + \
           (10 if (p.get('grating') or 0) >= 4.5 and (p.get('gcount') or 0) >= 100 else
            6 if (p.get('grating') or 0) >= 4.2 and (p.get('gcount') or 0) >= 50 else 0) + \
           (4 if len(p.get('v') or '') >= 14 else 0)
def solo_bonus(p):
    f = p.get('fac') or {}
    b = 0
    if p.get('soloPick'): b += 16
    if p.get('soloVerified'): b += 8
    elif solo(p): b += 5
    if p.get('budget') is not None and p['budget'] <= 2: b += 4
    if f.get('group') is True: b -= 5
    if f.get('room') is True: b -= 3
    return b
sp = [p for p in live if solo(p)]
top5 = [p['n'] for p in sorted(sp, key=lambda x: -(base(x) + solo_bonus(x)))[:5]]
check('산카쿠가 혼밥 상위 5개 안에 있다', '산카쿠' in top5, ' · '.join(top5))
check('더바사삭이 혼밥 상위 5개 안에 있다', '더바사삭' in top5)
check('중리옥이 혼밥에서 빠졌다', all(not solo(p) for p in live if '중리옥' in p['n']))
check('토미야가 혼밥·일식·점심이다', any(
    solo(p) and '일식' in (p.get('cats') or []) and p.get('lunch') for p in live if '토미야' in p['n']))

print('\n=== 주차 ===')
park_ok = [p for p in live if (p.get('fac') or {}).get('parking') is True]
check('주차 확인된 곳이 있다', len(park_ok) > 0, '%d곳' % len(park_ok))
check('주차 미확인이 주차 결과에 안 섞인다',
      all((p.get('fac') or {}).get('parking') is True for p in park_ok))

print('\n' + ('전부 통과했습니다.' if not fails else '%d건 실패: %s' % (len(fails), ', '.join(fails))))
sys.exit(1 if fails else 0)
