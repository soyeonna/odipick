#!/usr/bin/env python3
"""소연님 검수 엑셀(확정수정 시트)을 index.html 에 반영한다.

  ~/.agent-reach-venv/bin/python scripts/apply_audit_xlsx.py <xlsx> [--dry]

상태별 처리
  수정 확정      → 전부 반영
  정보 보강      → 이름·주소는 두고 나머지 반영
  가격 재확인    → 가격만 빼고 반영 (충돌 표시)
  지점 확인 필요 → 위치(이름·주소·좌표)는 손대지 않고 설명·메뉴만 반영, 검수 표시
'근거 없음'은 false 가 아니라 모름(None). 추측으로 채우지 않는다.
"""
import json, re, sys, datetime
from openpyxl import load_workbook
XLSX=sys.argv[1]; DRY='--dry' in sys.argv; TODAY=datetime.date.today().isoformat()

def parse_prices(txt):
    out=[]
    for part in re.split(r'\s*/\s*', str(txt or '')):
        m=re.search(r'(.+?)\s*([\d,]{4,})\s*원', part)
        if not m: continue
        name=m.group(1).strip(); p=int(m.group(2).replace(',',''))
        t='groupMenu' if re.search(r'\d\s*[-–~]\s*\d\s*인|중\(|대\(|2~3인|2–3인', name) else \
          'side' if re.search(r'미나리|반찬|사리|볶음밥|공기밥', name) else \
          'set' if re.search(r'코스|정식|한정식|세트', name) else 'main'
        row={'m':name,'p':p,'type':t}
        gm=re.search(r'(\d)\s*[-–~]\s*(\d)\s*인', name)
        if gm: row['minPeople']=int(gm.group(1)); row['maxPeople']=int(gm.group(2))
        out.append(row)
    return out

def budget_from(prices):
    main=[x['p'] for x in prices if x['type'] in ('main','set')]
    grp=[x for x in prices if x['type']=='groupMenu' and x.get('minPeople')]
    per=None
    if grp: g=grp[0]; per=g['p']/((g['minPeople']+g.get('maxPeople',g['minPeople']))/2)
    elif main: per=min(main)
    if per is None: return None
    return 1 if per<=10000 else 2 if per<=20000 else 3 if per<=30000 else 4 if per<=50000 else 5

def parking_from(txt):
    t=str(txt or '')
    if not t or '확인 필요' in t and '주차장' not in t: return None, None, t or None
    if re.search(r'전용', t): return True,'전용',t
    if re.search(r'건물|빌딩|지하주차장', t): return True,'건물',t
    if re.search(r'제공|가능|이용', t): return True,'가게',t
    return None,None,t

def room_from(txt):
    t=str(txt or '')
    if not t or '근거 없음' in t: return None
    if re.search(r'개별룸|프라이빗|룸 정보|단체룸|확인', t): return True
    return None

