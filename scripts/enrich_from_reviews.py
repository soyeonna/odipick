#!/usr/bin/env python3
"""구글 리뷰를 읽어 분위기·술 종류·대표 메뉴를 매장에 채운다.
   python3 scripts/enrich_from_reviews.py [--dry]

한 번에 다 받아 파일(data/greviews.json)에 저장해 두므로, 다시 돌릴 때는 구글을 또 부르지 않는다.
"""
import json, re, os, sys, subprocess, concurrent.futures as cf

DRY = '--dry' in sys.argv
CACHE = 'data/greviews.json'
h = open('index.html', encoding='utf-8').read()
GKEY = re.search(r"GOOGLE_KEY='([^']+)'", h).group(1)
m = re.search(r'(<script id="places" type="application/json">)(.*?)(</script>)', h, re.S)
P = json.loads(m.group(2))
cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}

def fetch(gid):
    out = subprocess.run(['curl', '-s', '-m', '25', f'https://places.googleapis.com/v1/places/{gid}?languageCode=ko',
        '-H', 'X-Goog-Api-Key: ' + GKEY, '-H', 'Referer: https://soyeonna.github.io/',
        '-H', 'X-Goog-FieldMask: reviews.text.text,editorialSummary,primaryTypeDisplayName'],
        capture_output=True, text=True).stdout
    try:
        d = json.loads(out)
        return {'rv': [r['text']['text'] for r in (d.get('reviews') or []) if r.get('text')],
                'ed': (d.get('editorialSummary') or {}).get('text', ''),
                'ty': (d.get('primaryTypeDisplayName') or {}).get('text', '')}
    except Exception:
        return {'rv': [], 'ed': '', 'ty': ''}

todo = [p['gid'] for p in P if p.get('gid') and p['gid'] not in cache and not p.get('closed')]
print(f'구글에서 새로 받을 곳 {len(todo)}곳 (이미 받아둔 곳 {len(cache)})')
if todo and not DRY:
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for gid, r in zip(todo, ex.map(fetch, todo)): cache[gid] = r
    os.makedirs('data', exist_ok=True)
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    print(f'받아서 저장 완료 ({CACHE})')

# ── 리뷰에서 뽑아낼 것들 ───────────────────────────────
MOOD = [
 (r'조용|한적|차분|아늑|편안', '조용한'),
 (r'예쁘|이쁘|감성|인테리어|사진\s*찍|인스타|분위기\s*좋', '예쁜'),
 (r'뷰가|전망|경치|야경|바라보|통창|풍경', '뷰맛집'),
 (r'넓|대형|층짜리|쾌적|공간이\s*커', '넓은'),
 (r'테라스|루프탑|야외|옥상|정원', '테라스'),
 (r'고급|근사|품격|모던하고\s*세련', '고급스러운'),
 (r'활기|왁자|시끌|북적', '활기찬'),
 (r'깔끔|정갈|청결|깨끗', '깔끔한'),
 (r'레트로|옛날\s*감성|빈티지|노포\s*감성', '레트로'),
 (r'이국|유럽|일본\s*감성|이태원|해외\s*같', '이국적'),
]
DRINK = [(r'생맥주|생맥', '생맥주'), (r'하이볼', '하이볼'), (r'산토리', '산토리'), (r'소주', '소주'),
         (r'맥주', '맥주'), (r'사케|정종', '사케'), (r'와인', '와인'), (r'막걸리|동동주', '막걸리'),
         (r'위스키', '위스키'), (r'칵테일', '칵테일'), (r'전통주', '전통주'), (r'수제맥주|크래프트', '수제맥주')]
