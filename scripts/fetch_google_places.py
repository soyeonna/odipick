#!/usr/bin/env python3
"""구글 Places API(New)로 영업시간·전화·주차·평점·사진 채우기. 정식 통로라 저작권 문제 없음.
   구글 규칙: 장소 ID 말고는 30일 넘게 보관하면 안 되므로 daily-care 에서 매달 다시 돌린다.
   python3 scripts/fetch_google_places.py            # 전부 (최근 25일 안에 받은 곳은 건너뜀)
   python3 scripts/fetch_google_places.py --force    # 전부 다시
   python3 scripts/fetch_google_places.py 이름        # 한 곳만
"""
import json,subprocess,sys,re,math,datetime
h=open('index.html',encoding='utf-8').read()
KEY=re.search(r"GOOGLE_KEY='([^']+)'",h).group(1)
REF='https://soyeonna.github.io/'
def call(method,url,body=None,mask=''):
    cmd=['curl','-s','-m','30','-X',method,url,'-H','Content-Type: application/json','-H','X-Goog-Api-Key: '+KEY,'-H','Referer: '+REF,'-H','X-Goog-FieldMask: '+mask]
    if body is not None: cmd+=['-d',json.dumps(body,ensure_ascii=False)]
    out=subprocess.run(cmd,capture_output=True,text=True).stdout
    try: return json.loads(out)
    except Exception: return {'error':out[:200]}
def km(a,b): return math.sqrt(((a[1]-b[1])*88.8)**2+((a[0]-b[0])*111.1)**2)
i=h.find('<script id="places"'); i=h.find('>',i)+1; j=h.find('</script>',i)
P=json.loads(h[i:j])
force='--force' in sys.argv; only=[a for a in sys.argv[1:] if not a.startswith('--')]
today=datetime.date.today().isoformat()
n=0; miss=[]
for p in P:
    if p.get('closed') or not p.get('lat'): continue
    if only and p['n'] not in only: continue
    if not force and p.get('gAt') and (datetime.date.today()-datetime.date.fromisoformat(p['gAt'])).days<25: continue
    pid=p.get('gid')
    if not pid:
        q=p['n']+' '+(p.get('area') or '').split()[0]
        r=call('POST','https://places.googleapis.com/v1/places:searchText',
               {'textQuery':q,'languageCode':'ko','locationBias':{'circle':{'center':{'latitude':p['lat'],'longitude':p['lng']},'radius':400.0}},'pageSize':3},
               'places.id,places.displayName,places.location')
        cands=[]
        for c in r.get('places',[]):
            d=km((p['lat'],p['lng']),(c['location']['latitude'],c['location']['longitude']))
            nm=c['displayName']['text'].replace(' ','')
            base=re.sub(r'\s|본점|대전역|\(.*?\)','',p['n'])
            sim = base[:2] in nm or nm[:2] in base
            if d<=0.35 and sim: cands.append((d,c['id'],c['displayName']['text']))
        if not cands: miss.append(p['n']+('('+r['error'][:60]+')' if 'error' in r else '')); continue
        cands.sort(); pid=cands[0][1]; p['gid']=pid; p['gname']=cands[0][2]
    d=call('GET','https://places.googleapis.com/v1/places/'+pid+'?languageCode=ko',None,
           'id,nationalPhoneNumber,regularOpeningHours,parkingOptions,rating,userRatingCount,photos,googleMapsUri,priceLevel')
    if 'error' in d or not d.get('id'): miss.append(p['n']+'(상세)'); continue
    oh=d.get('regularOpeningHours',{})
    if oh.get('weekdayDescriptions'): p['ghours']=oh['weekdayDescriptions']
    if oh.get('periods'):   # 요일별 [요일(0=일), 여는 분, 닫는 분] — 영업 중 판단용
        per=[]
        for x in oh['periods']:
            o=x.get('open',{}); c=x.get('close')
            om=o.get('hour',0)*60+o.get('minute',0)
            cm=(c.get('hour',0)*60+c.get('minute',0)) if c else 24*60
            if c and c.get('day')!=o.get('day'): cm+=24*60
            per.append([o.get('day',0),om,cm])
        p['gperiods']=per
    if d.get('nationalPhoneNumber') and not p.get('phone'): p['phone']=d['nationalPhoneNumber']
    po=d.get('parkingOptions')
    if po is not None:
        p.setdefault('fac',{})
        has=any(po.get(k) for k in ['freeParkingLot','paidParkingLot','freeStreetParking','paidStreetParking','valetParking','freeGarageParking','paidGarageParking'])
        if p['fac'].get('parking') is None: p['fac']['parking']=bool(has)
        p['gpark']=[k for k in po if po[k]]
    if d.get('rating'): p['grating']=d['rating']; p['gcount']=d.get('userRatingCount',0)
    if d.get('priceLevel'): p['gprice']=d['priceLevel']
    ph=[]
    for x in (d.get('photos') or [])[:6]:
        au=(x.get('authorAttributions') or [{}])[0].get('displayName','')
        ph.append({'name':x['name'],'by':au})
    if ph: p['gphotos']=ph
    p['gmaps']=d.get('googleMapsUri'); p['gAt']=today; n+=1
    print('OK',p['n'],'|',p.get('gname'),'| 시간' if p.get('ghours') else '| -', '| 주차' if po is not None else '', '| 평점',p.get('grating'),'| 사진',len(ph))
open('index.html','w',encoding='utf-8').write(h[:i]+json.dumps(P,ensure_ascii=False,separators=(',',':'))+h[j:])
print('채움',n,'/ 못 찾음',len(miss)); print(', '.join(miss)[:1500])
