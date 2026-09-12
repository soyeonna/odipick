#!/usr/bin/env python3
"""구글 리뷰에서 '조용한지 시끄러운지'를 뽑아 매장에 넣는다.

  python3 scripts/extract_ambience.py [--dry]

원칙
 - 리뷰 문장을 그대로 가져오지 않는다. **신호만 세고 판단은 우리가 한다.**
 - 구글이 가게당 리뷰를 5건만 주므로, 2건 이상이면 '확인됨', 1건이면 '짐작'으로 나눈다.
   '짐작'은 순위에만 쓰고 화면에 배지로 보여주지 않는다.
 - 조용하다는 말과 시끄럽다는 말이 맞서면 확정하지 않고 비워둔다.
 - 소연님이 직접 확인한 값(ownerCheckedAt)은 건드리지 않는다.
 - 근거를 함께 남긴다 (몇 건에서 나왔는지).
"""
import json, os, re, sys

DRY  = '--dry' in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 조용한 쪽 신호
QUIET = [
    r'조용(?!히\s*해)', r'한적', r'차분', r'아늑', r'소란스럽지\s*않',
    r'시끄럽지\s*않', r'대화\s*(하기|나누기)\s*좋', r'얘기하기\s*좋',
    r'붐비지\s*않',
]
# 시끄러운 쪽 신호
LOUD = [
    r'시끄(럽|러)', r'소란', r'왁자', r'정신\s*없', r'북적', r'떠들',
    r'대화가\s*(안|어렵)', r'말소리가\s*안', r'음악이\s*(너무\s*)?커',
]
# 이런 말이 같이 나오면 신호로 안 친다 (부정문·조건문)
NEGATE = re.compile(r'(조용|한적|아늑)[^.。!?]{0,10}(않|아니|없|말)')

QRE = [re.compile(p) for p in QUIET]
LRE = [re.compile(p) for p in LOUD]


def count_signals(reviews, shopname=''):
    q = l = 0
    qs, ls = [], []
    for r in reviews:
        t = str(r)
        if shopname and len(shopname) >= 2:
            t = t.replace(shopname, ' ')     # 가게 이름이 신호로 오인되는 것 방지 ('소란' 같은 상호)
        hitq = any(p.search(t) for p in QRE) and not NEGATE.search(t)
        hitl = any(p.search(t) for p in LRE)
        if hitq and not hitl:
            q += 1
            m = next((p.search(t) for p in QRE if p.search(t)), None)
            if m and len(qs) < 3: qs.append(m.group(0))
        elif hitl and not hitq:
            l += 1
            m = next((p.search(t) for p in LRE if p.search(t)), None)
            if m and len(ls) < 3: ls.append(m.group(0))
    return q, l, qs, ls


def main():
    path = os.path.join(ROOT, 'index.html')
    html = open(path, encoding='utf-8').read()
    m = re.search(r'(<script id="places" type="application/json">)(\[.*?\])(</script>)', html, re.S)
    P = json.loads(m.group(2))

    gpath = os.path.join(ROOT, 'data/greviews.json')
    if not os.path.exists(gpath):
        sys.exit('data/greviews.json 이 없습니다.')
    G = json.load(open(gpath, encoding='utf-8'))

    quiet, loud, mixed, thin = [], [], [], 0
    for p in P:
        gid = p.get('gid')
        if not gid or gid not in G:
            continue
        if p.get('ownerCheckedAt'):        # 소연님이 확인한 곳은 손대지 않는다
            continue
        rv = (G[gid] or {}).get('rv') or []
        q, l, qs, ls = count_signals(rv, p.get('n', ''))
        # 구글이 가게당 리뷰를 5건만 주므로 2건 요구는 무리다.
        #   2건 이상 → 확인됨 (화면에 배지로 보여도 된다)
        #   1건      → 짐작 (순위에만 반영하고 화면에는 안 쓴다)
        if q and l:
            mixed.append(p['n']); continue
        if q:
            verdict, why, cnt = 'quiet', qs, q
        elif l:
            verdict, why, cnt = 'lively', ls, l
        else:
            thin += 1; continue

        conf = 'confirmed' if cnt >= 2 else 'weak'
        amb = p.setdefault('ambience', {})
        amb['noiseLevel'] = verdict
        amb['noiseConfidence'] = conf
        amb['noiseEvidence'] = {'source': '구글 리뷰', 'mentions': cnt, 'words': why}
        (quiet if verdict == 'quiet' else loud).append((p['n'], cnt, conf, ' · '.join(why)))

    # 이미 붙어 있던 분위기 태그도 근거로 친다 (리뷰보다 먼저 정해진 값이라 덮어쓰지 않는다)
    from_mood = 0
    for p in P:
        if p.get('ownerCheckedAt'):
            continue
        amb = p.get('ambience') or {}
        if amb.get('noiseLevel'):
            continue
        mood = p.get('mood') or []
        v = 'quiet' if '조용한' in mood else ('lively' if '활기찬' in mood else None)
        if not v:
            continue
        amb = p.setdefault('ambience', {})
        amb['noiseLevel'] = v
        amb['noiseConfidence'] = 'confirmed'
        amb['noiseEvidence'] = {'source': '분위기 태그', 'words': ['조용한' if v == 'quiet' else '활기찬']}
        from_mood += 1

    print('=== 리뷰에서 찾은 분위기 ===')
    print('\n조용한 쪽 %d곳' % len(quiet))
    for n, c, cf, w in sorted(quiet, key=lambda x: -x[1])[:14]:
        print('  %-20s 리뷰 %d건 %-9s (%s)' % (n, c, '확인됨' if cf == 'confirmed' else '짐작', w))
    print('\n시끄러운 쪽 %d곳' % len(loud))
    for n, c, cf, w in sorted(loud, key=lambda x: -x[1])[:14]:
        print('  %-20s 리뷰 %d건 %-9s (%s)' % (n, c, '확인됨' if cf == 'confirmed' else '짐작', w))
    if mixed:
        print('\n말이 엇갈려 비워둔 곳 %d곳 — %s' % (len(mixed), ', '.join(mixed[:8])))
    print('\n분위기 태그에서 추가로 채운 곳: %d곳' % from_mood)
    print('근거가 부족해 건드리지 않은 곳: %d곳' % thin)

    if DRY:
        print('\n--dry 라서 파일은 그대로 뒀습니다.')
        return
    out = html[:m.start(2)] + json.dumps(P, ensure_ascii=False) + html[m.end(2):]
    open(path, 'w', encoding='utf-8').write(out)
    print('\nindex.html 에 반영했습니다.')


if __name__ == '__main__':
    main()
