#!/usr/bin/env python3
"""같은 매장이 두 번 들어간 것을 하나로 합친다.  python3 scripts/merge_dups.py
   합칠 때 정보가 더 많은 쪽을 남기고, 빠진 값만 다른 쪽에서 채운다."""
import json, re
h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
# (남길 이름, 없앨 이름) — 확인한 것만 손으로 지정한다
PAIRS = [('손의손', '손의손'),                       # 둔산동 본점만 남긴다 (봉명점은 같은 릴스의 다른 지점)
         ('대전칼국수족발', '칼국수족발쭈꾸미볶음'),
         ('약방카레', '카레약방'),
         ('와타요업', '와타요업 갈마본점')]
def richer(a, b): return a if len(json.dumps(a, ensure_ascii=False)) >= len(json.dumps(b, ensure_ascii=False)) else b
removed = []
# 손의손: 같은 이름이라 동네로 구분
sons = [p for p in P if p['n'] == '손의손']
if len(sons) == 2:
    keep = next((p for p in sons if str(p.get('area','')).startswith('둔산')), sons[0])
    drop = [p for p in sons if p is not keep][0]
    for k, v in drop.items(): keep.setdefault(k, v)
    P.remove(drop); removed.append(('손의손 (봉명점)', '손의손 (둔산동 본점)'))
for keepn, dropn in PAIRS[1:]:
    ks = [p for p in P if p['n'] == keepn]; ds = [p for p in P if p['n'] == dropn]
    if not ks or not ds: continue
    keep, drop = ks[0], ds[0]
    if keep is drop: continue
    for k, v in drop.items():
        if k != 'n': keep.setdefault(k, v)
    P.remove(drop); removed.append((dropn, keepn))
print(f'합친 매장 {len(removed)}건')
for d, k in removed: print('  ·', d, '→', k)
h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
open('index.html', 'w', encoding='utf-8').write(h)
