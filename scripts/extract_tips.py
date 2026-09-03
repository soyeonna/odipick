#!/usr/bin/env python3
"""릴스 캡션에서 시그니처 메뉴·먹는 조합·꿀팁(웨이팅/예약/주차/포장)을 뽑아 places에 넣는다.
   이미 손으로 적은 값(sig/combo/tip)은 덮어쓰지 않는다.   python3 scripts/extract_tips.py"""
import json,re
h=open('index.html',encoding='utf-8').read()
i=h.find('<script id="places"'); i=h.find('>',i)+1; j=h.find('</script>',i)
P=json.loads(h[i:j]); C=json.load(open('data/reel-captions.json',encoding='utf-8'))
def sents(t):
    t=re.sub(r'#\S+','',t); t=re.sub(r'@\S+','',t); t=re.sub(r'[📍⏰☎️🍴💰💝❤️‍🔥⬇️‼️✨🔺]','',t)
    return [s.strip(' .!?~') for s in re.split(r'(?<=[.!?요다죠음됨함])\s+|\n+',t) if 6<len(s.strip())<110]
n=0
for p in P:
    codes=(p.get('igs') or [])+([p['ig']] if p.get('ig') else [])
    cap=''
    for c in codes:
        if c in C and C[c].get('caption'): cap=C[c]['caption']; break
    if not cap or '이벤트' in cap[:80]: continue
    S=sents(cap)
    if not p.get('tip'):
        t=[s for s in S if re.search(r'웨이팅|줄 서|줄서|예약|브레이크|오픈런|포장|주차|재료 소진|마감|테이블링|캐치테이블|현금',s) and not re.search(r'이벤트|팔로우|태그',s)]
        if t: p['tip']=t[0][:90]; n+=1
    if not p.get('combo'):
        t=[s for s in S if re.search(r'조합|같이 먹|싸서|찍어|올려서|말아|비벼|킥|국룰|추천 조합|무조건 시켜',s) and not re.search(r'이벤트|팔로우',s)]
        if t: p['combo']=t[0][:90]; n+=1
    if not p.get('sig'):
        m=re.search(r'(?:제가\s*먹은\s*메뉴|먹은메뉴|메뉴)\s*[:：]?\s*([^\n]{2,40}?)\s*(?:₩|\d[\d,]{3,}\s*원?)',cap)
        if m: p['sig']=m.group(1).strip(' •-·')[:30]; n+=1
        else:
            t=[s for s in S if re.search(r'시그니처|대표 메뉴|대표메뉴|가장 유명|제일 유명|무조건 시켜',s)]
            if t: p['sig']=t[0][:60]; n+=1
open('index.html','w',encoding='utf-8').write(h[:i]+json.dumps(P,ensure_ascii=False,separators=(',',':'))+h[j:])
print('채운 항목',n,'| tip',sum(1 for p in P if p.get('tip')),'combo',sum(1 for p in P if p.get('combo')),'sig',sum(1 for p in P if p.get('sig')))
for p in P[:400]:
    if p.get('tip') or p.get('combo') or p.get('sig'):
        print('##',p['n']); 
        for k in ['sig','combo','tip']:
            if p.get(k): print('  ',k,':',p[k])
