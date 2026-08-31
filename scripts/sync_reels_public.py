#!/usr/bin/env python3
"""
릴스 자동 가져오기 — 토큰도 로그인도 메타 개발자 앱도 필요 없다.

인스타그램이 공개 프로필용으로 내려주는 정보를 그대로 읽는다.
최근 12개는 한 번에, --all 을 붙이면 과거 것까지 넘겨가며 가져온다.

  python3 scripts/sync_reels_public.py           # 최근 것만 확인해서 새 릴스 추가
  python3 scripts/sync_reels_public.py --all     # 과거 릴스까지 전부
  python3 scripts/sync_reels_public.py --dry     # 실제로 안 고치고 뭐가 바뀔지만 보여줌

손으로 다듬어 둔 문구는 절대 덮어쓰지 않는다. 없는 릴스만 새로 넣는다.
"""
import json, re, sys, time, html as H, base64, io, os
import subprocess

USER = "_princesspick_"
HTML_FILE = "index.html"
DATA_FILE = "data/reels_public.json"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126 Safari/537.36")
APP_ID = "936619743392459"
THUMB_W = 320


def get(url, headers=None, binary=False):
    """맥에 파이썬 인증서가 없어도 되도록 curl 로 받는다."""
    cmd = ["curl", "-sS", "--fail", "--max-time", "30", "-A", UA]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    cmd.append(url)
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return raw if binary else raw.decode("utf-8", "ignore")


def fetch_page():
    """공개 프로필 정보. 최근 12개까지만 내려온다.

    과거 것까지 넘겨보는 통로는 로그인을 요구해서 쓸 수 없다.
    대신 매일 자동으로 도니까 새 릴스는 빠짐없이 들어온다.
    """
    url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={USER}"
    d = json.loads(get(url, {"x-ig-app-id": APP_ID}))
    return d["data"]["user"]["edge_owner_to_timeline_media"]


def caption_of(node):
    e = node["edge_media_to_caption"]["edges"]
    return e[0]["node"]["text"] if e else ""


def hook_of(caption):
    """캡션 첫 줄에서 후킹 문구만."""
    for line in caption.split("\n"):
        s = re.sub(r"#[^\s#]+", "", line).strip()
        s = s.strip("‼️❗️❕!·-–— ")
        if len(s) >= 4:
            return s[:40]
    return ""


def shop_of(caption):
    """📍 뒤에 가게 이름, 주소 괄호에서 동 이름. 형식은 "동이름 가게이름"."""
    m = re.search(r"📍\s*([^\n(（]{1,30})", caption)
    name = m.group(1).strip() if m else ""
    # 지점 이름은 뗀다: 대전둔산점 / 봉명본점 / 시청점 / 대전점 …
    name = re.sub(r"\s*(대전)?\S{0,6}(본점|지점|점)\s*$", "", name).strip()
    a = re.search(r"대전\s*\S+구\s*(\S+동)", caption)
    area = a.group(1) if a else ""
    if not area:  # 주소가 없으면 해시태그에서 동 이름
        h = re.search(r"#(\S*?동)맛집|#대전(\S*?동)", caption)
        area = next((g for g in (h.groups() if h else ()) if g), "")
    return f"{area} {name}".strip() if name else ""


CATS = ('빵집','베이커리','케이크','디저트','고깃집','냉면','국밥','스시','파스타',
        '이자카야','포차','와인바','술집','횟집','브런치','분식','치킨','피자','카페','맛집')
REP = r'(?:3대장|삼대장|3대|성지|원조|1위|최초|유일|유명|웨이팅|노포|줄서|끝판왕)'


