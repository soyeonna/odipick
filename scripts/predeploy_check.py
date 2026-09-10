#!/usr/bin/env python3
"""배포 전 자동 점검.  python3 scripts/predeploy_check.py
   문제가 있으면 목록을 보여주고 1을 돌려준다 (배포 스크립트에서 막을 수 있게)."""
import json, re, sys, math, collections
h = open('index.html', encoding='utf-8').read()
P = [p for p in json.loads(re.search(r'<script id="places" type="application/json">(.*?)</script>', h, re.S).group(1)) if not p.get('closed')]
T = json.loads(re.search(r'<script id="thumbs" type="application/json">\s*(\{[\s\S]*?\})\s*</script>', h).group(1))
DJ = (36.15, 36.55, 127.20, 127.60); NEAR = (35.80, 37.05, 126.20, 128.20)
def inbox(la, lo, b): return b[0] <= la <= b[1] and b[2] <= lo <= b[3]
def nn(s): return re.sub(r'\s', '', s or '')
FOOD = {'한식','중식','일식','분식','양식','고기','술집','카페','디저트'}
BAD = re.compile(r'^(교육|부동산|가정,생활|의료|금융)')
# 릴스에서 뽑아둔 가게 목록 — 공주픽 근거 확인용
_REELS = set()
try:
    for _r in json.load(open('data/reels_parsed.json', encoding='utf-8')):
        if _r.get('shop'): _REELS.add(re.sub(r'\s', '', _r['shop']))
except Exception:
    pass
def _in_reels(name):
    k = re.sub(r'\s', '', name or '')
    return bool(k) and any(k in s or s in k for s in _REELS)

# 설명 문구가 '-한다' 반말로 끝나면 잡는다 (사이트 말투는 '-요' 로 통일)
BANMAL_END = re.compile(r'(다|음|함|됨|임|짐)$')
BANMAL_OK = re.compile(r'(요|죠)$')
def _banmal(text):
    for seg in re.split(r'\s+·\s+', str(text or '')):
        seg = seg.strip()
        if not seg or re.search(r'\d[\d,]*\s*원', seg) or BANMAL_OK.search(seg): continue
        if BANMAL_END.search(seg): return seg[:30]
    return None

HOOK = re.compile(r'[‼❗️🔥💖🤍]|!!|!$|공유|저장하기|태그|팔로우|이벤트|미쳤|실화|주목|등장|떴|찾음|최초|레전드|역대급|난리|대란|무조건|찐맛집')
bad = collections.OrderedDict()
def add(k, v): bad.setdefault(k, []).append(v)

for p in P:
    box = NEAR if p.get('gu') == '대전근교' else DJ
    if p.get('lat') and not inbox(p['lat'], p['lng'], box): add('대전에서 먼 좌표', p['n'])
    if p.get('travel') and (p.get('gu') == '대전근교' or (p.get('lat') and not inbox(p['lat'], p['lng'], DJ))):
        add('대전여행인데 대전 밖', p['n'])
    if p.get('src') == 'reel' and not (p.get('ig') or p.get('igs') or p.get('ph') or _in_reels(p['n'])):
        add('공주픽인데 릴스 근거 없음', p['n'])
    if FOOD & set(p.get('cats') or []) and p.get('kcat') and BAD.match(p['kcat']): add('엉뚱한 업종 연결', p['n'])
    for _k in ('v', 'combo', 'sig'):
        _b = _banmal(p.get(_k))
        if _b: add('반말 문구', p['n'] + f'({_k}) {_b}')
    for _k in ('v', 'sig', 'tip', 'combo'):
        if isinstance(p.get(_k), str) and HOOK.search(p[_k]): add('릴스 문구 남음', p['n'] + f'({_k})')
    if not (p.get('v') or '').strip(): add('설명 없음', p['n'])
    if not p.get('sit'): add('상황 태그 없음', p['n'])
    if not p.get('lat'): add('좌표 없음', p['n'])
    if not p.get('phone'): add('전화 없음', p['n'])
    if not p.get('hours') and not p.get('ghours'): add('영업시간 없음', p['n'])
    if not (any(T.get(p.get(k)) for k in ('cover','cv','ig','ph')) or (p.get('gpl') and T.get(p['gpl'][0]))): add('사진 없음', p['n'])
    if not p.get('budget') and (FOOD & set(p.get('cats') or [])): add('가격대 없음', p['n'])
for key, label in (('n', '이름'), ('kid', '카카오번호'), ('ig', '릴스번호'), ('gid', '구글장소')):
    c = collections.Counter(nn(p.get(key)) for p in P if p.get(key))
    for k, v in c.items():
        if v > 1: add(f'{label} 중복', k)
# 화면 동작 (코드에 있어야 할 것들)
for pat, label in [(r'class="shback"', '팝업 뒤로 버튼'), (r'\.mapover\{[^}]*z-index', '지도 필터가 지도 위'),
                   (r'function hashFor', '새로고침 화면 유지'), (r'function spread', '추천 다양성')]:
    if not re.search(pat, h): add('화면 기능 빠짐', label)

HARD = {'릴스 문구 남음', '대전에서 먼 좌표', '대전여행인데 대전 밖', '엉뚱한 업종 연결', '이름 중복', '카카오번호 중복', '릴스번호 중복', '구글장소 중복', '화면 기능 빠짐', '공주픽인데 릴스 근거 없음'}
fail = False
print(f'점검 대상 {len(P)}곳')
for k, v in bad.items():
    mark = '✖' if k in HARD else '·'
    if k in HARD: fail = True
    print(f' {mark} {k}: {len(v)}건' + (' — ' + ', '.join(v[:8]) + ('…' if len(v) > 8 else '') if k in HARD or len(v) <= 8 else ''))
L = ['# 배포 전 점검', '', f'매장 {len(P)}곳 · `python3 scripts/predeploy_check.py` 로 다시 만든다.', '']
for k, v in bad.items():
    L.append(f'## {k} ({len(v)}건)'); L.append('')
    L += [f'- {x}' for x in v]; L.append('')
open('docs/배포전-점검.md', 'w', encoding='utf-8').write('\n'.join(L))
print('자세한 목록: docs/배포전-점검.md')
sys.exit(1 if fail else 0)
