#!/usr/bin/env python3
"""영업시간 표기를 구글 원본(gperiods)에서 다시 만든다.
   지금 저장된 글자는 '오후 10:00' 을 '10:00' 으로 잘못 줄인 것이 많다.
   손으로 적은 '2·5번째 일 휴무' 같은 말은 뒤에 그대로 붙여 남긴다.
   python3 scripts/fix_hours.py            # 고치기
   python3 scripts/fix_hours.py --dry      # 미리보기만
"""
import json, re, sys

DAY = '월화수목금토일'          # gperiods 의 0 은 일요일
ORDER = [1, 2, 3, 4, 5, 6, 0]   # 월~일 순서
KEEP = re.compile(r'(?<![:\d])((?:[0-9]+[·,]\s*)*[0-9]+번째[^·]*휴무|연중무휴|라스트오더[^·]*|예약[^·]*|브레이크[^·]*)')

def hm(mn):
    mn %= 1440
    return '%02d:%02d' % (mn // 60, mn % 60)

def span(ps):
    """하루치 구간들 → '11:00–22:00' 또는 '11:00–15:00 · 17:00–21:00'"""
    ps = sorted(ps, key=lambda x: x[1] % 1440)
    out = []
    for _, o, c in ps:
        c2 = c % 1440
        out.append(hm(o) + '–' + ('24:00' if c2 == 0 else hm(c2)))
    return ' · '.join(out)

def label(days):
    """연속된 요일을 '월–금' 으로 묶는다"""
    idx = sorted(ORDER.index(d) for d in days)
    if len(idx) == 7: return '매일'
    out, i = [], 0
    while i < len(idx):
        j = i
        while j + 1 < len(idx) and idx[j + 1] == idx[j] + 1: j += 1
        out.append(DAY[idx[i]] if i == j else DAY[idx[i]] + '–' + DAY[idx[j]])
        i = j + 1
    return ','.join(out)

def build(gp):
    # 24시간 영업: 구글은 여는 시각만 주고 닫는 시각을 안 준다
    if len(gp) == 1 and gp[0][1] % 1440 == 0 and gp[0][2] % 1440 in (0,):
        return '24시간'
    byday = {}
    for row in gp:
        byday.setdefault(row[0], []).append(row)
    if not byday: return None
    groups = {}
    for d, ps in byday.items():
        groups.setdefault(span(ps), []).append(d)
    parts = []
    for s, days in sorted(groups.items(), key=lambda kv: min(ORDER.index(d) for d in kv[1])):
        parts.append((label(days) + ' ' + s).strip())
    off = [d for d in ORDER if d not in byday]
    if off and len(off) < 7:
        parts.append(label(off) + ' 휴무')
    return ' · '.join(parts)

h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
dry = '--dry' in sys.argv
changed = []
for p in P:
    gp = p.get('gperiods')
    if not gp: continue
    new = build(gp)
    if not new: continue
    old = p.get('hours') or ''
    keep2 = ' · ' not in new          # 구글이 브레이크타임을 안 준 경우만 손으로 적은 값을 남긴다
    tail = [t.strip(' ·') for t in KEEP.findall(old)
            if t.strip(' ·') and ('브레이크' not in t or keep2)]
    if tail:
        new += ' · ' + ' · '.join(dict.fromkeys(tail))
        # 'N번째 일요일 휴무' 가 있으면 뭉뚱그린 '일 휴무' 는 겹치므로 뺀다
        d2 = re.search(r'([월화수목금토일])요일 휴무', new)
        if d2:
            new = re.sub(r'(?<= )' + d2.group(1) + r' 휴무 · ', '', new)
    if new != old:
        changed.append((p['n'], old, new))
        p['hours'] = new
print(f'영업시간 다시 만든 곳 {len(changed)}')
for n, o, w in changed[:200]:
    print(f'  {n} : {o or "(없음)"}  →  {w}')
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