def desc_of(caption, name):
    """가게 특성 한 줄. 릴스 후킹이 아니라 '이 집이 어떤 곳인지'."""
    # 평판 표현이 있으면 그걸 쓴다
    body = ""
    for line in caption.split("\n")[:6]:
        if re.search(REP, line):
            t = re.sub(r"#\S+", "", line)
            t = re.sub(r"^[^ㅣ|]{0,6}[ㅣ|]", "", t)          # 내돈내산ㅣ, 가족외식ㅣ 떼기
            t = re.sub(r"[‼❗❕!,🤍💖✨🎉📍⏰☎️️]", "", t).strip()
            t = re.sub(r"^(개인적으로|진짜|여기|완전|솔직히|속보)\s*", "", t)
            t = re.sub(r"(라고 생각하는|이라고 생각하는|인정하는).*$", "", t).strip()
            if name:
                t = re.sub(rf"\s*{re.escape(name)}.*$", "", t).strip()
            if 6 <= len(t) <= 28:
                body = t
                break
    if not body:  # 없으면 해시태그 업종
        tags = [re.sub(r"^(대전|\S*?동)", "", x) for x in re.findall(r"#(\S+)", caption)]
        body = next((c for c in CATS if c in tags), "")
    # 대표 메뉴 붙이기
    m = re.search(r"💖\s*영상 속 메뉴\s*\n(.+)", caption)
    menu = re.sub(r"\s*[\d,]+\s*(원|웡).*$", "", m.group(1).strip())[:20] if m else ""
    return " · ".join([x for x in (body, menu) if x])


def thumb_b64(url):
    """썸네일을 작게 줄여 파일 안에 심는다."""
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(get(url, binary=True))).convert("RGB")
        w, h = im.size
        im = im.resize((THUMB_W, int(h * THUMB_W / w)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=70, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return None


def block(html, tag):
    m = re.search(rf'<script id="{tag}" type="application/json">([\s\S]*?)</script>', html)
    if not m:
        sys.exit(f"index.html 안에서 {tag} 블록을 못 찾았습니다.")
    return json.loads(m.group(1)), m


def put(html, tag, data):
    new = (f'<script id="{tag}" type="application/json">\n'
           + json.dumps(data, ensure_ascii=False, indent=1) + "\n</script>")
    return re.sub(rf'<script id="{tag}" type="application/json">[\s\S]*?</script>',
                  lambda _: new, html, count=1)


def main():
    dry = "--dry" in sys.argv
    if "--all" in sys.argv:
        print("※ --all 은 쓸 수 없습니다. 인스타그램이 과거 게시물은 로그인 없이 안 내줍니다.")

    e = fetch_page()
    nodes = [x["node"] for x in e["edges"]]
    print(f"인스타그램에서 최근 게시물 {len(nodes)}개 확인")

    reels = [n for n in nodes if n.get("is_video")]

    # 분석용 원본 저장
    os.makedirs("data", exist_ok=True)
    full = [{
        "code": n["shortcode"],
        "at": n["taken_at_timestamp"],
        "views": n.get("video_view_count"),
        "likes": n["edge_liked_by"]["count"],
        "comments": n["edge_media_to_comment"]["count"],
        "caption": caption_of(n),
    } for n in reels]
    prev = {}
    if os.path.exists(DATA_FILE):
        prev = {r["code"]: r for r in json.load(open(DATA_FILE, encoding="utf-8"))}
    for r in full:
        prev[r["code"]] = r
    merged = sorted(prev.values(), key=lambda r: r["at"], reverse=True)
    if not dry:
        json.dump(merged, open(DATA_FILE, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)

    # index.html 에 새 릴스만 추가
    html = open(HTML_FILE, encoding="utf-8").read()
    rd, _ = block(html, "reels")
    thumbs, _ = block(html, "thumbs")
    have = {i["code"] for i in rd["items"]}

    added = []
    for n in reels:
        c = n["shortcode"]
        if c in have:
            continue
        cap = caption_of(n)
        shop = shop_of(cap)
        name = shop.split(" ", 1)[-1] if shop else ""
        item = {"code": c, "hook": hook_of(cap), "shop": shop,
                "desc": desc_of(cap, name)}
        if c not in thumbs:
            t = thumb_b64(n["display_url"])
            if t:
                thumbs[c] = t
        added.append(item)

    if not added:
        print("새로 추가할 릴스 없음. 이미 최신입니다.")
    else:
        rd["items"] = added + rd["items"]
        rd["syncedAt"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        rd["source"] = "instagram-public"
        print(f"\n새 릴스 {len(added)}개:")
        for a in added:
            print(f"  · {a['shop'] or '가게이름 확인필요'} — {a['hook']}")
        if not dry:
            html = put(html, "reels", rd)
            html = put(html, "thumbs", thumbs)
            open(HTML_FILE, "w", encoding="utf-8").write(html)

    print(f"\n분석용 데이터: 릴스 {len(merged)}개 기록 ({DATA_FILE})")
    if dry:
        print("※ --dry 라서 실제로는 아무것도 안 고쳤습니다.")


if __name__ == "__main__":
    main()
