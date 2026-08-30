#!/usr/bin/env node
/**
 * 인스타그램 장기 토큰은 60일이면 만료된다. 만료 전에 한 번 호출하면 60일 연장된다.
 * 실행:  IG_TOKEN=... node scripts/refresh-token.mjs
 */
const TOKEN = process.env.IG_TOKEN;
if (!TOKEN) { console.error('IG_TOKEN 환경변수가 없습니다.'); process.exit(1); }

const res = await fetch(
  `https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=${TOKEN}`
);
const json = await res.json();
if (json.error) { console.error(json.error.message); process.exit(1); }

const days = Math.round(json.expires_in / 86400);
console.log(`새 토큰 (${days}일 유효):\n${json.access_token}`);
console.log('\n이 값을 저장소 시크릿 IG_TOKEN 에 덮어써 주세요.');
