#!/usr/bin/env python3
"""릴스 캡션에서 자동으로 뽑다가 말이 끊긴 꿀팁·조합·시그니처를 정리한다.
   끊긴 말은 지어내지 않고 지운다. 시그니처에 붙은 동사 찌꺼기('감자탕, 먹으면')도 떼어낸다.
   python3 scripts/fix_cut_text.py --dry
"""
import json, re, sys

# 문장이 끝나지 않은 꼬리
CUT = re.compile(r'(는데|건데|인데|킥인데|한다는데|주시는데|먹는데|하고|추천드리고|오면|편한게|주는|시킨건데)$')
# 시그니처에 붙은 동사 찌꺼기
VERB = re.compile(r'[,·]?\s*(먹으면|보면|생각하면|넣으면|말아주는|찍어먹는)\s*$')
JUNK = {'생각하면', '먹으면', '보면', '넣으면'}

h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
dry = '--dry' in sys.argv
log = []
for p in P:
    for k in ('tip', 'combo'):
        t = (p.get(k) or '').strip()
        if not t: continue
        parts = [x.strip() for x in t.split('·') if x.strip()]
        keep = [x for x in parts if not CUT.search(x.rstrip('.'))]
        if len(keep) == len(parts): continue      # 지울 게 없으면 손대지 않는다 (띄어쓰기가 바뀌지 않게)
        new = ' · '.join(keep)
        if new != t:
            log.append((p['n'], k, t, new or '(지움)'))
            if not dry:
                if new: p[k] = new
                else: p.pop(k, None)
    s = (p.get('sig') or '').strip()
    if s:
        n2 = VERB.sub('', s).strip(' ,·')
        n2 = re.sub(r',\s*$', '', n2)
        if n2 != s:
            log.append((p['n'], 'sig', s, n2 or '(지움)'))
            if not dry:
                if n2 and n2 not in JUNK: p['sig'] = n2
                else: p.pop('sig', None)
print(f'정리 {len(log)}건')
for n, k, o, w in log: print(f'  {n:20} [{k}] {o}  →  {w}')
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
