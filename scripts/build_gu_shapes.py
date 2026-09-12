#!/usr/bin/env python3
"""대전 5개 구의 실제 경계를 받아 지도 도형을 다시 만든다.

  python3 scripts/build_gu_shapes.py [--dry]

index.html 안의 GU_SHAPES(구 모양)와 GU_LABEL(구 이름 위치)을 통째로 갈아끼운다.
원본은 통계청 2013년 시군구 경계(공개 자료)이고, 대전 구 경계는 그 뒤로 바뀌지 않았다.
"""
import json, math, os, re, subprocess, sys, tempfile

DRY  = '--dry' in sys.argv
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = ('https://raw.githubusercontent.com/southkorea/southkorea-maps/'
        'master/kostat/2013/json/skorea_municipalities_geo.json')
WANT = ['유성구', '대덕구', '동구', '중구', '서구']      # 그리는 순서 (넓은 것부터)


def fetch():
    cache = os.path.join(tempfile.gettempdir(), 'skorea_municipalities_full.json')
    if not os.path.exists(cache) or os.path.getsize(cache) < 1000000:
        print('경계 자료를 받는 중…')
        subprocess.run(['curl', '-sSL', '-o', cache, SRC], check=True)
    return json.load(open(cache, encoding='utf-8'))


def rings(geom):
    """폴리곤 바깥선만 모은다 (구멍·섬은 무시)."""
    out = []
    if geom['type'] == 'Polygon':
        out.append(geom['coordinates'][0])
    else:
        for poly in geom['coordinates']:
            out.append(poly[0])
    return out


def simplify(pts, tol):
    """구불구불한 선을 펴서 점 수를 줄인다 (Douglas-Peucker)."""
    if len(pts) < 3:
        return pts
    a, b = pts[0], pts[-1]
    dx, dy = b[0] - a[0], b[1] - a[1]
    den = math.hypot(dx, dy) or 1e-9
    worst, idx = 0.0, 0
    for i in range(1, len(pts) - 1):
        p = pts[i]
        d = abs(dy * (p[0] - a[0]) - dx * (p[1] - a[1])) / den
        if d > worst:
            worst, idx = d, i
    if worst <= tol:
        return [a, b]
    return simplify(pts[:idx + 1], tol)[:-1] + simplify(pts[idx:], tol)


def centroid(pts):
    """면적 중심 — 이름표를 놓을 자리."""
    a = cx = cy = 0.0
    n = len(pts)
    for i in range(n):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % n]
        cr = x0 * y1 - x1 * y0
        a += cr; cx += (x0 + x1) * cr; cy += (y0 + y1) * cr
    if abs(a) < 1e-9:
        return pts[0]
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


def main():
    html = open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    proj = json.loads(re.search(r'var GU_PROJ=(\{.*?\});', html, re.S).group(1))

    def to_svg(lon, lat):
        return ((lon - proj['minx']) * proj['sx'] * proj['cos'],
                proj['h'] - (lat - proj['miny']) * proj['sx'])

    feats = {f['properties'].get('name'): f for f in fetch()['features']
             if f['properties'].get('name') in WANT
             and 127.2 < rings(f['geometry'])[0][0][0] < 127.6
             and 36.1 < rings(f['geometry'])[0][0][1] < 36.6}
    missing = [g for g in WANT if g not in feats]
    if missing:
        sys.exit('경계 자료에서 못 찾은 구: ' + ', '.join(missing))

    shapes, labels = {}, {}
    for gu in WANT:
        ring = max(rings(feats[gu]['geometry']), key=len)      # 제일 큰 덩어리만
        pts = [to_svg(lon, lat) for lon, lat in ring]
        if pts[0] == pts[-1]:                                  # 닫힌 고리의 중복 끝점을 뺀다
            pts = pts[:-1]                                     # (안 빼면 시작점=끝점이라 선이 한 점으로 뭉개진다)
        for tol in (0.06, 0.12, 0.25, 0.5, 1.0):            # 점이 140개 밑으로 떨어질 때까지
            s = simplify(pts, tol)
            if len(s) <= 140:
                break
        d = 'M' + ' L'.join('%.1f,%.1f' % p for p in s) + 'Z'
        shapes[gu] = d
        cx, cy = centroid(s)
        labels[gu] = [round(cx, 1), round(cy, 1)]
        print('  %-5s 점 %3d개 → %5.1fKB' % (gu, len(s), len(d) / 1024))

    new_shapes = 'var GU_SHAPES=' + json.dumps(shapes, ensure_ascii=False) + ';'
    new_labels = 'var GU_LABEL=' + json.dumps(labels, ensure_ascii=False) + ';'
    if DRY:
        print('\n--dry 라서 파일은 그대로 뒀습니다.')
        return
    out = re.sub(r'var GU_SHAPES=\{.*?\};', lambda m: new_shapes, html, count=1, flags=re.S)
    out = re.sub(r'var GU_LABEL=\{.*?\};',  lambda m: new_labels, out,  count=1, flags=re.S)
    open(os.path.join(ROOT, 'index.html'), 'w', encoding='utf-8').write(out)
    print('\nindex.html 의 구 경계를 실제 경계로 바꿨습니다.')
    print('확인: python3 scripts/selftest.py')


if __name__ == '__main__':
    main()
