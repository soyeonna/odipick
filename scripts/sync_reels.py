#!/usr/bin/env python3
"""
대전공주 릴스 → 오디픽 자동 동기화

인스타그램에 올린 릴스를 전부 가져와 index.html 의 릴스 데이터를 갈아끼운다.
기존 게시물도 첫 실행에 함께 들어온다.

실행:  python3 scripts/sync_reels.py
       python3 scripts/sync_reels.py --months 12     (최근 12개월만)
"""
import json, os, re, sys, time, urllib.request, urllib.parse
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "index.html")
FIELDS = "id,caption,media_type,media_product_type,permalink,thumbnail_url,media_url,timestamp,like_count,comments_count"


def load_env():
    """.env 에서 값을 읽는다. 따옴표나 앞뒤 공백은 알아서 걷어낸다."""
    env = {}
    path = os.path.join(ROOT, ".env")
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "odipick-sync/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def fetch_all(token, months=None):
    """페이지를 끝까지 넘겨가며 전부 받아온다."""
    cutoff = None
    if months:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)

    url = f"https://graph.instagram.com/me/media?fields={FIELDS}&limit=100&access_token={token}"
    out, page = [], 0
    while url:
        data = fetch(url)
        if "error" in data:
            raise SystemExit(f"인스타그램 오류: {data['error'].get('message')}")
        for m in data.get("data", []):
            if cutoff and m.get("timestamp"):
                when = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
                if when < cutoff:
                    return out          # 최신순이므로 여기서 멈추면 된다
            out.append(m)
        page += 1
        sys.stdout.write(f"\r  {page}페이지 · {len(out)}개 수집")
        sys.stdout.flush()
        url = data.get("paging", {}).get("next")
        time.sleep(0.3)
    return out


def code_of(permalink):
    m = re.search(r"/(?:reel|reels|p)/([^/?#]+)", permalink or "")
    return m.group(1) if m else None


def hook_of(caption):
    """캡션 첫 줄이 후킹 문구다. 해시태그는 걷어낸다."""
    if not caption:
        return None
    for line in caption.split("\n"):
        line = re.sub(r"#[^\s#]+", "", line).strip()
        if line:
            return line[:33] + "…" if len(line) > 34 else line
    return None


def shop_of(caption):
    """📍 뒤에 오는 게 대개 가게 이름이다."""
    if not caption:
        return None
    m = re.search(r"📍\s*([^\n(]{1,40})", caption)
    if m:
        return m.group(1).strip()
    m = re.search(r"#([가-힣]{2,4}동)(?:맛집|카페|술집)?", caption)
    return m.group(1) if m else None


def main():
    months = None
    if "--months" in sys.argv:
        months = int(sys.argv[sys.argv.index("--months") + 1])

    token = load_env().get("IG_TOKEN") or os.environ.get("IG_TOKEN")
    if not token:
        raise SystemExit(".env 파일에 IG_TOKEN 이 없습니다.")

    print("인스타그램에서 릴스를 가져오는 중…")
    media = fetch_all(token, months)
    print()

    reels = []
    for m in media:
        if m.get("media_type") != "VIDEO" and m.get("media_product_type") != "REELS":
            continue
        code = code_of(m.get("permalink"))
        if not code:
            continue
        reels.append({
            "code": code,
            "hook": hook_of(m.get("caption")),
            "shop": shop_of(m.get("caption")),
            "likes": m.get("like_count"),
            "comments": m.get("comments_count"),
            "at": m.get("timestamp"),
            "thumbUrl": m.get("thumbnail_url") or m.get("media_url"),
            "caption": (m.get("caption") or "")[:1200],
        })
    reels.sort(key=lambda r: r["at"] or "", reverse=True)

    payload = {"syncedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "source": "instagram-graph-api", "items": reels}

    html = open(HTML, encoding="utf-8").read()
    block = '<script id="reels" type="application/json">\n' + \
            json.dumps(payload, ensure_ascii=False) + "\n</script>"
    new, n = re.subn(r'<script id="reels" type="application/json">[\s\S]*?</script>',
                     lambda _: block, html, count=1)
    if not n:
        raise SystemExit("index.html 안에서 릴스 데이터 자리를 못 찾았습니다.")
    open(HTML, "w", encoding="utf-8").write(new)

    # 캡션 원문은 따로 저장해둔다 — 가게 정보를 뽑아낼 때 쓴다
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    with open(os.path.join(ROOT, "data", "reels.json"), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)

    print(f"릴스 {len(reels)}개 동기화 완료")
    print(f"  index.html 반영 · data/reels.json 저장")
    if reels:
        print(f"  가장 최근: {reels[0]['at'][:10]}  가장 오래된: {reels[-1]['at'][:10]}")


if __name__ == "__main__":
    main()