H=open('index.html',encoding='utf-8').read()
m=re.search(r'(<script id="places" type="application/json">)\s*(\[.*?\])\s*(</script>)',H,re.S)
P=json.loads(m.group(2))
ws=load_workbook(XLSX,data_only=True)['확정수정']
hdr=[h for h in next(ws.iter_rows(min_row=1,max_row=1,values_only=True)) if h]
done=[]; held=[]
for r in ws.iter_rows(min_row=2, values_only=True):
    if not r[0]: continue
    row=dict(zip(hdr, r[:len(hdr)]))
    old,new,status=row['기존명'],row['확정명'],str(row['상태'] or '')
    key=re.sub(r'\s*(만년동점|대전점|대전본점|대전둔산점|대전시청점|대전엑스포)$','',old).strip()
    hits=[p for p in P if key in p['n']]
    if len(hits)!=1:
        held.append((old, f'목록에서 {len(hits)}곳 매칭')); continue
    p=hits[0]; ch=[]
    loc_ok = status in ('수정 확정','정보 보강','가격 재확인')
    if status=='수정 확정' and new and new!=p['n']: p['n']=new; ch.append('이름')
    if loc_ok and row.get('주소') and '카카오 장소 ID 기준' not in str(row['주소']):
        p['addr']=str(row['주소']).strip(); ch.append('주소')
    if row.get('업종'): p['cat']=str(row['업종']).strip(); ch.append('업종')
    if row.get('영업시간'):
        p['hours']=str(row['영업시간']).strip(); p['hoursCheckedAt']=TODAY; ch.append('영업시간')
    pk,pt,pn=parking_from(row.get('주차'))
    f=p.setdefault('fac',{})
    if pk is not None: f['parking']=pk; p['parkType']=pt; ch.append('주차')
    if pn: p['parkNote']=pn
    rm=room_from(row.get('룸'))
    if rm is not None: f['room']=rm; ch.append('룸')
    if row.get('대표메뉴'): p['sig']=str(row['대표메뉴']).strip(); ch.append('대표메뉴')
    if status!='가격 재확인':
        pr=parse_prices(row.get('메뉴·가격'))
        # 대표메뉴에 "(2–3인)" 처럼 인원이 적혀 있으면 같은 이름의 가격에 붙인다 (공유 메뉴를 1인 가격으로 계산하지 않기)
        sm=re.search(r'^(.*?)\s*\(?(\d)\s*[-–~]\s*(\d)\s*인\)?', str(row.get('대표메뉴') or ''))
        if sm:
            for x in pr:
                if x['m'].replace(' ','') in sm.group(1).replace(' ','') or sm.group(1).replace(' ','') in x['m'].replace(' ',''):
                    x['type']='groupMenu'; x['minPeople']=int(sm.group(2)); x['maxPeople']=int(sm.group(3))
        if pr:
            p['prices']=pr; ch.append(f'메뉴 {len(pr)}개')
            b=budget_from(pr)
            if b: p['budget']=b; ch.append(f'예산={b}')
    else:
        p['priceReview']=str(row.get('메뉴·가격') or '')
    if row.get('오디픽 소개글'): p['v']=str(row['오디픽 소개글']).strip(); ch.append('소개')
    if row.get('추천 이유'): p['why']=str(row['추천 이유']).strip(); ch.append('추천이유')
    if row.get('주의점'): p['caution']=str(row['주의점']).strip(); ch.append('주의점')
    if row.get('리뷰 취합'): p['reviewSummary']=str(row['리뷰 취합']).strip()
    if status=='지점 확인 필요': p['needsReview']='지점 확인 필요'; ch.append('⚠ 지점확인')
    conf={'높음':'high','중간':'medium','낮음':'low'}.get(str(row.get('신뢰도') or '').strip())
    if conf: p['confidence']=conf
    p['ownerCheckedAt']=TODAY
    p.setdefault('evidence',[]).append({'source':'대전공주 검수 엑셀 v1','fields':ch,'verifiedAt':TODAY,
                                        'refs':[u for u in str(row.get('출처') or '').split() if u.startswith('http')]})
    if '카페' in str(p.get('cats') or []) and status in ('수정 확정',) and '카페' not in str(row.get('업종')):
        p['cats']=[c for c in p['cats'] if c not in ('카페','디저트')]; ch.append('카페분류 제거')
    done.append((p['n'], status, ', '.join(ch)))

print(f"=== 반영 {len(done)}곳 ===")
for n,s,c in done: print(f"  {n:<18} [{s}] {c}")
if held:
    print(f"\n=== 보류 {len(held)}곳 ===")
    for n,w in held: print(f"  {n}: {w}")
if DRY: print("\n--dry"); sys.exit(0)
H=H[:m.start(2)]+json.dumps(P,ensure_ascii=False)+H[m.end(2):]
open('index.html','w',encoding='utf-8').write(H)
print("\nindex.html 반영")
