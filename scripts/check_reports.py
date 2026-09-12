#!/usr/bin/env python3
"""손님들이 남긴 '잘못된 정보 신고'를 모아서 보여준다.

  python3 scripts/check_reports.py          # 아직 처리 안 한 것만
  python3 scripts/check_reports.py --all    # 처리한 것까지 전부
  python3 scripts/check_reports.py --done 3,7,12   # 3,7,12번 처리 완료로 표시

급한 것(폐업 신고, 같은 가게에 여러 번 들어온 신고)을 맨 위에 보여준다.
"""
import json, os, re, sys, subprocess
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def env():
    out = {}
    p = os.path.join(ROOT, '.env')
    if not os.path.exists(p):
        sys.exit('.env 파일이 없습니다. 소연님께 받아서 프로젝트 폴더에 넣어주세요.')
    for line in open(p, encoding='utf-8'):
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        out[k.strip()] = v.strip()
    return out

E = env()
URL = E.get('SUPABASE_URL', '').rstrip('/')
KEY = E.get('SUPABASE_SERVICE_KEY', '')
if not URL or not KEY:
    sys.exit('.env 에 SUPABASE_URL 과 SUPABASE_SERVICE_KEY 가 필요합니다.')


def api(path, method='GET', body=None, extra_headers=None):
    """다른 스크립트들과 같이 curl 로 부른다 (맥 파이썬 인증서 문제를 피하려고)."""
    cmd = ['curl', '-s', '-m', '30', '-X', method, URL + '/rest/v1/' + path,
           '-H', 'apikey: ' + KEY, '-H', 'Authorization: Bearer ' + KEY,
           '-H', 'Content-Type: application/json']
    for k, v in (extra_headers or {}).items():
        cmd += ['-H', '%s: %s' % (k, v)]
    if body is not None:
        cmd += ['-d', json.dumps(body, ensure_ascii=False)]
    raw = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
    if not raw:
        return []
    try:
        out = json.loads(raw)
    except json.JSONDecodeError:
        sys.exit('저장소에서 답을 못 받았습니다. 인터넷 연결이나 .env 키를 확인해 주세요.\n' + raw[:200])
    if isinstance(out, dict) and out.get('message'):
        sys.exit('저장소 오류: ' + out['message'])
    return out


def places():
    h = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    m = re.search(r'<script id="places" type="application/json">(\[.*?\])</script>', h, re.S)
    return json.loads(m.group(1)) if m else []


LABEL = {
    'closed':  '폐업했대요',
    'hours':   '영업시간이 다르대요',
    'parking': '주차 정보가 틀렸대요',
    'price':   '가격이 다르대요',
    'etc':     '기타 정보 오류',
    'open':    '영업 상태 관련',
}
# info_* 는 신고가 아니라 손님이 알려준 좋은 정보다
INFO = {
    'info_quiet': '조용한 편이래요', 'info_parking': '주차 된대요',
    'info_solo': '혼밥하기 좋대요', 'info_group': '단체 된대요',
    'info_good': '맛있대요 (추천)',
}


def mark_done(ids):
    for i in ids:
        api('user_reports?id=eq.%d' % i, 'PATCH', {'verification_status': 'done'},
            {'Prefer': 'return=minimal'})
    print('%d건 처리 완료로 표시했습니다.' % len(ids))


def main():
    args = sys.argv[1:]
    if '--done' in args:
        raw = args[args.index('--done') + 1]
        mark_done([int(x) for x in re.findall(r'\d+', raw)])
        return

    show_all = '--all' in args
    q = 'user_reports?select=*&order=created_at.desc&limit=500'
    if not show_all:
        q += '&verification_status=eq.pending'
    rows = api(q)

    if not rows:
        print('새로 들어온 신고가 없습니다.')
        return

    known = {p['n'] for p in places()}

    reports, infos = [], []
    for r in rows:
        (infos if str(r.get('report_type', '')).startswith('info_') else reports).append(r)

    # 같은 가게에 몇 번 들어왔는지
    by_shop = defaultdict(list)
    for r in reports:
        by_shop[(r.get('value') or '(가게 이름 없음)').strip()].append(r)

    def urgency(shop, rs):
        kinds = {r['report_type'] for r in rs}
        if 'closed' in kinds:
            return 0, '폐업 신고 — 사실이면 바로 내려야 합니다'
        if len(rs) >= 3:
            return 1, '같은 가게에 %d번 들어왔습니다' % len(rs)
        if shop not in known:
            return 2, '목록에 없는 가게 이름입니다 — 오타이거나 이미 지운 곳'
        return 3, ''

    ranked = sorted(by_shop.items(), key=lambda kv: (urgency(kv[0], kv[1])[0], -len(kv[1])))

    urgent = [(s, rs) for s, rs in ranked if urgency(s, rs)[0] <= 1]
    normal = [(s, rs) for s, rs in ranked if urgency(s, rs)[0] > 1]

    print('=' * 46)
    print('오디픽 신고 정리   ·   총 %d건 (가게 %d곳)' % (len(reports), len(by_shop)))
    print('=' * 46)

    if urgent:
        print('\n■ 빨리 봐야 할 것 %d곳' % len(urgent))
        for shop, rs in urgent:
            _, why = urgency(shop, rs)
            print('\n  · %s   [%s]' % (shop, why))
            for r in rs:
                print('      #%-4d %-16s %s' % (r['id'], LABEL.get(r['report_type'], r['report_type']),
                                                r['created_at'][:10]))

    if normal:
        print('\n■ 확인해두면 좋은 것 %d곳' % len(normal))
        for shop, rs in normal:
            kinds = ' / '.join(sorted({LABEL.get(r['report_type'], r['report_type']) for r in rs}))
            ids = ','.join(str(r['id']) for r in rs)
            print('  · %-22s %-28s (#%s)' % (shop, kinds, ids))

    if infos:
        print('\n■ 손님이 알려준 정보 %d건 — 신고가 아니라 제보입니다' % len(infos))
        agg = defaultdict(list)
        for r in infos:
            agg[(r.get('value') or '?').strip()].append(INFO.get(r['report_type'], r['report_type']))
        for shop, ks in sorted(agg.items(), key=lambda kv: -len(kv[1]))[:20]:
            print('  · %-22s %s' % (shop, ' / '.join(ks)))

    print('\n처리한 건은 이렇게 표시하세요:')
    print('  python3 scripts/check_reports.py --done 1,2,3')


if __name__ == '__main__':
    main()
