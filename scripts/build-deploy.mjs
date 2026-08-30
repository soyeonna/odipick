#!/usr/bin/env node
/**
 * index.html 은 Artifact 미리보기용이라 <head> 가 없다.
 * 실제 서버에 올릴 때는 viewport 같은 필수 태그가 있어야 모바일에서 제대로 보인다.
 * 이 스크립트가 그 껍데기를 씌워 dist/index.html 을 만든다.
 *
 * 실행:  node scripts/build-deploy.mjs
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises';

const SITE = {
  title: '오디픽 · 대전 상황별 맛집',
  desc: '10명 회식 룸, 가족끼리 조용한 카페 — 상황을 그대로 검색하세요. 대전공주가 직접 가보고 판정한 곳만 나옵니다.',
  url: 'https://odipick.kr',
  theme: '#F2417E',
};

const body = await readFile('index.html', 'utf8');

// <title> 은 본문에 이미 있으니 중복되지 않게 걷어낸다
const inner = body.replace(/<title>[\s\S]*?<\/title>\s*/i, '');

const html = `<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>${SITE.title}</title>
<meta name="description" content="${SITE.desc}">
<meta name="theme-color" content="${SITE.theme}">
<meta name="format-detection" content="telephone=no">

<meta property="og:type" content="website">
<meta property="og:title" content="${SITE.title}">
<meta property="og:description" content="${SITE.desc}">
<meta property="og:url" content="${SITE.url}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">

<link rel="icon" href="placepick_icon.png">
<link rel="apple-touch-icon" href="placepick_icon.png">
<meta name="apple-mobile-web-app-title" content="오디픽">
<meta name="mobile-web-app-capable" content="yes">

<style>
  *{box-sizing:border-box}
  html{-webkit-text-size-adjust:100%}
  body{margin:0}
  img{max-width:100%}
  [hidden]{display:none!important}
</style>
</head>
<body>
<script>window.__ODIPICK_DEPLOY__=true;</script>
${inner}
</body>
</html>
`;

await mkdir('dist', { recursive: true });
await writeFile('dist/index.html', html, 'utf8');

const kb = (n) => `${Math.round(n / 1024)}KB`;
console.log(`dist/index.html 생성 — ${kb(html.length)}`);
console.log('placepick_icon.png 를 dist/ 로 함께 복사해서 올리세요.');
