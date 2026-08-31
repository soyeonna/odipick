#!/usr/bin/env python3
"""릴스 주소 목록(data/reel-codes.txt)으로 캡션을 하나씩 받아온다.

로그인도 토큰도 없이, 인스타그램이 링크 미리보기용으로 공개하는 정보를 읽는다.
받은 것은 data/reel-captions.json 에 쌓이고, 이미 받은 건 건너뛴다.
"""
import json, os, re, subprocess, sys, time, html as H

CODES = "data/reel-codes.txt"
OUT = "data/reel-captions.json"
BOT = "facebookexternalhit/1.1"

got = {}
if os.path.exists(OUT):
    got = json.load(open(OUT, encoding="utf-8"))

codes = [c.strip() for c in open(CODES, encoding="utf-8") if c.strip()]
todo = [c for c in codes if c not in got]
print(f"전체 {len(codes)}개 · 이미 받음 {len(got)}개 · 이번에 받을 것 {len(todo)}개")

fail = 0
for i, c in enumerate(todo, 1):
    try:
        r = subprocess.run(
            ["curl", "-sS", "--max-time", "20", "-A", BOT,
             f"https://www.instagram.com/p/{c}/"],
            capture_output=True)
        b = r.stdout.decode("utf-8", "ignore")
        m = re.search(r'og:description[^>]*content="([^"]*)"', b)
        if not m:
            fail += 1
            continue
        t = H.unescape(m.group(1))
        # "2,994 likes, 46 comments - _princesspick_ on August 25, 2026: "캡션"" 형태
        meta = re.match(r'([\d,]+) likes?, ([\d,]+) comments? - \S+ on ([^:]+): "(.*)"\s*\.?\s*$',
                        t, re.S)
        if meta:
            got[c] = {"likes": int(meta.group(1).replace(",", "")),
                      "comments": int(meta.group(2).replace(",", "")),
                      "date": meta.group(3).strip(),
                      "caption": meta.group(4)}
        else:
            got[c] = {"caption": t}
    except Exception:
        fail += 1
    if i % 25 == 0:
        json.dump(got, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"  {i}/{len(todo)} …")
    time.sleep(0.7)

json.dump(got, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"끝. 캡션 {len(got)}개 확보, 실패 {fail}개 → {OUT}")
