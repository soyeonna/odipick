#!/usr/bin/env python3
"""사이트에서 보낸 의견(별점·글)을 데이터베이스에서 받아 index.html 의 관리자 전용 목록에 넣고 docs/받은-의견.md 로도 저장한다.
   daily-care 에서 매일 돈다.   python3 scripts/pull_feedback.py"""
import json, re, subprocess
env = dict(l.strip().split('=', 1) for l in open('.env') if '=' in l and not l.startswith('#'))
U = (env.get('SUPABASE_URL') or 'https://ntmzjsozgxjepwhxsniu.supabase.co').strip().strip('"')
K = env.get('SUPABASE_SERVICE_KEY', '').strip().strip('"')
if not K: print('SUPABASE_SERVICE_KEY 없음'); raise SystemExit
rows = json.loads(subprocess.run(['curl', '-s', '-m', '30',
    U + '/rest/v1/recommendation_logs?select=parsed_conditions,created_at&query=eq.__feedback__&order=created_at.desc&limit=500',
    '-H', 'apikey: ' + K, '-H', 'Authorization: Bearer ' + K], capture_output=True, text=True).stdout or '[]')
fb = []
for r in rows:
    pc = r.get('parsed_conditions') or {}
    fb.append({'r': int(pc.get('rating') or 0), 't': pc.get('text') or '', 'at': (r.get('created_at') or '')[:16].replace('T', ' ')})
h = open('index.html', encoding='utf-8').read()
m = re.search(r'(<script id="fb" type="application/json">)([\s\S]*?)(</script>)', h)
old = json.loads(m.group(2) or '[]')
seen = {(x.get('at'), x.get('t')) for x in fb}
merged = fb + [x for x in old if (x.get('at'), x.get('t')) not in seen]
h = h[:m.start(2)] + '\n' + json.dumps(merged, ensure_ascii=False) + '\n' + h[m.end(2):]
open('index.html', 'w', encoding='utf-8').write(h)
L = ['# 받은 의견', '', f'총 {len(merged)}건 · 최신순. `python3 scripts/pull_feedback.py` 로 갱신.', '']
for x in merged: L.append(f"- {x['at']} · {'★' * x['r'] or '별점 없음'} · {x['t'] or '(글 없음)'}")
open('docs/받은-의견.md', 'w', encoding='utf-8').write('\n'.join(L) + '\n')
print(f'의견 {len(fb)}건 받음 · 총 {len(merged)}건 → docs/받은-의견.md')
