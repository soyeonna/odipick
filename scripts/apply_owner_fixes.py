#!/usr/bin/env python3
"""소연님이 직접 확인해 주신 매장 정보를 반영한다.

  python3 scripts/apply_owner_fixes.py [--dry]

소연님이 다녀와서 확인한 내용이라 구글·공공데이터보다 우선한다.
반영한 항목에는 '대전공주 직접 확인' 출처를 남긴다.
"""
import json, os, re, sys, datetime

DRY  = '--dry' in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date.today().isoformat()

# 가게이름 : {고칠 것}
#   parking/room/group/reserve → True(있음) / False(없음) / None(모름)
#   cat  → 분류 문자열 교체
#   solo → 혼밥 가능
FIXES = {
    '더바사삭':        {'cat': '돈까스·한식', 'cats': ['한식']},
    '화로야':          {'parking': False},
    '행운삼겹살':      {'parking': False},
    '새벽소':          {'parking': False, 'room': True},
    '계인기':          {'parking': True,  'room': False},
    '찰싹':            {'parking': False, 'room': False, 'group': True},
    '국제통닭':        {'parking': True,  'room': False},
    '천가':            {'parking': False, 'room': False},
    '남촌황소곱창':    {'parking': False, 'room': False, 'group': True},
    '은주':            {'room': False, 'group': True},
    '원조태평소국밥':  {'room': False},
    '범수산':          {'parking': True,  'room': True},
    '아오리의 행방불명': {'parking': False, 'group': False, 'room': False, 'solo': True},
    '소머리해장국':    {'budget': 2},                     # 1인 1만원대
    '오씨칼국수':      {'sig': '물총칼국수 · 해물파전'},
    '수미가':          {'room': False},
    '찰싹':            {'combo': '3mm 숙성삼겹살로 쌈 싸먹는 신박한 조합'},   # 앞 '3' 이 잘려 있었다
    # 명소·공원 — 시설 주차장이 따로 있다 (가게 주차 개념이 아니다)
    '장태산자연휴양림': {'parking': True, 'tip': None},
    '한밭수목원':      {'parking': True},
    '대청호자연생태관': {'cat': '생태관'},                  # '박물관' 은 공공데이터 분류라 실제와 안 맞다

    # 2026-09-13 2차
    '로바타모에':      {'v': '전 좌석에 앉아 즐기는 둔산동 일본 감성 이자카야'},
    '빨간포차':        {'dropReels': ['DL4WldsSfh4']},      # 이전 가게 릴스
    '파스타바밍':      {'dropReels': ['DZuEt5iCfpc']},      # 릴스가 아니라 피드 캐러셀
    '구구구':          {'parking': False},
    '글리하우스':      {'pet': True, 'group': True,
                       'v': '우베 디저트로 알려진 구암동 대형 베이커리 카페. 강아지 놀이터가 따로 있어요'},
    '타향골 따귀탕':   {'parking': False, 'hours': '24시간',
                       'v': '맑고 진한 뼈탕에 육사시미. 둔산동'},
    '다이너':          {'pet': True, 'room': True,
                       'v': '애견동반 되는 가성비 양식집. 강아지 쿠션·배변패드·물·수제간식까지 챙겨줘요'},
}

FACKEY = {'parking': 'parking', 'room': 'room', 'group': 'group', 'reserve': 'reserve'}


def main():
    path = os.path.join(ROOT, 'index.html')
    html = open(path, encoding='utf-8').read()
    m = re.search(r'(<script id="places" type="application/json">)(\[.*?\])(</script>)', html, re.S)
    P = json.loads(m.group(2))

    touched, notfound = [], []
    for name, fix in FIXES.items():
        hits = [p for p in P if name in p.get('n', '')]
        if not hits:
            notfound.append(name)
            continue
        for p in hits:
            fac = p.setdefault('fac', {})
            changed = []
            for k, v in fix.items():
                if k in FACKEY:
                    if fac.get(FACKEY[k]) != v:
                        fac[FACKEY[k]] = v
                        changed.append('%s=%s' % (k, {True: '있음', False: '없음'}.get(v, v)))
                elif k == 'solo':
                    sit = p.setdefault('sit', [])
                    if v and '혼밥' not in sit:
                        sit.append('혼밥'); changed.append('혼밥 가능')
                elif k == 'cats':
                    p['cats'] = v; changed.append('종류=' + '·'.join(v))
                elif k == 'dropReels':
                    igs = [x for x in (p.get('igs') or []) if x not in v]
                    if igs != (p.get('igs') or []):
                        p['igs'] = igs
                        if p.get('ig') in v: p['ig'] = igs[0] if igs else None
                        changed.append('릴스 %d개 뺌' % len(v))
                elif k == 'pet':
                    fac = p.setdefault('fac', {})
                    if fac.get('pet') != v: fac['pet'] = v; changed.append('애견동반=%s' % ('있음' if v else '없음'))
                elif k == 'tip' and v is None:
                    if p.get('tip'):
                        changed.append('꿀팁 지움("%s")' % str(p['tip'])[:20]); p.pop('tip', None)
                else:
                    if p.get(k) != v:
                        p[k] = v; changed.append('%s=%s' % (k, v))
            if changed:
                # 누가 확인했는지 남긴다
                ev = p.setdefault('evidence', [])
                ev.append({'source': '대전공주 직접 확인', 'fields': list(fix.keys()), 'verifiedAt': TODAY})
                p['ownerCheckedAt'] = TODAY
                touched.append((p['n'], ', '.join(changed)))

    print('=== 반영한 매장 %d건 ===' % len(touched))
    for n, c in touched:
        print('  %-20s %s' % (n, c))
    if notfound:
        print('\n=== 목록에서 못 찾은 이름 ===')
        print('  ' + ', '.join(notfound))

    if DRY:
        print('\n--dry 라서 파일은 그대로 뒀습니다.')
        return
    out = html[:m.start(2)] + json.dumps(P, ensure_ascii=False) + html[m.end(2):]
    open(path, 'w', encoding='utf-8').write(out)
    print('\nindex.html 에 반영했습니다.')


if __name__ == '__main__':
    main()
