/* 오디픽 — 검색문을 조건으로 바꾸는 해석기
 *
 * "둔산동에서 소개팅인데 너무 시끄럽지 않고 주차 가능한 곳, 둘이 총 8만원 이하"
 *   → 지역 둔산동 / 상황 소개팅 / 인원 2 / 총예산 80000 (1인 40000)
 *     / 꼭 필요 주차 / 좋으면 조용함·대화 / 빼기 시끄러운 곳
 *
 * 브라우저에서도 deno 로도 돌아간다. 밖에서 쓰는 건 parseQuery 하나뿐이다.
 * AI를 부르지 않는다 — 흔한 말은 전부 여기서 처리하고, 정말 모르겠는 문장만 나중에 AI로 넘긴다.
 */
(function (root) {
  'use strict';

  /* ── 대전 행정구역 ───────────────────────────────────────── */
  var GU = ['동구', '중구', '서구', '유성구', '대덕구'];
  var GU_ALIAS = { '유성': '유성구', '대덕': '대덕구', '둔산': null };  // '둔산'은 동이라 여기서 제외

  var LANDMARK = {
    '대전역': 700, '성심당': 600, '은행동': 700, '으능정이': 600,
    '대전시청': 700, '시청': 700, '한밭수목원': 900, '충남대': 900,
    '카이스트': 900, '유성온천': 700, '궁동': 700, '엑스포': 900,
    '복합터미널': 700, '터미널': 700, '이글스파크': 900, '한화생명이글스파크': 900,
    '중앙시장': 600, '계족산': 1200, '장태산': 1200
  };

  /* ── 상황 ───────────────────────────────────────────────── */
  /* 소개팅과 데이트는 끝까지 따로 둔다 (기획서 요구) */
  var OCCASION = [
    ['소개팅', /소개팅|선\s*보|맞선/],
    ['데이트', /데이트|여자친구|남자친구|여친|남친|애인|썸/],
    ['부모님', /부모님|엄마|아빠|어머니|아버지|장인|장모|시부모|어른\s*모시/],
    ['가족', /가족|온가족|식구|처가|시댁|조카|아이들과/],
    ['회식', /회식|단합|송년|신년|워크샵|워크숍|팀\s*저녁|부서/],
    ['접대', /거래처|접대|바이어|손님\s*모시|상사|대표님\s*모시/],
    ['친구', /친구|친구들|동기|동창|모임|번개/],
    ['혼밥', /혼밥|혼자\s*밥|혼자\s*먹|나\s*혼자/],
    ['혼술', /혼술|혼자\s*술|혼자\s*한잔/],
    ['생일', /생일|기념일|축하|프로포즈/],
    ['2차', /2차|이차|삼차|3차/]
  ];

  /* ── 장소 종류 ──────────────────────────────────────────── */
  var PLACETYPE = [
    ['cafe', /카페|커피|디저트|브런치|베이커리|빵집/],
    ['bar', /술집|호프|이자카야|포차|바\b|와인바|칵테일|맥주집|펍/],
    ['play', /놀거리|방탈출|볼링|전시|미술관|박물관|공원|산책|수목원|둘레길/],
    ['rest', /맛집|식당|밥집|밥\s*먹|식사|저녁\s*먹|점심\s*먹/]
  ];

  var CUISINE = [
    ['고기', /고기|고깃|삼겹|갈비|목살|한우|소고기|돼지|구이|곱창|막창|닭갈비|치킨/],
    ['한식', /한식|한정식|백반|국밥|찌개|정식|칼국수|수제비|해장국|두루치기|보쌈|족발/],
    ['중식', /중식|중국집|짜장|짬뽕|탕수육|마라|양꼬치/],
    ['일식', /일식|초밥|스시|돈까스|돈카츠|라멘|라면집|우동|사시미|오마카세|이자카야/],
    ['양식', /양식|파스타|스테이크|피자|이탈리|프렌치|버거/],
    ['분식', /분식|떡볶이|김밥|순대|튀김/],
    ['면', /면\b|국수|냉면|밀면|소바/],
    ['해산물', /해산물|회\b|횟집|조개|새우|게\b|해물|생선|장어/]
  ];

  /* ── 편의 (꼭 필요 / 있으면 좋음) ─────────────────────────── */
  var FACILITY = [
    ['주차', /주차/],
    ['룸', /룸|방\s*있|개별\s*실|프라이빗\s*룸|독립\s*공간/],
    ['예약', /예약/],
    ['단체석', /단체석|단체\s*가능|긴\s*테이블|한\s*테이블에/],
    ['애견동반', /애견|반려견|강아지\s*동반|펫\s*동반|개\s*데리|멍멍이/]
  ];

  /* ── 분위기·선호 ────────────────────────────────────────── */
  var PREFERENCE = [
    ['조용함', /조용|시끄럽지\s*않|소란스럽지\s*않|한적|차분/],
    ['대화하기 좋음', /대화|얘기\s*하기|이야기\s*나누|말하기\s*좋/],
    ['넓음', /넓|대형|큰\s*곳|널찍/],
    ['깔끔함', /깔끔|정갈|청결|깨끗/],
    ['분위기 좋음', /분위기\s*(좋|있)|느좋|무드|감성|예쁜|이쁜/],
    ['가성비', /가성비|저렴|싸고|싼\s*곳|가격\s*착/],
    ['웨이팅 없음', /웨이팅\s*(없|짧|안)|줄\s*안\s*서|기다리지\s*않|바로\s*들어/],
    ['노포', /노포|오래된|전통|몇\s*십\s*년|현지인/],
    ['실내', /실내|비\s*오|비올|우천/]
  ];

  /* 조건 칩으로 만들면 안 되는 말들 */
  var STOPWORD = new RegExp('^(' + [
    '가능한', '가능', '갈', '곳', '데', '곳좀', '먹을', '먹고', '먹는', '갈만한', '가고', '가는',
    '있는', '있을', '있고', '없는', '좋은', '괜찮은', '추천', '추천좀', '찾아줘', '알려줘',
    '너무', '말고', '아닌', '보다', '정도', '같이', '함께', '그냥', '조금', '많이', '진짜', '정말',
    '여기', '저기', '어디', '우리', '저희', '사람', '분들', '자리', '시간', '기분', '오늘', '내일',
    '이하', '이상', '미만', '초과', '근처', '주변', '쪽', '에서', '으로', '하고', '이랑', '랑'
  ].join('|') + ')$');

  /* ── 도우미 ─────────────────────────────────────────────── */
  function blank() {
    return {
      location: { city: '대전', district: null, neighborhood: null, landmark: null, radiusMeters: null },
      placeTypes: [], cuisines: [], occasions: [], partySize: null,
      budget: { type: null, min: null, max: null, perPerson: null, currency: 'KRW' },
      visitDateTime: null, openNow: false,
      mustHave: [], preferences: [], exclude: [],
      rawKeywords: [], confidence: 0, needsClarification: false, clarificationQuestion: null
    };
  }
  function push(arr, v) { if (v != null && arr.indexOf(v) < 0) arr.push(v); }

  /* '술집 말고', 'A 빼고' — 부정 대상을 먼저 뜯어낸다.
     남은 문장에서 다시 술집을 찾지 않도록 부정 구간은 지워서 돌려준다. */
  function pullNegatives(text, out) {
    var re = /([가-힣A-Za-z0-9]{1,12})\s*(말고|빼고|제외|아닌\s*곳|은\s*싫|는\s*싫|말구)/g, m, rest = text;
    while ((m = re.exec(text)) !== null) {
      var word = m[1];
      PLACETYPE.forEach(function (r) { if (r[1].test(word)) push(out.exclude, r[0]); });
      CUISINE.forEach(function (r) { if (r[1].test(word)) push(out.exclude, r[0]); });
      if (/웨이팅|줄/.test(word)) push(out.preferences, '웨이팅 없음');
      if (!out.exclude.length && word && !STOPWORD.test(word)) push(out.exclude, word);
      rest = rest.replace(m[0], ' ');
    }
    return rest;
  }

  /* 예산 — 총액인지 1인당인지 가린다 */
  function parseBudget(text, out) {
    var perHint = /1\s*인|한\s*사람|인당|각자|1인당|일인당/.test(text);
    var totHint = /총|합쳐|다\s*해서|전부|둘이\s*총|모두/.test(text);
    var won = null;
    var m = text.match(/(\d+(?:\.\d+)?)\s*만\s*원?\s*(대|정도|이하|미만|안팎|내외)?/);
    if (m) {
      won = Math.round(parseFloat(m[1]) * 10000);
      if (m[2] === '대') won = won + 9999;              // '10만원대' = 10~19만
    } else {
      var m2 = text.match(/(\d{1,3}(?:,\d{3})+|\d{4,6})\s*원/);
      if (m2) won = +m2[1].replace(/,/g, '');
    }
    if (won == null) return;
    var isTotal = totHint || (!perHint && out.partySize && out.partySize > 1 && /총|둘이|셋이|넷이/.test(text));
    out.budget.type = isTotal ? 'total' : 'per_person';
    out.budget.max = won;
    out.budget.perPerson = (isTotal && out.partySize) ? Math.round(won / out.partySize) : (isTotal ? null : won);
  }

  /* 인원 */
  function parseParty(text, out) {
    var m = text.match(/(\d{1,2})\s*(명|인)(?!분)/);
    if (m) { out.partySize = +m[1]; return; }
    var k = text.match(/(둘|두\s*명|셋|세\s*명|넷|네\s*명|다섯)/);
    if (k) { out.partySize = { '둘': 2, '두 명': 2, '셋': 3, '세 명': 3, '넷': 4, '네 명': 4, '다섯': 5 }[k[1].replace(/\s+/g, ' ')] || null; }
    var b = text.match(/(두|세|네|다섯)\s*분/);          // '부모님 두 분' = 본인 포함 3
    if (b) out.partySize = ({ '두': 2, '세': 3, '네': 4, '다섯': 5 }[b[1]]) + 1;
    if (/혼밥|혼술|혼자/.test(text)) out.partySize = 1;
  }

  /* 방문 시각 — Asia/Seoul 기준. '지금 영업'과 '오늘 7시'를 구분한다 */
  function parseWhen(text, out, now) {
    now = now || new Date();
    if (/지금\s*(영업|하는|여는|문\s*연)|현재\s*영업|영업\s*중/.test(text)) out.openNow = true;

    var dayOff = 0, hasDay = false;
    if (/모레/.test(text)) { dayOff = 2; hasDay = true; }
    else if (/내일/.test(text)) { dayOff = 1; hasDay = true; }
    else if (/오늘|이따|today/.test(text)) { dayOff = 0; hasDay = true; }

    var t = text.match(/(아침|오전|점심|낮|저녁|밤|오후)?\s*(\d{1,2})\s*시\s*(반)?/);
    if (!t) {
      if (hasDay && /저녁|밤/.test(text)) { t = [null, '저녁', '19', null]; }
      else if (hasDay && /점심/.test(text)) { t = [null, '점심', '12', null]; }
      else if (!hasDay) return;
      else return;
    }
    if (/시간|시까지|시쯤까지/.test(text) && !/시에|시\s*도착|시\s*예약/.test(text)) { /* '2시간'은 시각이 아니다 */
      if (/\d\s*시간/.test(text)) return;
    }
    var hh = +t[2], part = t[1] || '';
    if (/아침|오전/.test(part)) { /* 그대로 */ }
    else if (/점심|낮/.test(part)) { if (hh <= 4) hh += 12; }
    else if (/저녁|밤|오후/.test(part)) { if (hh < 12) hh += 12; }
    else if (hh <= 10) hh += 12;                       // '7시'는 저녁으로 본다
    var mm = t[3] ? 30 : 0;

    var d = new Date(now.getTime() + dayOff * 86400000);
    out.visitDateTime = {
      date: d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'),
      minutes: hh * 60 + mm,
      timeZone: 'Asia/Seoul'
    };
  }

  /* 지역 — 행정구역과 랜드마크를 구분한다 */
  function parseLocation(text, out) {
    Object.keys(LANDMARK).forEach(function (k) {
      if (out.location.landmark) return;
      if (text.indexOf(k) > -1 && /근처|주변|앞|에서\s*가까|도보|걸어서/.test(text)) {
        out.location.landmark = k; out.location.radiusMeters = LANDMARK[k];
      }
    });
    var dm = text.match(/([가-힣]{1,5}동)(?=\s|$|에|의|으로|쪽|에서|안)/);
    if (dm) out.location.neighborhood = dm[1];
    GU.forEach(function (g) { if (text.indexOf(g) > -1) out.location.district = g; });
    if (!out.location.district) {
      Object.keys(GU_ALIAS).forEach(function (a) {
        if (GU_ALIAS[a] && text.indexOf(a) > -1 && !out.location.neighborhood) out.location.district = GU_ALIAS[a];
      });
    }
    /* 랜드마크만 잡혔는데 그게 동 이름이기도 하면 랜드마크를 우선한다 */
    if (out.location.landmark && out.location.neighborhood === out.location.landmark) out.location.neighborhood = null;
  }

  /* ── 본체 ───────────────────────────────────────────────── */
  function parseQuery(input, now) {
    var out = blank();
    var text = String(input || '').trim();
    if (!text) { out.needsClarification = true; out.clarificationQuestion = '어떤 곳을 찾으세요?'; return out; }

    var rest = pullNegatives(text, out);

    parseParty(rest, out);
    parseBudget(rest, out);
    parseWhen(rest, out, now);
    parseLocation(rest, out);

    OCCASION.forEach(function (r) { if (r[1].test(rest)) push(out.occasions, r[0]); });
    /* 소개팅이면 데이트를 얹지 않는다 — 서로 다른 자리다 */
    if (out.occasions.indexOf('소개팅') > -1) out.occasions = out.occasions.filter(function (o) { return o !== '데이트'; });
    if (out.occasions.indexOf('부모님') > -1) out.occasions = out.occasions.filter(function (o) { return o !== '데이트'; });

    CUISINE.forEach(function (r) { if (r[1].test(rest) && out.exclude.indexOf(r[0]) < 0) push(out.cuisines, r[0]); });
    PLACETYPE.forEach(function (r) { if (r[1].test(rest) && out.exclude.indexOf(r[0]) < 0) push(out.placeTypes, r[0]); });
    if (!out.placeTypes.length && out.cuisines.length) push(out.placeTypes, 'rest');

    /* 편의: '주차 가능한'처럼 대놓고 요구하면 꼭 필요, 그냥 스치면 있으면 좋음 */
    FACILITY.forEach(function (r) {
      if (!r[1].test(rest)) return;
      var must = new RegExp(r[1].source + '\\s*(되|있|필수|가능|돼|OK|오케)').test(rest) ||
                 new RegExp(r[1].source + '(?=\\s*(되는|있는|가능한|필수))').test(rest) ||
                 r[0] === '주차' || r[0] === '애견동반';
      push(must ? out.mustHave : out.preferences, r[0]);
    });

    /* 웨이팅·시끄러움 같은 '싫은 것'은 부정 구간이 지워지기 전 원문에서 본다 */
    PREFERENCE.forEach(function (r) { if (r[1].test(rest)) push(out.preferences, r[0]); });
    if (/웨이팅|줄\s*서/.test(text) && /없|짧|안|말고|싫|긴데/.test(text)) push(out.preferences, '웨이팅 없음');
    if (/시끄럽|소란/.test(text) && /않|말고|싫/.test(text)) push(out.exclude, '시끄러운 곳');

    /* 상황에 따라 자동으로 따라오는 선호 */
    if (out.occasions.indexOf('소개팅') > -1) {
      ['조용함', '대화하기 좋음', '깔끔함'].forEach(function (v) { push(out.preferences, v); });
    }
    if (out.occasions.indexOf('부모님') > -1) {
      ['조용함', '편안한 좌석'].forEach(function (v) { push(out.preferences, v); });
    }
    if (out.occasions.indexOf('회식') > -1) push(out.preferences, '예약');
    /* 5명 이상이 한 자리에 앉아야 하면 단체석은 '있으면 좋음'이 아니라 '꼭 필요'다 */
    if (out.partySize && out.partySize >= 5 && /한\s*테이블|다\s*같이\s*앉|한\s*자리에|단체/.test(text)) {
      out.preferences = out.preferences.filter(function (v) { return v !== '단체석'; });
      push(out.mustHave, '단체석');
    }

    /* 남은 낱말 — 가게 이름 검색용. 조사·형용사는 버린다 */
    /* 이미 조건으로 알아들은 낱말은 다시 검색어로 쓰지 않는다 */
    var understood = [].concat(PREFERENCE, FACILITY, OCCASION, CUISINE, PLACETYPE);
    rest.split(/[\s,·]+/).forEach(function (w) {
      w = w.replace(/(에서|에게|으로|에|은|는|이|가|을|를|와|과|의|도|만|랑|이랑|하고)$/, '').trim();
      if (w.length < 2 || STOPWORD.test(w)) return;
      if (understood.some(function (r) { return r[1].test(w); })) return;
      if (/^(않|안|못|말|싫|없)/.test(w)) return;
      /* 이미 '조용함'·'웨이팅 없음' 으로 바꿔 읽은 형용사는 낱말 검색에서 뺀다 */
      if (/^(시끄럽|소란|복잡|불편|붐비|조용|한적|넓|좁|깔끔|저렴|비싸)/.test(w)) return;
      if (/^\d/.test(w) || /(동|구|시|명|원|만원|시간|분)$/.test(w)) return;
      if (out.rawKeywords.length < 4) push(out.rawKeywords, w);
    });

    /* 확신도 — 지역과 상황이 있으면 충분히 알아들은 것 */
    var got = 0;
    if (out.location.neighborhood || out.location.district || out.location.landmark) got += 2;
    if (out.occasions.length) got += 2;
    if (out.cuisines.length || out.placeTypes.length) got += 1;
    if (out.budget.max) got += 1;
    if (out.partySize) got += 1;
    out.confidence = Math.min(1, got / 5);

    /* 지역을 모르면 그것만 한 번 물어본다 (질문을 여러 개 쏟지 않는다) */
    if (!out.location.neighborhood && !out.location.district && !out.location.landmark) {
      out.needsClarification = true;
      out.clarificationQuestion = '지금 계신 동네나 이동 가능한 지역이 어디예요?';
    }
    return out;
  }

  var api = { parseQuery: parseQuery };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.ODIPICK_PARSE = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
