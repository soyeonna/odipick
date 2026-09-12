#!/usr/bin/env python3
"""'양식/일식/고기/분식/술집' 처럼 종류 표기가 길게 나열된 곳을 짧게 바꾼다.
   카카오 업종 분류를 앞세우고, 없으면 대표 종류 하나만 남긴다.
   python3 scripts/fix_cats.py --dry   # 미리보기
   python3 scripts/fix_cats.py         # 적용
"""
import json, re, sys

LEAD = [('고기', '고깃집'), ('카페', '카페'), ('디저트', '디저트'), ('일식', '일식'),
        ('중식', '중식'), ('양식', '양식'), ('분식', '분식'), ('술집', '술집'), ('한식', '한식')]
SHORT = {'호프·요리주점': '술집', '실내포장마차': '포차', '제과·베이커리': '베이커리',
         '해물·생선': '해물', '육류·고기': '고깃집', '곱창·막창': '곱창·막창'}

def clean(p):
    nm = re.sub(r'\s', '', p['n'])
    base = (p.get('kcat') or '').split('>')[-1].strip().replace(',', '·')
    b2 = re.sub(r'\s', '', base)
    # 업종 대신 가게 이름이 들어간 경우(예: '덕수파스타')는 버린다
    if base in ('음식점', '기타', '') or (b2 and b2 in nm and len(b2) / len(nm) > 0.6):
        base = ''
    base = SHORT.get(base, base)
    if '육류' in base: base = '고깃집'
    cs = p.get('cats') or []
    lead = next((lab for c, lab in LEAD if c in cs), '')
    # 카카오 업종이 있으면 그것만 쓴다. 화면에 보이는 글자이므로 짧을수록 좋다
    if base: lead = ''
    return (base + '·' + lead).strip('·') if (base and lead) else (base or lead or p.get('cat'))

h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
ch = []
for p in P:
    if (p.get('cat') or '').count('/') < 2 or p.get('closed'): continue
    new = clean(p)
    if new and new != p['cat']:
        ch.append((p['n'], p['cat'], new))
        if '--dry' not in sys.argv: p['cat'] = new
print(f'종류 표기 정리 {len(ch)}곳')
for n, o, w in ch: print(f'  {n} : {o} → {w}')
if '--dry' not in sys.argv:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
