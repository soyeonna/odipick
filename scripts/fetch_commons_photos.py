#!/usr/bin/env python3
"""위키미디어 공용(Wikimedia Commons)의 자유 이용 사진(CC·퍼블릭도메인)을 명소 커버로 넣는다.
   식당은 거의 없고 미술관·공원·성심당 같은 명소만 잡힌다. 출처·작가·라이선스는 photoSrc에 남긴다.
   python3 scripts/fetch_commons_photos.py            # 커버 없는 체험·나들이·숙소·성심당 대상
"""
import json,subprocess,urllib.parse,re,io,os,sys
from PIL import Image
UA='odipick/1.0 (https://github.com/soyeonna/odipick; nasoyeon6@gmail.com)'
def curl(u):
    return subprocess.run(['curl','-s','-L','-m','40','-A',UA,u],capture_output=True).stdout
def commons(q):
    u='https://commons.wikimedia.org/w/api.php?'+urllib.parse.urlencode({'action':'query','generator':'search','gsrsearch':q,'gsrnamespace':6,'gsrlimit':6,'prop':'imageinfo','iiprop':'url|extmetadata|size','iiurlwidth':1200,'format':'json'})
    try: pages=json.loads(curl(u)).get('query',{}).get('pages',{})
    except Exception: return []
    res=[]
    for pg in pages.values():
        ii=(pg.get('imageinfo') or [{}])[0]; md=ii.get('extmetadata',{})
        lic=md.get('LicenseShortName',{}).get('value','')
        if not any(x in lic for x in ['CC','Public domain','CC0']): continue
        if re.search(r'logo|map|지도|표지석|monument|disabled|공덕비',pg['title'],re.I): continue
        if (ii.get('width') or 0)<600 or (ii.get('height') or 0)<400: continue
        artist=re.sub('<[^>]+>','',md.get('Artist',{}).get('value','')).strip()[:30]
        res.append({'title':pg['title'],'lic':lic,'artist':artist,'url':ii.get('thumburl') or ii.get('url')})
    return res
def crop916(raw,out):
    im=Image.open(io.BytesIO(raw)).convert('RGB'); w,h=im.size
    tw,th=540,960
    if w/h>tw/th: nw=int(h*tw/th); im=im.crop(((w-nw)//2,0,(w-nw)//2+nw,h))
    else: nh=int(w*th/tw); im=im.crop((0,(h-nh)//2,w,(h-nh)//2+nh))
    im.resize((tw,th),Image.LANCZOS).save(out,'WEBP',quality=82)
h=open('index.html',encoding='utf-8').read()
i=h.find('<script id="places"'); i=h.find('>',i)+1; j=h.find('</script>',i)
P=json.loads(h[i:j])
ALIAS={'엑스포과학공원 한빛탑':'Expo Bridge Daejeon Hanbit Tower','성심당 케익부띠끄':'Sungsimdang','대전예술의전당':'Daejeon Arts Center','반지공방 아뜰리에호수 대전':None,'런던스테이지':None,'오디티모드':None,'라븐스튜디오':None,'하늘강 아뜰리에':None,'헤레디움':'Heredium Daejeon'}
targets=[p for p in P if not p.get('closed') and not(p.get('cover') or (p.get('ph') and not p.get('noCardPhoto')))
         and (any(c in (p.get('cats') or []) for c in ['체험','나들이','숙소']) or '성심당' in p['n'])]
n=0
for p in targets:
    q=ALIAS.get(p['n'],p['n'])
    if q is None: continue
    r=commons(q) or commons(p['n'])
    if not r: print('없음',p['n']); continue
    pick=r[0]; raw=curl(pick['url'])
    if len(raw)<20000: print('다운 실패',p['n']); continue
    key='cm'+re.sub(r'[^0-9A-Za-z가-힣]','',p['n'])[:12]
    os.makedirs('img',exist_ok=True); crop916(raw,f'img/{key}.webp')
    p['cover']=key; p['ph']=key; p['noCardPhoto']=False
    p['photoSrc']=f"Wikimedia Commons · {pick['artist'] or '작가 미상'} · {pick['lic']}"
    n+=1; print('적용',p['n'],'←',pick['title'][:40],'|',pick['lic'])
open('index.html','w',encoding='utf-8').write(h[:i]+json.dumps(P,ensure_ascii=False,separators=(',',':'))+h[j:])
print('적용',n,'곳')
