#!/usr/bin/env python3
"""구글 장소 검색(정식 API)으로 '대전 노포·현지인 맛집' 후보를 긁어 모아, 이미 있는 곳·뺀 곳·프랜차이즈를 제외하고
   리뷰 수 순으로 보여준다. 소연님이 번호로 고르면 add 한다.   python3 scripts/find_candidates.py"""
import json,re,subprocess,math
h=open('index.html',encoding='utf-8').read()
KEY=re.search(r"GOOGLE_KEY='([^']+)'",h).group(1)
i=h.find('<script id="places"'); i=h.find('>',i)+1; j=h.find('</script>',i)
P=json.loads(h[i:j]); R=json.load(open('data/removed-2026-09-03.json',encoding='utf-8'))
have={re.sub(r'\s','',p['n']) for p in P}|{re.sub(r'\s','',p['n']) for p in R}
gids={p.get('gid') for p in P if p.get('gid')}
fr=re.compile('|'.join(x.strip() for x in open('data/franchise-pattern.txt',encoding='utf-8') if x.strip()))
def search(q,pagetoken=None):
    body={'textQuery':q,'languageCode':'ko','locationRestriction':{'rectangle':{'low':{'latitude':36.18,'longitude':127.25},'high':{'latitude':36.50,'longitude':127.56}}},'pageSize':20}
    if pagetoken: body['pageToken']=pagetoken
    out=subprocess.run(['curl','-s','-m','30','-X','POST','https://places.googleapis.com/v1/places:searchText','-H','Content-Type: application/json','-H','X-Goog-Api-Key: '+KEY,'-H','Referer: https://soyeonna.github.io/','-H','X-Goog-FieldMask: places.id,places.displayName,places.formattedAddress,places.rating,places.userRatingCount,places.primaryTypeDisplayName,nextPageToken','-d',json.dumps(body,ensure_ascii=False)],capture_output=True,text=True).stdout
    try: return json.loads(out)
    except: return {}
GU=['동구','중구','서구','유성구','대덕구']
KW=['노포 맛집','오래된 식당','현지인 맛집','국밥','칼국수','냉면','중국집 노포','횟집','포장마차','고깃집 노포','백반','분식 노포']
C={}
for g in GU:
    for k in KW:
        r=search(f'대전 {g} {k}')
        for x in r.get('places',[]):
            nm=x['displayName']['text']; key=re.sub(r'\s','',nm)
            if x['id'] in gids or key in have or any(key.startswith(hv) or hv.startswith(key) for hv in have if len(hv)>=3): continue
            if fr.search(nm): continue
            if '대전' not in x.get('formattedAddress',''): continue
            c=C.setdefault(x['id'],{'n':nm,'addr':x.get('formattedAddress',''),'rating':x.get('rating'),'cnt':x.get('userRatingCount',0),'type':x.get('primaryTypeDisplayName',{}).get('text',''),'hits':0})
            c['hits']+=1
L=[c for c in C.values() if (c['rating'] or 0)>=4.0 and c['cnt']>=150]
L.sort(key=lambda c:(-c['hits'],-c['cnt']))
json.dump(L,open('data/candidates.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('후보',len(L))
for k,c in enumerate(L[:120],1):
    a=c['addr'].replace('대한민국 대전광역시 ','').split(' ')
    print(f"{k}. {c['n']} · {c['type']} · {' '.join(a[:2])} · ★{c['rating']} 리뷰{c['cnt']}")
