#!/usr/bin/env python3
"""인스타그램 장기 토큰은 60일이면 만료된다. 만료 전 한 번 실행하면 60일 연장된다."""
import json, os, re, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(ROOT, ".env")
env = {}
for line in open(path, encoding="utf-8"):
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.strip().split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

token = env.get("IG_TOKEN")
if not token:
    raise SystemExit(".env 에 IG_TOKEN 이 없습니다.")

url = ("https://graph.instagram.com/refresh_access_token"
       f"?grant_type=ig_refresh_token&access_token={token}")
data = json.loads(urllib.request.urlopen(url, timeout=30).read().decode())
if "error" in data:
    raise SystemExit(data["error"].get("message"))

new = data["access_token"]
days = round(data["expires_in"] / 86400)
src = open(path, encoding="utf-8").read()
open(path, "w", encoding="utf-8").write(re.sub(r"IG_TOKEN=.*", "IG_TOKEN=" + new, src))
print(f"토큰을 {days}일 연장하고 .env 에 저장했습니다.")
