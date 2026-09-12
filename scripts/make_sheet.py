#!/usr/bin/env python3
"""매장 전체를 소연님이 눈으로 훑을 수 있게 번호 붙은 점검표로 만든다.
   docs/전체점검표.md 로 저장. 번호만 말씀해주시면 고칠 수 있게 하는 것이 목적.
   python3 scripts/make_sheet.py
"""
import json, re, collections

h = open('index.html', encoding='utf-8').read()
P = json.loads(re.search(r'<script id="places" type="application/json">(.*?)</script>', h, re.S).group(1))
A = [p for p in P if not p.get('closed')]

GU = ['중구', '서구', '유성구', '동구', '대덕구']
BUD = {1: '1만원 이하', 2: '1–2만원', 3: '2–3만원', 4: '3–5만원', 5: '5만원 이상'}   # 화면 표기와 같게

# 한줄평이 알맹이 없는 복붙인지
FLAT = re.compile(r'^현지인들이 인정하는|^대전의 (?:맛집|카페)$|^맛있는 |^유명한 ')

def needs_budget(p):
    """화면의 needsBudget 과 같은 기준. 공원·미술관·공방은 '한 끼 얼마'가 어울리지 않는다"""
    c = p.get('cats') or []
    if p.get('spot'): return False
    for x in ('뷰티', '운동', '숙소', '쇼핑', '체험', '나들이'):
        if x in c: return False
    if p.get('cat') in ('쇼핑', '아울렛'): return False
    return True

def budget_txt(p):
    b = p.get('budget')
    if not needs_budget(p): return '가격 안 씀'
    if not b: return '❓없음'
    t = BUD[b]
    return t + '(추정)' if p.get('budgetAuto') else t

def flags(p):
    f = []
    v = p.get('v') or ''
    if not v: f.append('한줄평없음')
    elif FLAT.match(v) or len(v) < 10: f.append('한줄평빈약')
    if needs_budget(p):
        if not p.get('budget'): f.append('가격없음')
        elif p.get('budgetAuto'): f.append('가격추정')
    if not p.get('hours'): f.append('시간없음')
    if not p.get('phone'): f.append('전화없음')
    if p.get('spot'): f = [x for x in f if x not in ('전화없음', '시간없음')]
    if not (p.get('grating') or p.get('src') == 'reel'): f.append('근거약함')
    elif p.get('src') != 'reel' and (p.get('gcount') or 0) < 10: f.append('리뷰10개미만')
    if p.get('grating') and p['grating'] < 3.9 and (p.get('gcount') or 0) > 100: f.append('평점낮음')
    return f

rows, i = [], 0
for gu in GU:
    g = [p for p in A if p.get('gu') == gu]
    g.sort(key=lambda p: ((p.get('area') or '').split()[0], p['n']))
    rows.append((gu, []))
    for p in g:
        i += 1
        rows[-1][1].append((i, p, flags(p)))

out = ['# 오디픽 전체 점검표', '',
       f'매장 **{len(A)}곳** 전부입니다. 구 → 동네 순으로 묶었어요.',
       '',
       '**읽는 법**', '',
       '`번호. 가게이름 | 동네 | 가격대 | 종류 | 한줄평` 순서입니다.',
       '`👑` 는 대전공주 릴스에 나온 곳, `(추정)` 은 구글이 매긴 값을 그대로 쓴 가격입니다.',
       '뒤에 `⚠` 로 표시한 것은 제가 보기에 손볼 데가 있는 곳이에요.', '',
       '**알려주실 때** — 번호만 적어주세요.', '',
       '```', '17 빼기', '42 가격 3만원대', '88 종류 술집아니라 한식', '103 한줄평 이상함', '```', '',
       '---', '']

# 먼저 볼 것
pri = collections.OrderedDict([
    ('한줄평이 비었거나 알맹이 없는 곳', lambda f: '한줄평없음' in f or '한줄평빈약' in f),
    ('가격대가 아예 없는 곳', lambda f: '가격없음' in f),
    ('리뷰도 없고 릴스에도 없어 근거가 약한 곳', lambda f: '근거약함' in f),
    ('리뷰가 많은데 평점이 낮은 곳 (호불호 갈림)', lambda f: '평점낮음' in f),
])
out += ['# 먼저 봐주시면 좋은 것', '',
        '전체를 다 못 보시면 이 번호들만 봐주세요.', '']
