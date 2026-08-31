#!/usr/bin/env python3
"""릴스 캡션에서 새 가게를 뽑아 사이트 장소 목록에 넣는다.

이미 등록된 곳은 건드리지 않는다. 새로 넣는 곳에는 src="reel-auto" 를 붙여
소연님이 직접 정리하신 데이터와 구분할 수 있게 한다.
"""
import json, re, sys

CAPS = "data/reel-captions.json"
HTML = "index.html"

CATS = [
    (r"빵집|베이커리|케이크|디저트|카페|브런치|모찌|빙수|타르트", ["카페", "디저트"]),
    (r"고깃집|삼겹|한우|갈비|곱창|막창|고기|정육|오겹|목살", ["고기"]),
    (r"술집|포차|이자카야|와인|칵테일|바\b|호프|맥주|안주|혼술", ["술집"]),
    (r"일식|스시|초밥|라멘|우동|소바|텐동|오마카세|돈까스|돈카츠", ["일식"]),
    (r"중식|짜장|짬뽕|탕수육|마라", ["중식"]),
    (r"파스타|피자|스테이크|양식|리조또|브런치", ["양식"]),
    (r"떡볶이|김밥|분식|튀김|순대", ["분식"]),
    (r"한식|백반|국밥|칼국수|냉면|찌개|한정식|족발|보쌈|해장", ["한식"]),
]
SIT = [
    (r"데이트|분위기|감성|기념일|소개팅", "데이트"),
    (r"술집|포차|안주|술상|이자카야|와인|칵테일|맥주|소주", "술자리"),
    (r"가성비|저렴|무한리필|무제한|만원|천원|할인", "가성비"),
    (r"가족|부모님|외식|아이", "가족"),
    (r"회식|단체|모임", "친구모임"),
    (r"혼밥|혼술|1인", "혼밥"),
    (r"노포|년\s*전통|\d+년째|원조", "노포"),
]
FAC = [(r"주차", "parking"), (r"룸\b|룸이|프라이빗", "room"), (r"예약", "reserve"),
       (r"새벽|24시|늦게까지", "late"), (r"애견|반려", "pet"), (r"콜키지", "corkage")]


def clean_name(raw):
    n = re.sub(r"@\S+|#\S+", "", raw)
    n = n.strip(" '‘’\"“”~ㅣ|·,")
    return re.sub(r"\s*(대전)?\S{0,6}(본점|지점|점)\s*$", "", n).strip()


DONG2GU = {}


def cats_from_tags(cap):
    """해시태그가 캡션 전체보다 정확하다. #대전빵집 → 카페·디저트"""
    tags = " ".join(re.findall(r"#(\S+)", cap))
    hits = []
    for pat, cs in CATS:
        if re.search(pat, tags):
            hits += [c for c in cs if c not in hits]
    return hits[:3]


def parse(cap):
    m = re.search(r"📍\s*([^\n(（]{1,40})", cap)
    if not m:
        return None
    name = clean_name(m.group(1))
    name = re.sub(r"\s*\d{1,2}[.\-/]\d{1,2}.*$", "", name).strip()   # 이벤트 날짜 제거
    if len(name) < 2 or len(name) > 20:
        return None

    addr = re.search(r"[(（]\s*(대전[^)）]{2,40}|세종[^)）]{2,40})\s*[)）]", cap)
    full = addr.group(1).strip() if addr else ""
    gu = (re.search(r"(서구|유성구|중구|동구|대덕구)", full) or [None, None])[1] if full else None
    dong = re.search(r"(\S+동)\s*([\d-]+)?", full) if full else None
    area = (dong.group(0).strip() if dong else "")
    if not gu and dong:
        gu = DONG2GU.get(dong.group(1))          # 기존 데이터에서 동→구 찾기

    hours = re.search(r"⏰\s*([^\n]{2,60})", cap)
    phone = re.search(r"☎️?\s*([\d][\d\-]{6,15})", cap)
    menu = re.search(r"💖\s*영상 속 메뉴\s*\n((?:[^\n]+\n?){1,3})", cap)
    v = " · ".join(x.strip() for x in menu.group(1).strip().split("\n")[:3]) if menu else None

    cats = cats_from_tags(cap)
    if not cats:
        return None                              # 음식점으로 분류 안 되면 넣지 않는다
    sit = [s for pat, s in SIT if re.search(pat, cap)][:3]
    if "노포" in sit:
        sit.remove("노포")
        if "노포" not in cats:
            cats.append("노포")
    fac = {k: True for pat, k in FAC if re.search(pat, cap)}

    price = [int(x.replace(",", "")) for x in re.findall(r"([\d,]{4,7})\s*원", cap)]
    price = [p for p in price if 1000 <= p <= 300000]
    avg = sum(price) / len(price) if price else 0
    budget = None
    for lim, b in ((10000, 1), (20000, 2), (35000, 3), (60000, 4)):
        if avg and avg <= lim:
            budget = b
            break
    if avg > 60000:
        budget = 5

    return {"n": name, "cat": "/".join(cats) or None, "cats": cats or ["한식"],
            "area": area, "gu": gu, "hours": hours.group(1).strip() if hours else None,
            "budget": budget, "sit": sit or ["데이트"], "fac": fac, "cap": None,
            "ig": None, "link": None, "v": v, "src": "reel-auto",
            "phone": phone.group(1) if phone else None, "ph": None}


def main():
    dry = "--dry" in sys.argv
    caps = json.load(open(CAPS, encoding="utf-8"))
    html = open(HTML, encoding="utf-8").read()
    m = re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>', html)
    P = json.loads(m.group(1))
    have = {re.sub(r"\s", "", str(p.get("n", ""))) for p in P}
    for q in P:                                   # 기존 데이터로 동→구 표 만들기
        d = re.match(r"(\S+동)", str(q.get("area") or ""))
        if d and q.get("gu"):
            DONG2GU.setdefault(d.group(1), q["gu"])

    add = []
    seen = set()
    for code, v in caps.items():
        p = parse(v.get("caption", ""))
        if not p:
            continue
        key = re.sub(r"\s", "", p["n"])
        if key in seen or any(key in x or x in key for x in have):
            continue
        seen.add(key)
        p["ig"] = code
        add.append(p)

    print(f"새로 넣을 가게 {len(add)}곳")
    for p in add[:12]:
        print(f"  · {p['n']} [{p['gu'] or '?'} {p['area']}] {p['cat'] or ''} · {p['hours'] or '영업시간 미확인'}")
    if dry:
        print("\n※ --dry 라 실제로는 안 넣었습니다.")
        return
    P = P + add
    blk = '<script id="places" type="application/json">\n' + \
        json.dumps(P, ensure_ascii=False, separators=(",", ":")) + '\n</script>'
    html = html[:m.start()] + blk + html[m.end():]
    open(HTML, "w", encoding="utf-8").write(html)
    print(f"\n총 장소 {len(P)}곳이 되었습니다.")


if __name__ == "__main__":
    main()
