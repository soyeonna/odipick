#!/usr/bin/env python3
"""구글이 '영업 종료(폐업)'로 표시한 가게를 찾는다.   python3 scripts/check_closed_google.py [--apply]

카카오 검색으로만 보던 기존 방식보다 정확하다. 구글은 폐업·임시휴업을 따로 알려준다.
--apply 를 붙이면 index.html 에 표시하고, 붙이지 않으면 목록만 보여준다.
"""
import json, re, sys, subprocess, concurrent.futures as cf

APPLY = '--apply' in sys.argv
h = open('index.html', encoding='utf-8').read()
KEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))

def status(gid):
    out = subprocess.run(['curl', '-s', '-m', '20', f'https://places.googleapis.com/v1/places/{gid}?languageCode=ko',
        '-H', 'X-Goog-Api-Key: ' + KEY, '-H', 'Referer: https://soyeonna.github.io/',
        '-H', 'X-Goog-FieldMask: businessStatus,displayName'], capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
        return d.get('businessStatus'), d.get('displayName', {}).get('text', '')
    except Exception:
        return None, ''

todo = [p for p in P if p.get('gid') and not p.get('closed')]
print(f'구글에 확인할 곳 {len(todo)}곳')
res = {}
with cf.ThreadPoolExecutor(max_workers=8) as ex:
    for p, r in zip(todo, ex.map(status, [x['gid'] for x in todo])): res[p['n']] = r

shut = [(n, r[0], r[1]) for n, r in res.items() if r[0] in ('CLOSED_PERMANENTLY', 'CLOSED_TEMPORARILY')]
gone = [n for n, r in res.items() if r[0] is None]
LABEL = {'CLOSED_PERMANENTLY': '폐업', 'CLOSED_TEMPORARILY': '임시 휴업'}
print(f'\n폐업·휴업으로 나온 곳 {len(shut)}곳')
for n, s, g in shut: print(f'  · {n}  →  {LABEL[s]}  ({g})')
if gone: print(f'\n구글에서 응답이 없던 곳 {len(gone)}곳 (키 문제일 수 있음): {gone[:8]}')

if APPLY and shut:
    for p in P:
        r = res.get(p['n'])
        if not r: continue
        if r[0] == 'CLOSED_PERMANENTLY':
            p['closed'] = True; p['closedWhy'] = '구글에서 폐업으로 확인'
        elif r[0] == 'CLOSED_TEMPORARILY':
            p['tempClosed'] = True
    h2 = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h2)
    print('\nindex.html 에 표시했습니다.')
elif shut:
    print('\n표시까지 하려면: python3 scripts/check_closed_google.py --apply')