allrows = [r for _, rs in rows for r in rs]
for title, test in pri.items():
    hit = [r for r in allrows if test(r[2])]
    out.append(f'### {title} — {len(hit)}곳')
    out.append('')
    out.append(' · '.join(f'**{n}**.{p["n"]}' for n, p, _ in hit) or '없음')
    out.append('')
# 가격대를 종류별로 보여준다. 168곳 목록을 읽는 건 사람이 못 할 일이라 규칙으로 고치게 한다
KIND = [('고기·구이', r'고기|갈비|삼겹|막창|곱창|구이|한우'), ('횟집·해산물', r'회|해산물|수산|초밥|스시'),
        ('한식·국밥·칼국수', r'한식|국밥|칼국수|국수|냉면|분식|떡볶'), ('중식', r'중식|짬뽕|중국'),
        ('일식·양식', r'일식|돈까스|양식|파스타|피자'), ('카페·디저트·빵', r'카페|디저트|베이커리|빵|케이크'),
        ('술집·포차', r'술집|포차|바|호프|주점')]
def kind_of(p):
    s2 = (p.get('cat') or '') + ' ' + ' '.join(p.get('cats') or [])
    for name, pat in KIND:
        if re.search(pat, s2): return name
    return '그 외'
auto = [r for r in allrows if '가격추정' in r[2]]
out += ['# 가격대 — 구글 추정값 %d곳' % len(auto), '',
        '구글은 "저렴/보통/비쌈" 네 단계만 줍니다. 그래서 **한 곳씩 보는 대신 종류별로** 정리했어요.',
        '아래 표에서 **"이 종류는 전부 ○단계로"** 라고만 말씀해주시면 한번에 고칩니다.', '',
        '| 종류 | 1만원 이하 | 1–2만원 | 2–3만원 | 3–5만원 | 5만원↑ |', '|---|---|---|---|---|---|']
for name, _ in KIND + [('그 외', '')]:
    g = [r for r in auto if kind_of(r[1]) == name]
    if not g: continue
    cells = []
    for b in (1, 2, 3, 4, 5):
        k = [r for r in g if r[1].get('budget') == b]
        cells.append(str(len(k)) + '곳' if k else '—')
    out.append('| **%s** (%d곳) | %s |' % (name, len(g), ' | '.join(cells)))
out.append('')

# 대놓고 이상해 보이는 조합
ODD = [('고기·구이인데 1만원 이하', lambda p: kind_of(p) == '고기·구이' and p.get('budget') == 1),
       ('횟집·해산물인데 1만원 이하', lambda p: kind_of(p) == '횟집·해산물' and p.get('budget') == 1),
       ('카페·디저트인데 2–3만원 이상', lambda p: kind_of(p) == '카페·디저트·빵' and (p.get('budget') or 0) >= 3),
       ('한식·분식인데 3–5만원 이상', lambda p: kind_of(p) == '한식·국밥·칼국수' and (p.get('budget') or 0) >= 4)]
out += ['### 이 조합은 제가 봐도 이상합니다', '']
for title, test in ODD:
    hit = [r for r in auto if test(r[1])]
    if not hit: continue
    out.append('**%s** — %s' % (title, ' · '.join('**%d**.%s' % (n, p['n']) for n, p, _ in hit)))
    out.append('')
out += ['---', '']

for gu, rs in rows:
    out += [f'# {gu} — {len(rs)}곳', '']
    dong = None
    for n, p, f in rs:
        d = (p.get('area') or '').split()[0] or '동네미정'
        if d != dong:
            dong = d
            out += ['', f'**{d}**', '']
        crown = '👑' if p.get('src') == 'reel' else ''
        v = (p.get('v') or '').split(' · ')[0]
        tag = ' ⚠' + ','.join(f) if f else ''
        out.append(f'{n}. {crown}**{p["n"]}** | {budget_txt(p)} | {p.get("cat") or "?"} | {v or "(한줄평 없음)"}{tag}')
    out.append('')

open('docs/전체점검표.md', 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print(f'{len(A)}곳 · docs/전체점검표.md')
for title, test in pri.items():
    print(f'  {title}: {len([r for r in allrows if test(r[2])])}곳')
