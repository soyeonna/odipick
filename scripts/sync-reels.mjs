#!/usr/bin/env node
/**
 * 대전공주 릴스 → PLACEPICK 자동 동기화
 *
 * 인스타그램에 올린 릴스를 전부 가져와 index.html 의
 * <script id="reels"> 블록을 통째로 갈아끼운다. 기존 게시물도 함께 채운다.
 *
 * 실행:  IG_TOKEN=... node scripts/sync-reels.mjs
 */
import { readFile, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const TOKEN = process.env.IG_TOKEN;
if (!TOKEN) {
  console.error('IG_TOKEN 환경변수가 없습니다. docs/SETUP.md 를 보세요.');
  process.exit(1);
}

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const HTML = join(ROOT, 'index.html');
const FIELDS = 'id,caption,media_type,media_product_type,permalink,thumbnail_url,timestamp,like_count,comments_count';

/** 인스타그램이 주는 모든 미디어를 페이지 넘겨가며 전부 받아온다 */
async function fetchAll() {
  let url = `https://graph.instagram.com/me/media?fields=${FIELDS}&limit=100&access_token=${TOKEN}`;
  const out = [];
  while (url) {
    const res = await fetch(url);
    const json = await res.json();
    if (json.error) throw new Error(`${json.error.message} (code ${json.error.code})`);
    out.push(...(json.data ?? []));
    url = json.paging?.next ?? null;
  }
  return out;
}

/** permalink 에서 릴스 코드만 뽑는다: .../reel/ABC123/ → ABC123 */
const codeOf = (permalink) => (permalink.match(/\/(?:reel|reels|p)\/([^/?]+)/) ?? [])[1] ?? null;

/** 캡션 첫 줄 = 후킹 문구. 이모지·구분자는 남겨둔다 */
function hookOf(caption) {
  if (!caption) return null;
  const line = caption.split('\n').map((s) => s.trim()).find(Boolean);
  if (!line) return null;
  return line.length > 34 ? line.slice(0, 33) + '…' : line;
}

/** 캡션 안의 해시태그에서 지역 힌트를 줍는다 (#둔산동맛집 → 둔산동) */
function areaOf(caption) {
  if (!caption) return null;
  const m = caption.match(/#([가-힣]{2,4}동)(?:맛집|카페|술집)?/);
  return m ? m[1] : null;
}

const reels = (await fetchAll())
  .filter((m) => m.media_type === 'VIDEO' || m.media_product_type === 'REELS')
  .map((m) => ({
    code: codeOf(m.permalink),
    hook: hookOf(m.caption),
    shop: areaOf(m.caption),
    likes: m.like_count ?? null,
    comments: m.comments_count ?? null,
    at: m.timestamp ?? null,
  }))
  .filter((r) => r.code);

reels.sort((a, b) => String(b.at).localeCompare(String(a.at)));

const payload = {
  syncedAt: new Date().toISOString(),
  source: 'instagram-graph-api',
  items: reels,
};

const block =
  '<script id="reels" type="application/json">\n' +
  JSON.stringify(payload, null, 1) +
  '\n</script>';

const html = await readFile(HTML, 'utf8');
const next = html.replace(
  /<script id="reels" type="application\/json">[\s\S]*?<\/script>/,
  block
);

if (next === html) {
  console.error('index.html 안에서 <script id="reels"> 블록을 못 찾았습니다.');
  process.exit(1);
}

await writeFile(HTML, next, 'utf8');
console.log(`릴스 ${reels.length}개 동기화 완료 · ${payload.syncedAt}`);
