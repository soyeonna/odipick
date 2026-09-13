#!/usr/bin/env python3
"""소연님이 확인해 준 주소로 카카오에서 좌표와 장소 ID를 다시 잡는다.

  python3 scripts/link_by_address.py [--dry]

원칙
 - 상호 + 주소(동) + 업종이 전부 맞을 때만 확정한다.
 - 후보가 여러 개거나 하나도 없으면 손대지 않고 보고만 한다.
 - 구글이 자동으로 잡아둔 좌표는 믿지 않고 이 결과로 덮는다.
"""
import json, os, re, sys, subprocess, datetime

DRY   = '--dry' in sys.argv
ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TODAY = datetime.date.today().isoformat()

# 소연님이 확인한 것. name = 목록에서 찾을 이름(부분 일치), shop = 카카오에서 찾을 상호
TARGETS = [
  dict(name='경복궁',     shop='경복궁',            addr='대전 서구 대덕대로 366',          dong='만년동', kind='음식점', newName='경복궁 대전점'),
  dict(name='수린',       shop='수린',              addr='대전 유성구 대덕대로 576',        dong='도룡동', kind='음식점', newName='수린 대전점'),
  dict(name='도군샤부',   shop='도군샤부',          addr='대전 서구 둔산남로9번길 51',      dong='둔산동', kind='음식점', newName='도군샤부 둔산점', create=True),
  dict(name='칼만사',     shop='칼국수 만드는 사람들', addr='대전 서구 둔산중로78번길 20',   dong='둔산동', kind='음식점', newName='칼국수 만드는 사람들', create=True),
  dict(name='타츠진우동', shop='타츠진우동',        addr='대전 서구 대덕대로249번길 15',    dong='둔산동', kind='음식점'),
  dict(name='삼오식당',   shop='삼오식당',          addr='대전 서구 만년로 70',            dong='만년동', kind='음식점'),
  dict(name='일등석갈비', shop='일등석갈비',        addr='대전 서구 둔산대로117번길 17',   dong='만년동', kind='음식점'),
]


def env():
    out = {}
    for line in open(os.path.join(ROOT, '.env'), encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1); out[k.strip()] = v.strip()
    return out

KEY = env().get('KAKAO_REST_KEY')
if not KEY:
    sys.exit('.env 에 KAKAO_REST_KEY 가 없습니다.')


def kakao(path, **q):
    cmd = ['curl', '-s', '-m', '20', '-G', 'https://dapi.kakao.com/v2/local/' + path,
           '-H', 'Authorization: KakaoAK ' + KEY]
    for k, v in q.items():
        cmd += ['--data-urlencode', '%s=%s' % (k, v)]
    raw = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(raw).get('documents') or []
    except Exception:
        return []


def norm(s):
    return re.sub(r'[\s\-·,.()]|대전점|둔산점|본점|직영점', '', str(s or '')).lower()


