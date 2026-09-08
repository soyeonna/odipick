#!/usr/bin/env python3
"""카카오 고유번호(kid)가 있는 매장의 좌표를 카카오 기준으로 바로잡는다.   python3 scripts/fix_coords.py [--dry]
   좌표가 300m 넘게 다르면 카카오 좌표로 바꾼다. 로드뷰·지도·가까운 순·코스가 모두 이 좌표를 쓴다."""
import json, re, subprocess, sys, time, urllib.parse, math
dry = '--dry' in sys.argv
key = ''
for line in open('.env', encoding='utf-8'):
    if line.strip().startswith('KAKAO_REST_KEY'): key = line.split('=', 1)[1].strip()
if not key: sys.exit('KAKAO_REST_KEY 없음')
def kakao(q):
    u = 'https://dapi.kakao.com/v2/local/search/keyword.json?size=15&query=' + urllib.parse.quote(q)
    r = subprocess.run(['curl', '-sS', '--max-time', '15', '-H', f'Authorization: KakaoAK {key}', u], capture_output=True)
    try: return json.loads(r.stdout).get('documents', [])
    except Exception: return []
h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
fixed, miss = [], []
for p in P:
    if not p.get('kid'): continue
    dong = re.match(r'(\S+동)', str(p.get('area') or ''))
    doc = None
    for q in ([f"대전 {dong.group(1)} {p['n']}"] if dong else []) + [f"대전 {p['n']}", p['n']]:
        doc = next((d for d in kakao(q) if d['id'] == str(p['kid'])), None)
        if doc: break
        time.sleep(0.1)
    if not doc: miss.append(p['n']); continue
    la, lo = float(doc['y']), float(doc['x'])
    if p.get('lat') and math.hypot((p['lng'] - lo) * 88.8, (p['lat'] - la) * 111.1) < 0.3: continue
    fixed.append((p['n'], p.get('area'), round(math.hypot((p['lng'] - lo) * 88.8, (p['lat'] - la) * 111.1), 1) if p.get('lat') else None))
    p['lat'], p['lng'] = la, lo
print(f'좌표 바로잡음 {len(fixed)}곳 · 카카오에서 못 찾음 {len(miss)}곳')
for f in fixed: print('  ·', *f, 'km')
if miss: print('  못 찾음:', ', '.join(miss[:30]))
if not dry:
    h = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h)
