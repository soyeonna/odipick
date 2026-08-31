#!/usr/bin/env python3
"""폐업 의심 가게를 찾아 따로 표시한다.

카카오 지도에서 검색되지 않으면 폐업 신호로 본다. 자동으로 지우지는 않는다 —
`closed: true` 만 붙이고, 사람이 확인한 뒤 정리한다.

  python3 scripts/check_closed.py          # 확인만
  python3 scripts/check_closed.py --apply  # index.html 에 표시까지
필요: .env 의 KAKAO_REST_KEY
"""
import json, os, re, subprocess, sys, time, urllib.parse

HTML = "index.html"


def kakao(q, key):
    u = ("https://dapi.kakao.com/v2/local/search/keyword.json?size=5&query="
         + urllib.parse.quote(q))
    r = subprocess.run(["curl", "-sS", "--max-time", "15",
                        "-H", f"Authorization: KakaoAK {key}", u], capture_output=True)
    try:
        return json.loads(r.stdout).get("documents", [])
    except Exception:
        return []


def main():
    key = ""
    if os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if line.strip().startswith("KAKAO_REST_KEY"):
                key = line.split("=", 1)[1].strip()
    if not key:
        sys.exit("KAKAO_REST_KEY 가 .env 에 없습니다. 카카오 개발자 사이트에서 키를 받아 넣어주세요.")

    apply_ = "--apply" in sys.argv
    html = open(HTML, encoding="utf-8").read()
    m = re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>', html)
    P = json.loads(m.group(1))

    gone, moved = [], []
    for i, p in enumerate(P, 1):
        n = p.get("n")
        if not n:
            continue
        dong = re.match(r"(\S+동)", str(p.get("area") or ""))
        tries = []
        if dong: tries.append(f"대전 {dong.group(1)} {n}")
        tries += [f"대전 {n}", n]
        docs = []
        for q in tries:
            docs = kakao(q, key)
            if docs: break
        if not docs:
            p["closed"] = True
            gone.append(n)
        else:
            p.pop("closed", None)
            addr = docs[0].get("road_address_name") or docs[0].get("address_name") or ""
            d2 = re.search(r"(\S+동)", p.get("area") or "")
            if d2 and d2.group(1) not in addr:
                moved.append(f"{n} → {addr}")
        if i % 50 == 0:
            print(f"  {i}/{len(P)} …", flush=True)
        time.sleep(0.25)

    print(f"\n정상 {len(P)-len(gone)}곳 · 폐업 의심 {len(gone)}곳 · 위치 바뀐 듯 {len(moved)}곳")
    if gone:
        print("폐업 의심:", ", ".join(gone))
    if moved:
        print("확인 필요:", " / ".join(moved[:20]))

    if apply_:
        blk = ('<script id="places" type="application/json">\n'
               + json.dumps(P, ensure_ascii=False, separators=(",", ":")) + '\n</script>')
        open(HTML, "w", encoding="utf-8").write(html[:m.start()] + blk + html[m.end():])
        print("\nindex.html 에 표시했습니다. (closed: true)")


if __name__ == "__main__":
    main()
