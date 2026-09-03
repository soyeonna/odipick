#!/usr/bin/env python3
"""전국주차장정보표준데이터(공공데이터포털, 정식 API)에서 대전 공영주차장을 받아 data/parking.json 으로 저장.
   사이트에서는 가게마다 '가까운 공영주차장 · 도보 N분'을 계산해 보여준다.
   data.go.kr 에서 '전국주차장정보표준데이터' 활용신청(자동승인)이 돼 있어야 한다.   python3 scripts/fetch_parking.py"""
import json,subprocess,urllib.parse
raw=[l.split('=',1)[1].strip().strip('"\'') for l in open('.env') if l.startswith('DATA_GO_KR_KEY')][0]
key=urllib.parse.quote(urllib.parse.unquote(raw),safe='')
lots=[]; page=1
while True:
    u=f"http://api.data.go.kr/openapi/tn_pubr_prkplce_info_api?serviceKey={key}&pageNo={page}&numOfRows=500&type=json&lnmadr=%EB%8C%80%EC%A0%84%EA%B4%91%EC%97%AD%EC%8B%9C"
    d=json.loads(subprocess.run(['curl','-s','-m','60',u],capture_output=True,text=True).stdout)
    body=d.get('response',{}).get('body',{}); items=body.get('items') or []
    if isinstance(items,dict): items=items.get('item',[])
    for x in items:
        try: lat=float(x.get('latitude') or 0); lng=float(x.get('longitude') or 0)
        except: continue
        if not(36.1<lat<36.6 and 127.2<lng<127.6): continue
        lots.append({'n':x.get('prkplceNm'),'lat':lat,'lng':lng,'type':x.get('prkplceType'),'fee':x.get('parkingchrgeInfo'),'cnt':x.get('prkcmprt'),'addr':x.get('rdnmadr') or x.get('lnmadr')})
    total=int(body.get('totalCount') or 0)
    if page*500>=total or not items: break
    page+=1
json.dump(lots,open('data/parking.json','w',encoding='utf-8'),ensure_ascii=False)
print('대전 주차장',len(lots),'곳 저장')
