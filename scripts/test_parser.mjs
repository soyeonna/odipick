/* 검색문 해석기 회귀 테스트
 *
 *   deno run --allow-read scripts/test_parser.mjs
 *   deno run --allow-read scripts/test_parser.mjs 기획서-1     (한 건만)
 *
 * AI를 부르지 않으므로 몇 번을 돌려도 요금이 들지 않는다.
 */
const ROOT = new URL('..', import.meta.url).pathname;

const src = await Deno.readTextFile(ROOT + 'js/parse-query.js');
const g = {};
new Function('globalThis', 'module', src)(g, { exports: {} });
const { parseQuery } = g.ODIPICK_PARSE;

const spec = JSON.parse(await Deno.readTextFile(ROOT + 'tests/queries.json'));
const only = Deno.args[0];

function dig(o, path) {
  return path.split('.').reduce((v, k) => (v == null ? v : v[k]), o);
}
function has(actual, want) {
  if (Array.isArray(want)) {
    if (!Array.isArray(actual)) return false;
    return want.every((w) => actual.includes(w));
  }
  if (want === '있음') return actual != null;
  return actual === want;
}

let pass = 0, fail = 0;
const fails = [];

for (const c of spec.cases) {
  if (only && c.id !== only) continue;
  const got = parseQuery(c.q);
  const bad = [];

  for (const [path, want] of Object.entries(c.expect || {})) {
    const actual = dig(got, path);
    if (!has(actual, want)) {
      bad.push(`  ${path}\n      나와야 함: ${JSON.stringify(want)}\n      실제:      ${JSON.stringify(actual)}`);
    }
  }
  for (const [path, bannedRaw] of Object.entries(c.notExpect || {})) {
    const actual = dig(got, path);
    const banned = Array.isArray(bannedRaw) ? bannedRaw : [bannedRaw];
    if (bannedRaw === '있음') {
      if (actual != null) bad.push(`  ${path}\n      없어야 하는데 있음: ${JSON.stringify(actual)}`);
      continue;
    }
    const hit = Array.isArray(actual)
      ? banned.filter((b) => actual.includes(b))
      : (banned.includes(actual) ? [actual] : []);
    if (hit.length) {
      bad.push(`  ${path}\n      나오면 안 되는데 나옴: ${JSON.stringify(hit)}`);
    }
  }

  if (bad.length) { fail++; fails.push({ c, bad, got }); } else pass++;
}

console.log('='.repeat(46));
console.log(`검색문 해석 테스트   ·   통과 ${pass} / 실패 ${fail}`);
console.log('='.repeat(46));

for (const f of fails) {
  console.log(`\n[${f.c.id}] "${f.c.q}"`);
  console.log(f.bad.join('\n'));
}
if (!fail) console.log('\n전부 통과했습니다.');
else console.log(`\n${fail}건이 아직 안 맞습니다.`);

Deno.exit(fail ? 1 : 0);
