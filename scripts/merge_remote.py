#!/usr/bin/env python3
"""원격(봇·다른 세션) 커밋과 내 index.html 을 필드 단위로 합친다.

  python3 scripts/merge_remote.py        # fetch → 합치기 → 빌드는 안 함 (커밋도 안 함)

규칙
 - 원격이 바꾼 필드만 받는다 (merge-base 와 비교).
 - 소연님 확인값(ownerCheckedAt 있는 곳)의 보호 필드는 안 덮는다. 단 우리 쪽에 비어 있으면 받는다.
 - 원격이 새로 넣은 가게는 추가한다.
 - index.html 밖의 파일은 내가 안 건드린 것이면 원격 버전을 받는다.
 - 원격이 index.html 의 코드(데이터 줄 밖)를 바꿨으면 멈추고 알려준다.
"""
import json, re, subprocess, sys
run=lambda *a: subprocess.run(list(a),capture_output=True,text=True).stdout
subprocess.run(['git','fetch','-q','origin'])
if not run('git','log','--oneline','HEAD..origin/main').strip():
    print("원격에 새 커밋 없음"); sys.exit(0)
print("원격 커밋:\n"+run('git','log','--oneline','HEAD..origin/main'))
base=run('git','merge-base','HEAD','origin/main').strip()
files=run('git','diff','--name-only',base,'origin/main').splitlines()
mine=run('git','diff','--name-only',base,'HEAD').splitlines()
RX=r'(<script id="places" type="application/json">)\s*(\[.*?\])\s*(</script>)'
def strip_data(src): return re.sub(RX,'<DATA>',src,flags=re.S)
if 'index.html' in files:
    if strip_data(run('git','show',base+':index.html'))!=strip_data(run('git','show','origin/main:index.html')):
        print("⚠ 원격이 index.html 코드도 바꿨습니다. 손으로 확인하세요."); sys.exit(2)
subprocess.run(['git','merge','-s','ours','--no-commit','-q','origin/main'])
for f in files:
    if f in ('index.html','dist/index.html') or f in mine: continue
    subprocess.run(['git','checkout','origin/main','--',f]); print("원격 버전 받음:",f)
if 'index.html' in files:
    places=lambda ref: json.loads(re.search(RX,run('git','show',ref+':index.html'),re.S).group(2))
    B={p['n']:p for p in places(base)}; R={p['n']:p for p in places('origin/main')}
    H=open('index.html',encoding='utf-8').read(); m=re.search(RX,H,re.S); L=json.loads(m.group(2))
    PROTECT={'fac','hours','cat','cats','n','addr','prices','budget','sig','v','why','caution','lat','lng','kid','kurl','kcat','igs','ig','cover','closed'}
    t=0; kept=[]
    for p in L:
        r=R.get(p['n']); b=B.get(p['n'])
        if not r or not b: continue
        owned=bool(p.get('ownerCheckedAt'))
        for k in set(r)|set(b):
            if r.get(k)==b.get(k): continue
            if owned and k in PROTECT:
                if k=='fac':
                    for fk,fv in (r.get('fac') or {}).items():
                        if p.setdefault('fac',{}).get(fk) is None: p['fac'][fk]=fv; t+=1
                elif p.get(k) in (None,'',[],{}) and r.get(k) not in (None,'',[],{}): p[k]=r[k]; t+=1
                else: kept.append((p['n'],k))
                continue
            p[k]=r[k]; t+=1
    added=[n for n in R if n not in B and n not in {p['n'] for p in L}]
    for n in added: L.append(R[n])
    H=H[:m.start(2)]+json.dumps(L,ensure_ascii=False)+H[m.end(2):]; open('index.html','w',encoding='utf-8').write(H)
    print(f"원격 변경 받아들임 {t}필드 / 지킨 것 {len(kept)} {kept[:5]} / 새 가게 {added}")
print("합치기 완료 — 이제 빌드하고 커밋하세요.")
