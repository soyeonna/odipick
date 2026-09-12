#!/usr/bin/env python3
"""'데이트' 태그를 원칙대로 다시 매긴다.
   지금은 161곳이라 아무 데나 데이트로 나온다. 노포·포차·곱창집이 소개팅 결과에 끼는 게 문제.

   데이트로 보는 곳
     - 분위기 태그가 있는 곳 (예쁜·조용한·고급스러운·테라스·이국적·뷰맛집·아늑한)
     - 카페·디저트·양식, 와인바·칵테일바·이자카야·스시·오마카세·파스타·브런치
     - 소연님이 릴스에서 데이트로 소개한 곳(rank_date)은 무조건 유지
   데이트에서 빼는 곳
     - 노포
     - 포차·실비·막창·곱창·뭉티기·순대·국밥·해장·족발·보쌈·시장·호프·통닭·닭발·양푼·뒷고기·수산시장
   python3 scripts/fix_date_tag.py --dry
"""
import json, re, sys

MOOD = re.compile(r'예쁜|조용한|고급스러운|이국적|뷰맛집|아늑한')   # 테라스만으로는 데이트가 아니다 (야장도 테라스다)
YES  = re.compile(r'와인|칵테일|이자카야|스시|오마카세|파스타|스테이크|브런치|다이닝|비스트로|재즈')
NO   = re.compile(r'포차|실비|막창|곱창|뭉티기|순대|국밥|해장|족발|보쌈|시장|호프|통닭|닭발|양푼|뒷고기|수산|밀면|분식|기사식당|백반|구이|숯불|정육|고깃집|삼겹|갈비|주물럭|무한리필')

h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
dry = '--dry' in sys.argv

def fits(p):
    cs = set(p.get('cats') or [])
    hay = p['n'] + ' ' + (p.get('cat') or '') + ' ' + (p.get('kcat') or '')
    if p.get('rank_date'): return True            # 소연님이 정한 데이트 순위는 건드리지 않는다
    if p.get('yajang'): return False              # 야장은 분위기 좋아도 데이트 자리는 아니다
    if '노포' in cs: return False
    if NO.search(hay): return False
    if MOOD.search(' '.join(p.get('mood') or [])): return True
    if cs & {'카페', '디저트', '양식'}: return True
    if YES.search(hay): return True
    return False

add, rm = [], []
for p in P:
    if p.get('closed') or p.get('src') == 'public' or p.get('spot'): continue   # 명소는 따로 관리
    s = set(p.get('sit') or [])
    ok = fits(p)
    if '데이트' in s and not ok:
        rm.append(p['n'])
        if not dry: p['sit'] = sorted(s - {'데이트'})
    elif '데이트' not in s and ok and (p.get('cats') or []):
        add.append(p['n'])
        if not dry: p['sit'] = sorted(s | {'데이트'})
now = len([p for p in P if '데이트' in (p.get('sit') or []) and not p.get('closed')])
print(f'데이트 뺀 곳 {len(rm)} · 넣은 곳 {len(add)} · 최종 {now if dry is False else "(미리보기)"}')
print('\n[뺌]', ' · '.join(rm))
print('\n[넣음]', ' · '.join(add))
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
