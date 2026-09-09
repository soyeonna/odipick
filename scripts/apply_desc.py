#!/usr/bin/env python3
"""data/desc/*.json 에 적어둔 소개 문구를 매장에 반영한다.  python3 scripts/apply_desc.py
   메뉴 가격은 v 에 그대로 두고(카드에서 따로 보여줌), 앞부분 설명만 바꾼다."""
import json, re, glob
h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
D = {}
for f in sorted(glob.glob('data/desc/*.json')):
    D.update(json.load(open(f, encoding='utf-8')))
CATFIX = {'리틀아우': (['쇼핑'], '캐릭터 굿즈'), '워크업': (['쇼핑'], '옷가게'),
          '고릴라캠핑': (['쇼핑'], '캠핑용품'), '나만의휴일': (['뷰티'], '세신·바디관리')}
hit, price_kept = 0, 0
for p in P:
    if p['n'] not in D: continue
    old = str(p.get('v') or '')
    prices = [s.strip() for s in old.split('·') if re.search(r'\d[\d,]*\s*원', s)]
    p['v'] = D[p['n']] + (' · ' + ' · '.join(prices) if prices else '')
    p['vSrc'] = '리뷰 요약'
    if prices: price_kept += 1
    if p['n'] in CATFIX:
        p['cats'], p['cat'] = CATFIX[p['n']][0], CATFIX[p['n']][1]
    hit += 1
print(f'설명 반영 {hit}곳 (메뉴 가격 유지 {price_kept}곳)')
miss = [n for n in D if not any(p['n'] == n for p in P)]
if miss: print('못 찾은 이름:', ', '.join(miss))
h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
open('index.html', 'w', encoding='utf-8').write(h)