# 메뉴로 보이는 말 (리뷰에서 자주 나오는 명사)
# 음식 이름처럼 보이는 말만 대표 메뉴로 인정한다 (리뷰 문장에서 엉뚱한 낱말이 딸려 오지 않게)
FOODWORD = re.compile(r'(탕|국밥|국수|칼국수|냉면|면|밥|덮밥|초밥|스시|롤|찜|구이|전골|찌개|볶음|무침|튀김|전$|회$|쌈|삼겹|목살|갈비|곱창|막창|족발|보쌈|순대|만두|떡볶이|김밥|파스타|피자|스테이크|리조또|뇨끼|버거|샌드위치|샐러드|포케|카레|돈까스|우동|라멘|짜장|짬뽕|탕수육|치킨|닭|오리|장어|새우|조개|굴|게장|물회|정식|세트|코스|모듬|한판|빵|케이크|타르트|마카롱|쿠키|크로플|와플|빙수|아이스크림|라떼|커피|에이드|주스|스무디|티$|차$)')
BAD = re.compile(r'(요$|서$|고$|며$|데$|것$|때$|들$|음$|임$|함$|네$|죠$|죵$|처음|가장|제일|진짜|정말|너무|조금|약간|다시|여기|저기|이번|다음|하고|해서|이라|라서|지인|함께|같이|모두|전부|하나|둘째|대전|방문|사장|직원|가격|주차)')
JOSA = re.compile(r'(을|를|이|가|은|는|과|와|도|의|에|으로|로|만|까지|부터|랑|이랑|하고)$')
def moods_of(text):
    out = []
    for pat, tag in MOOD:
        if len(re.findall(pat, text)) >= 1 and tag not in out: out.append(tag)
    return out[:3]
def drinks_of(text):
    return [tag for pat, tag in DRINK if re.search(pat, text)][:5]
def menu_of(text, name):
    # 음식 이름으로 보이는 말 중, 리뷰에 여러 번 나오거나 '시켰/맛있' 앞에 온 것만 고른다
    c = {}
    for x in re.findall(r'[가-힣A-Za-z]{2,12}', text):
        x = JOSA.sub('', x)                       # 뒤에 붙은 조사(~을, ~는)를 뗀다
        if len(x) < 2 or x in name: continue
        if BAD.search(x) or not FOODWORD.search(x): continue
        c[x] = c.get(x, 0) + 1
    top = sorted(c.items(), key=lambda kv: (-kv[1], -len(kv[0])))
    return [k for k, v in top if v >= 2][:2]

FOOD = {'한식','중식','일식','분식','양식','고기','술집','카페','디저트'}
BLAND = re.compile(r'^현지인들이 인정하는|^구글 리뷰 \d+개$')
nm = nd = ns = nv = 0
review_needed = []
for p in P:
    if p.get('closed'): continue
    c = cache.get(p.get('gid') or '')
    if not c: continue
    text = ' '.join(c['rv']) + ' ' + c['ed']
    if len(text) < 30: continue
    # 분위기
    if not p.get('mood'):
        mo = moods_of(text)
        if mo: p['mood'] = mo; nm += 1
    # 술 종류
    if (set(p.get('cats') or []) & {'술집', '한식', '고기', '일식', '양식', '중식'}) and not p.get('kw'):
        dr = drinks_of(text)
        if dr: p['kw'] = dr; nd += 1
    # 대표 메뉴
    if not p.get('sig'):
        mn = menu_of(text, p['n'])
        if mn: p['sig'] = ', '.join(mn); ns += 1
    # 알맹이 없는 설명은 목록에 모아 둔다 (문구는 사람이 쓴다)
    if BLAND.match(str(p.get('v') or '')):
        review_needed.append({'n': p['n'], 'cat': p.get('cat'), 'area': p.get('area'),
                              'ty': c['ty'], 'ed': c['ed'][:120], 'rv': [x[:180] for x in c['rv'][:2]]})

print(f'분위기 채움 {nm}곳 · 술 종류 {nd}곳 · 대표 메뉴 {ns}곳 · 설명 다시 쓸 곳 {len(review_needed)}곳')
if not DRY:
    h2 = h[:m.start(2)] + json.dumps(P, ensure_ascii=False) + h[m.end(2):]
    open('index.html', 'w', encoding='utf-8').write(h2)
    json.dump(review_needed, open('data/설명-다시쓸곳.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('설명 다시 쓸 곳: data/설명-다시쓸곳.json')
