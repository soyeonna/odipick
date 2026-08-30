#!/usr/bin/env node
/**
 * 폐업·정보변경 감지
 *
 * 맛집 데이터는 상한다. 폐업한 집을 추천하면 그 한 번으로 신뢰가 끝난다.
 * 그래서 등록된 가게를 주기적으로 다시 조회해서 상태를 확인한다.
 *
 *   OPEN   정상 — 조회됨
 *   MOVED  이름은 있는데 주소가 달라짐 (이전 가능성)
 *   GONE   조회 안 됨 — 폐업 의심, 사람이 확인 필요
 *
 * 실행:  node scripts/check-closed.mjs
 *        node scripts/check-closed.mjs --apply    (index.html 에 상태를 기록)
 */
import { readFile, writeFile } from 'node:fs/promises';

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/126 Safari/537.36';
const KAKAO_KEY = process.env.KAKAO_REST_KEY;   // 있으면 카카오를 우선 사용한다

/** 카카오 로컬: 폐업하면 검색 결과에서 사라진다 — 가장 정확한 신호 */
async function viaKakao(name, area) {
  const q = encodeURIComponent(`${area ?? ''} ${name}`.trim());
  const res = await fetch(`https://dapi.kakao.com/v2/local/search/keyword.json?query=${q}&size=5`, {
    headers: { Authorization: `KakaoAK ${KAKAO_KEY}` },
  });
  if (!res.ok) return null;
  const { documents = [] } = await res.json();
  if (!documents.length) return { status: 'GONE', source: 'kakao' };
  const d = documents[0];
  return {
    status: 'OPEN', source: 'kakao',
    address: d.road_address_name || d.address_name,
    phone: d.phone || null,
    lat: Number(d.y), lng: Number(d.x),
    url: d.place_url,
  };
}

/** 카카오 키가 없을 때의 대체 경로 */
async function viaDiningcode(name, area) {
  const body = new URLSearchParams({
    query: `${area ?? ''} ${name}`.trim(),
    order: 'r_score', rn_search_flag: 'on', search_type: 'poi_search', page: '1', size: '3',
  });
  const res = await fetch('https://im.diningcode.com/API/isearch/', {
    method: 'POST', body,
    headers: { 'User-Agent': UA, 'Content-Type': 'application/x-www-form-urlencoded',
               Origin: 'https://www.diningcode.com', Referer: 'https://www.diningcode.com/' },
  });
  if (!res.ok) return null;
  const json = await res.json();
  const list = json?.result_data?.poi_section?.list ?? [];
  const hit = list.find((p) => p.nm && name.includes(p.nm.slice(0, 3)));
  if (!hit) return { status: 'UNKNOWN', source: 'diningcode' };
  return { status: hit.open_status === '영업 종료' ? 'GONE' : 'OPEN', source: 'diningcode',
           address: hit.road_addr ?? hit.addr, lat: hit.lat, lng: hit.lng };
}

const html = await readFile('index.html', 'utf8');
const block = html.match(/<script id="places" type="application\/json">\s*(\[[\s\S]*?\])\s*<\/script>/);
if (!block) { console.error('가게 데이터를 찾지 못했습니다.'); process.exit(1); }
const places = JSON.parse(block[1]);

console.log(`${places.length}곳 확인 · ${KAKAO_KEY ? '카카오' : '다이닝코드'} 기준\n`);

const report = [];
for (const p of places) {
  const area = (p.area ?? '').split(/[ ·]/)[0];
  const r = (KAKAO_KEY ? await viaKakao(p.n, area) : await viaDiningcode(p.n, area))
            ?? { status: 'UNKNOWN' };

  // 주소가 달라졌으면 이전했을 수 있다
  if (r.status === 'OPEN' && p.address && r.address && !r.address.includes(area)) r.status = 'MOVED';

  const mark = { OPEN: '○', MOVED: '△', GONE: '✕', UNKNOWN: '?' }[r.status];
  console.log(`${mark} ${p.n.padEnd(20)} ${r.status.padEnd(7)} ${r.address ?? ''}`);
  report.push({ ...p, _check: r });
  await new Promise((s) => setTimeout(s, 400));
}

const gone = report.filter((r) => r._check.status === 'GONE');
const moved = report.filter((r) => r._check.status === 'MOVED');
console.log(`\n정상 ${report.filter((r) => r._check.status === 'OPEN').length} · 이전의심 ${moved.length} · 폐업의심 ${gone.length}`);
if (gone.length) console.log('폐업 의심:', gone.map((g) => g.n).join(', '));

if (process.argv.includes('--apply')) {
  const next = report.map(({ _check, ...p }) => {
    if (_check.status === 'GONE') return { ...p, closed: true, checkedAt: new Date().toISOString().slice(0, 10) };
    const { closed, ...rest } = p;
    return { ...rest,
      ...(_check.lat ? { lat: _check.lat, lng: _check.lng } : {}),
      ...(_check.phone ? { phone: _check.phone } : {}),
      checkedAt: new Date().toISOString().slice(0, 10) };
  });
  await writeFile('index.html',
    html.replace(block[0], `<script id="places" type="application/json">\n${JSON.stringify(next, null, 1)}\n</script>`),
    'utf8');
  console.log('index.html 에 반영했습니다.');
}
