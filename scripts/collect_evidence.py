#!/usr/bin/env python3
"""설명을 새로 쓸 매장의 '근거'를 모은다 (구글 요약·리뷰·업종·메뉴가격·릴스 캡션).
   결과는 data/evidence2.json — 이걸 보고 사람이 읽기 좋은 한 줄 설명을 쓴다.
   python3 scripts/collect_evidence.py"""
import json, re, subprocess, concurrent.futures as cf

h = open('index.html', encoding='utf-8').read()
KEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
P = json.loads(re.search(r'<script id="places" type="application/json">(.*?)</script>', h, re.S).group(1))
P = [p for p in P if not p.get('closed')]
HOOK = re.compile(r'[‼❗️]|!!|공유|저장|태그|댓글|팔로우|이벤트|떴|미쳤|실화|주목|알려드림')
def weak(p):
    v = (p.get('v') or '').strip()
    if not v: return '없음'
    if HOOK.search(v): return '릴스문구'
    if len(v) < 12: return '너무짧음'
    if re.fullmatch(r'[가-힣A-Za-z /,·]+', v) and len(v) < 20: return '밋밋함'
    return None
def why1(p):
    v = str(p.get('v') or '')
    for seg in re.split(r'\s*·\s*', v):
        seg = seg.strip()
        if not seg: continue
        if re.search(r'\d[\d,]*\s*원', seg):
            head = re.sub(r'[^.]*\d[\d,]*\s*원.*$', '', seg).strip(' .,')
            if len(head) >= 6: return head
            continue
        return seg
    return ''
need = [p for p in P if weak(p) or len(why1(p)) < 6]
R = json.load(open('data/reels_parsed.json', encoding='utf-8'))
def nm(s): return re.sub(r'\s', '', s or '')
caps = {nm(r.get('shop')): r for r in R if r.get('shop')}

FIELDS = 'displayName,primaryTypeDisplayName,editorialSummary,generativeSummary,reviews,rating,userRatingCount,priceLevel,servesBreakfast,servesBrunch,servesVegetarianFood,goodForGroups,goodForChildren,outdoorSeating,takeout,delivery,reservable,liveMusic,servesDessert,servesCoffee,servesBeer,servesWine,servesCocktails,menuForChildren,restroom,parkingOptions'
def detail(p):
    if not p.get('gid'): return {}
    out = subprocess.run(['curl', '-s', '-m', '30',
        f"https://places.googleapis.com/v1/places/{p['gid']}?languageCode=ko",
        '-H', 'X-Goog-Api-Key: ' + KEY, '-H', 'Referer: https://soyeonna.github.io/',
        '-H', 'X-Goog-FieldMask: ' + FIELDS], capture_output=True, text=True).stdout
    try: return json.loads(out)
    except Exception: return {}

print(f'설명 손봐야 할 곳 {len(need)}곳 — 구글 정보 받는 중')
with cf.ThreadPoolExecutor(max_workers=6) as ex:
    ds = list(ex.map(detail, need))

out = []
for p, d in zip(need, ds):
    c = caps.get(nm(p['n'])) or {}
    revs = [(r.get('text') or {}).get('text', '') for r in (d.get('reviews') or [])]
    feats = [k for k in ('goodForGroups','goodForChildren','outdoorSeating','servesDessert','servesCoffee',
                         'servesBeer','servesWine','servesCocktails','reservable','liveMusic','servesBreakfast','servesVegetarianFood') if d.get(k)]
    out.append({
        'n': p['n'], 'why': weak(p), 'now': p.get('v'), 'area': p.get('area'), 'cat': p.get('cat'),
        'cats': p.get('cats'), 'sit': p.get('sit'), 'src': p.get('src'), 'budget': p.get('budget'),
        'gtype': (d.get('primaryTypeDisplayName') or {}).get('text'),
        'gsum': (d.get('editorialSummary') or {}).get('text') or (d.get('generativeSummary') or {}).get('overview', {}).get('text'),
        'grating': d.get('rating'), 'gcount': d.get('userRatingCount'), 'feats': feats,
        'prices': c.get('prices'), 'hook': c.get('hook'),
        'caption': (c.get('caption') or '')[:600],
        'reviews': [r[:260].replace('\n', ' ') for r in revs[:5]],
    })
json.dump(out, open('data/evidence2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(f'근거 모음 저장: data/evidence2.json ({len(out)}곳, 리뷰 있는 곳 {sum(1 for x in out if x["reviews"])}곳)')