def main():
    path = os.path.join(ROOT, 'index.html')
    html = open(path, encoding='utf-8').read()
    m = re.search(r'(<script id="places" type="application/json">)\s*(\[.*?\])\s*(</script>)', html, re.S)
    P = json.loads(m.group(2))

    fixed, held = [], []
    for t in TARGETS:
        # ① 주소 → 좌표
        geo = kakao('search/address.json', query=t['addr'])
        if not geo:
            held.append((t['shop'], '주소를 카카오가 못 찾음: ' + t['addr'])); continue
        gx, gy = float(geo[0]['x']), float(geo[0]['y'])

        # ② 그 자리 150m 안에서 상호로 검색
        near = kakao('search/keyword.json', query=t['shop'], x=gx, y=gy, radius=150, size=15)
        cands = []
        for d in near:
            same_name = norm(t['shop']) in norm(d['place_name']) or norm(d['place_name']) in norm(t['shop'])
            same_kind = t['kind'] in str(d.get('category_group_name') or '') or t['kind'] in str(d.get('category_name') or '')
            same_dong = t['dong'] in str(d.get('address_name') or '')
            if same_name and same_kind and same_dong:
                cands.append(d)
        if len(cands) != 1:
            why = '후보 %d개' % len(cands) if cands else '150m 안에 맞는 상호·업종·동네가 없음'
            if near and not cands:
                why += ' (근처엔 ' + ', '.join(d['place_name'] + '/' + (d.get('category_group_name') or '?') for d in near[:3]) + ')'
            held.append((t['shop'], why)); continue
        d = cands[0]

        # ③ 목록에서 대상 찾기 (같은 이름이 여럿이면 카페 같은 딴 업종은 제외)
        hits = [p for p in P if t['name'] in p['n']]
        if not hits and t.get('create'):
            p = {'n': t.get('newName') or d['place_name'], 'cat': str(d.get('category_name') or '').split('>')[-1].strip() or t['kind'],
                 'cats': ['한식'], 'src': 'local', 'sit': [], 'fac': {}}
            P.append(p); hits = [p]
        if not hits:
            held.append((t['shop'], '목록에 없고 create 지정도 없음')); continue
        if len(hits) > 1:
            # 같은 건물 층별 중복 같은 것 — 첫 것만 남기고 나머지는 합친다
            keep = hits[0]
            for extra in hits[1:]:
                for k, v in extra.items():
                    if k not in keep or keep[k] in (None, '', [], {}): keep[k] = v
                P.remove(extra)
            hits = [keep]
        p = hits[0]
        p['n']    = t.get('newName') or p['n']
        p['lat']  = float(d['y']); p['lng'] = float(d['x'])
        p['kid']  = d['id']; p['kurl'] = 'https://place.map.kakao.com/' + d['id']
        p['kcat'] = d.get('category_name')
        # 업종은 카카오 결과로 덮는다 (자동 추가 도구가 전부 '카페'로 넣어둔 문제)
        kc = str(d.get('category_name') or '')
        p['cat'] = kc.split('>')[-1].strip() or p.get('cat') or t['kind']
        cats = []
        if '고기' in kc or '갈비' in kc or '육류' in kc: cats.append('고기')
        if '한식' in kc or '칼국수' in kc or '샤브' in kc: cats.append('한식')
        if '일식' in kc or '우동' in kc or '초밥' in kc: cats.append('일식')
        if '면' in kc or '국수' in kc or '우동' in kc: cats.append('면')
        if '해물' in kc or '회' in kc.split('>')[-1]: cats.append('해산물')
        if cats: p['cats'] = cats
        p['addr'] = d.get('road_address_name') or t['addr']
        p['area'] = t['dong']
        p['gu']   = re.search(r'대전\s*(\S+구)', d.get('address_name') or t['addr']).group(1)
        if d.get('phone') and not p.get('phone'): p['phone'] = d['phone']
        p.pop('needsCoords', None)
        p['ownerCheckedAt'] = TODAY
        p.setdefault('evidence', []).append({'source': '대전공주 직접 확인', 'fields': ['주소', '좌표', '장소ID'], 'verifiedAt': TODAY})
        fixed.append((p['n'], p['addr'], d['id']))

    print('=== 확정한 곳 %d ===' % len(fixed))
    for n, a, i in fixed: print('  ✔ %-16s %s  (카카오 %s)' % (n, a, i))
    print('\n=== 손대지 않은 곳 %d ===' % len(held))
    for n, w in held: print('  ✖ %-16s %s' % (n, w))
    if DRY:
        print('\n--dry 라서 파일은 그대로 뒀습니다.'); return
    out = html[:m.start(2)] + json.dumps(P, ensure_ascii=False) + html[m.end(2):]
    open(path, 'w', encoding='utf-8').write(out)
    print('\nindex.html 에 반영했습니다.')


if __name__ == '__main__':
    main()
