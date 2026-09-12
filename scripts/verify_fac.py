#!/usr/bin/env python3
"""주차·룸이 '있다'고 돼 있는데 근거가 없는 곳을, 구글 리뷰를 읽어 확인한다.
   리뷰에 근거가 있으면 그대로 두고 잠그고, 없으면 '미확인'으로 돌린다.
   python3 scripts/verify_fac.py --dry
"""
import json, re, subprocess, sys, time

h = open('index.html', encoding='utf-8').read()
KEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
dry = '--dry' in sys.argv

YES_PARK = re.compile(r'주차(장)?(가|는|도|이)?\s*(넓|많|편|충분|가능|있|무료|완비)|주차\s*\d+\s*대|발렛')
NO_PARK  = re.compile(r'주차(가|는|장)?\s*(어렵|불편|힘들|없|협소|빡세|안\s*되)|길가에\s*(대|주차)|주차\s*전쟁')
YES_ROOM = re.compile(r'룸(이|은|도|에서)?\s*(있|따로|넉넉|예약)|개별\s*룸|프라이빗\s*룸|방(이|으로)\s*(있|따로)|단체석')
NO_ROOM  = re.compile(r'룸(은|이)?\s*(없|안\s*되)')

def reviews(gid):
    o = subprocess.run(['curl', '-s', '-m', '25', f'https://places.googleapis.com/v1/places/{gid}?languageCode=ko',
        '-H', 'X-Goog-Api-Key: ' + KEY, '-H', 'Referer: https://soyeonna.github.io/',
        '-H', 'X-Goog-FieldMask: reviews'], capture_output=True, text=True).stdout
    try:
        g = json.loads(o)
        return ' '.join((r.get('text') or {}).get('text', '') for r in (g.get('reviews') or []))
    except Exception:
        return ''

def check(key, yes, no):
    keep, drop, off = [], [], []
    for p in P:
        f = p.get('fac') or {}
        if f.get(key) is not True or p.get('facLock'): continue
        if key == 'parking' and p.get('gpark'): continue        # 구글 주차정보가 있으면 근거로 본다
        rv = reviews(p['gid']) if p.get('gid') else ''
        if no.search(rv):
            off.append(p['n'])
            if not dry: f[key] = False; p['facLock'] = True
        elif yes.search(rv):
            keep.append(p['n'])
            if not dry: p['facLock'] = True
        else:
            drop.append(p['n'])
            if not dry: f.pop(key, None)
        time.sleep(0.1)
    print(f'[{key}] 근거 확인 {len(keep)} · 없음으로 {len(off)} · 미확인으로 {len(drop)}')
    if keep: print('  그대로:', ' · '.join(keep))
    if off:  print('  없음:  ', ' · '.join(off))
    if drop: print('  미확인:', ' · '.join(drop))

check('parking', YES_PARK, NO_PARK)
check('room', YES_ROOM, NO_ROOM)
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
