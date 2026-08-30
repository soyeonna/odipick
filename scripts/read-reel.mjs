#!/usr/bin/env node
/**
 * 릴스 URL만 있으면 캡션을 통째로 읽어온다. 토큰도 로그인도 필요 없다.
 * 인스타그램 공개 임베드(/embed/captioned/)가 캡션을 그대로 내려주는 걸 이용한다.
 *
 * 실행:
 *   node scripts/read-reel.mjs https://www.instagram.com/reel/XXXX/ [...]
 *   node scripts/read-reel.mjs --file urls.txt
 *
 * 결과는 화면에 뜨고 data/reel-captions.json 에도 쌓인다.
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36';

const codeOf = (u) => (u.match(/\/(?:reel|reels|p)\/([^/?#]+)/) ?? [])[1] ?? null;

const unescapeHtml = (t) =>
  t.replace(/&quot;/g, '"').replace(/&#039;|&#39;/g, "'")
   .replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>')
   .replace(/&nbsp;/g, ' ').replace(/<br\s*\/?>/gi, '\n').replace(/<[^>]+>/g, '');

/** 캡션에서 쓸 만한 것만 추려낸다 */
function parse(caption) {
  const tags = [...caption.matchAll(/#([^\s#]+)/g)].map((m) => m[1]);
  const clean = caption.replace(/#[^\s#]+/g, '').trim();
  const hook = clean.split('\n').map((s) => s.trim()).find(Boolean) ?? null;

  // 📍 뒤에 오는 게 대개 가게 이름과 주소다
  const pin = caption.match(/📍\s*([^\n(]{1,40})(?:\(([^)]{2,60})\))?/);
  // 가격은 "메뉴(12,000원)" 또는 "12,000원" 꼴
  const prices = [...caption.matchAll(/([가-힣A-Za-z][가-힣A-Za-z0-9 ]{1,20})\s*[:(]?\s*(\d{1,3},\d{3})\s*원/g)]
    .map((m) => ({ menu: m[1].trim(), price: Number(m[2].replace(/,/g, '')) }));
  const phone = (caption.match(/0\d{1,3}-\d{3,4}-\d{4}/) ?? [])[0] ?? null;
  const hours = (caption.match(/(?:매일|월|화|수|목|금|토|일)[^\n]{0,40}\d{1,2}:\d{2}\s*[-~]\s*\d{1,2}:\d{2}/) ?? [])[0] ?? null;
  const area = (caption.match(/#([가-힣]{2,4}동)(?:맛집|카페|술집)?/) ?? [])[1]
            ?? (caption.match(/([가-힣]{2,4}동)\s*\d/) ?? [])[1] ?? null;

  return {
    hook,
    shop: pin?.[1]?.trim() ?? null,
    address: pin?.[2]?.trim() ?? null,
    area, phone, hours,
    prices: prices.slice(0, 6),
    tags,
    caption: caption.trim(),
  };
}

async function readReel(url) {
  const code = codeOf(url);
  if (!code) return { url, error: '릴스 주소가 아닙니다' };

  const res = await fetch(`https://www.instagram.com/reel/${code}/embed/captioned/`, {
    headers: { 'User-Agent': UA, 'Accept-Language': 'ko-KR,ko;q=0.9' },
  });
  if (!res.ok) return { code, error: `HTTP ${res.status}` };

  const html = await res.text();
  const raw = html.match(/class="Caption"[\s\S]*?<\/div>/)?.[0]
           ?? html.match(/"caption"\s*:\s*"((?:[^"\\]|\\.)*)"/)?.[1]
           ?? '';
  if (!raw) return { code, error: '캡션을 찾지 못했습니다 (비공개이거나 형식이 바뀌었을 수 있습니다)' };

  const caption = unescapeHtml(raw.replace(/^[\s\S]*?<\/a>/, ''));
  const likes = Number((html.match(/([\d,]+)\s*likes/) ?? [])[1]?.replace(/,/g, '') ?? 0) || null;
  const collab = [...html.matchAll(/@([a-z0-9._]{3,30})/gi)].map((m) => m[1])
    .filter((u) => u !== '_princesspick_');

  return { code, url: `https://www.instagram.com/reel/${code}/`, likes,
           collab: [...new Set(collab)].slice(0, 3), ...parse(caption) };
}

const args = process.argv.slice(2);
let urls = args;
if (args[0] === '--file') urls = (await readFile(args[1], 'utf8')).split('\n').map((s) => s.trim()).filter(Boolean);
if (!urls.length) { console.error('사용법: node scripts/read-reel.mjs <릴스 URL...>'); process.exit(1); }

const out = [];
for (const u of urls) {
  const r = await readReel(u);
  out.push(r);
  if (r.error) { console.log(`✗ ${r.code ?? u} — ${r.error}`); continue; }
  console.log(`\n✓ ${r.shop ?? '(가게명 못 찾음)'}  [${r.code}]  좋아요 ${r.likes ?? '?'}`);
  console.log(`  후킹  ${r.hook ?? '-'}`);
  console.log(`  주소  ${r.address ?? r.area ?? '-'}`);
  if (r.hours) console.log(`  시간  ${r.hours}`);
  if (r.phone) console.log(`  전화  ${r.phone}`);
  if (r.prices.length) console.log(`  가격  ${r.prices.map((p) => `${p.menu} ${p.price.toLocaleString()}원`).join(' · ')}`);
  await new Promise((r) => setTimeout(r, 700));   // 예의상 간격을 둔다
}

if (!existsSync('data')) await mkdir('data');
await writeFile('data/reel-captions.json', JSON.stringify(out, null, 1), 'utf8');
console.log(`\n${out.filter((r) => !r.error).length}/${out.length}개 읽음 → data/reel-captions.json`);
