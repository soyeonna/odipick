#!/usr/bin/env python3
"""현재 매장·릴스 데이터를 Supabase로 올린다. (한 번만 실행)

준비: .env 에 두 줄 추가
  SUPABASE_URL=https://xxxx.supabase.co
  SUPABASE_SERVICE_KEY=eyJ...   (Settings → API → service_role)
"""
import json, os, re, subprocess, sys

env={}
for line in open(".env",encoding="utf-8"):
    if "=" in line and not line.strip().startswith("#"):
        k,v=line.split("=",1); env[k.strip()]=v.strip()
URL=env.get("SUPABASE_URL"); KEY=env.get("SUPABASE_SERVICE_KEY")
if not URL or not KEY: sys.exit(".env 에 SUPABASE_URL / SUPABASE_SERVICE_KEY 를 넣어주세요")

def post(table, rows):
    r=subprocess.run(["curl","-sS","-X","POST",f"{URL}/rest/v1/{table}",
        "-H",f"apikey: {KEY}","-H",f"Authorization: Bearer {KEY}",
        "-H","Content-Type: application/json","-H","Prefer: resolution=merge-duplicates,return=minimal",
        "-d",json.dumps(rows)],capture_output=True)
    err=r.stdout.decode()
    return err if err.strip() else None

h=open("index.html",encoding="utf-8").read()
P=json.loads(re.search(r'<script id="places" type="application/json">([\s\S]*?)</script>',h).group(1))
rows=[]
for p in P:
    rows.append({"kakao_place_id":p.get("kid"),"name":p["n"],
        "place_type":None,"category":p.get("cat"),"cats":p.get("cats") or [],
        "district":p.get("gu"),"neighborhood":(p.get("area") or "").split(" ")[0] or None,
        "road_address":p.get("area"),"latitude":p.get("lat"),"longitude":p.get("lng"),
        "phone":p.get("phone"),"kakao_place_url":p.get("kurl"),"hours":p.get("hours"),
        "budget":p.get("budget"),"cap":p.get("cap"),"sit":p.get("sit") or [],
        "fac":p.get("fac") or {},"mood":p.get("mood") or [],"v":p.get("v"),
        "src":p.get("src"),"status":"closed" if p.get("closed") else "open",
        "likes":p.get("likes")})
for i in range(0,len(rows),100):
    err=post("places",rows[i:i+100])
    if err: sys.exit(f"places 업로드 실패: {err[:300]}")
print(f"places {len(rows)}곳 업로드 완료")

caps=json.load(open("data/reel-captions.json",encoding="utf-8"))
crows=[{"code":c,"caption":v.get("caption"),"likes":v.get("likes"),
        "comments":v.get("comments")} for c,v in caps.items()]
for i in range(0,len(crows),100):
    err=post("contents",crows[i:i+100])
    if err: sys.exit(f"contents 업로드 실패: {err[:300]}")
print(f"contents {len(crows)}건 업로드 완료")
