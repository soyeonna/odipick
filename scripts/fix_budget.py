#!/usr/bin/env python3
"""구글이 매긴 가격대 중 '그 종류면 대체로 이 값' 인 것만 남기고 나머지는 비운다.
   비운 곳은 화면에 '가격 확인 필요' 로 나온다. 추정 표시(budgetAuto)는 아예 없앤다.
   1=1만원 이하 · 2=1–2만원 · 3=2–3만원 · 4=3–5만원 · 5=5만원 이상
   python3 scripts/fix_budget.py --dry   # 미리보기
"""
import json, re, sys

# 위에서부터 먼저 걸리는 종류로 판정한다. 고깃집도 cats 에 '한식'이 있어 순서가 중요하다.
BAND = [('한우·오마카세', r'한우|오마카세|참치|스시|초밥', (3, 5)),
        ('횟집·해산물·장어', r'횟집|회$|회·|해산물|수산|해물|장어|대게|킹크랩', (2, 5)),
        ('고기·구이', r'고기|갈비|삼겹|막창|곱창|구이|뒷고기|족발|보쌈', (2, 4)),
        ('치킨·닭', r'치킨|닭|통닭', (1, 3)),
        ('술집·포차', r'술집|포차|호프|주점|칵테일|와인|이자카야', (1, 3)),
        ('카페·디저트·빵', r'카페|디저트|베이커리|빵|케이크|제과|아이스크림', (1, 2)),
        ('분식', r'분식|떡볶|김밥|만두', (1, 1)),
        ('중식', r'중식|짬뽕|중국', (1, 2)),
        ('일식·양식', r'일식|돈까스|우동|라멘|양식|파스타|피자', (1, 3)),
        ('한식·국밥·칼국수', r'한식|국밥|칼국수|국수|냉면|순대|백반|찌개|탕', (1, 2))]

def kind(p):
    s = (p.get('cat') or '') + ' ' + ' '.join(p.get('cats') or [])
    for name, pat, band in BAND:
        if re.search(pat, s): return name, band
    return None, None

h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
dry = '--dry' in sys.argv
keep, clear = [], []
for p in P:
    if not p.get('budgetAuto'): continue
    k, band = kind(p)
    b = p.get('budget')
    if k and b and band[0] <= b <= band[1]:
        keep.append((p['n'], k, b))
    else:
        clear.append((p['n'], k or '분류없음', b))
        if not dry: p['budget'] = None
    if not dry: p.pop('budgetAuto', None)
print(f'그대로 두는 값 {len(keep)}곳 · 비우는 값 {len(clear)}곳')
print('\n[비우는 곳]')
for n, k, b in clear: print(f'  {n} ({k}) — {b}단계였음')
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
