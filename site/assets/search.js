/* ===========================================================================
   search.js — 中英混排的轻量 BM25 检索引擎（浏览器本地，无依赖）
   中文按「单字 + 二元组」切分，英文按词切分；用于站内搜索与 AI 检索。
   =========================================================================== */
(function () {
  "use strict";

  var CJK = /[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]/;

  // 问句里的功能词与疑问词：切开后不承载检索意义，先剔除
  var STOP_PHRASES = [
    "为什么", "是什么", "什么样", "什么", "怎么样", "怎么", "怎样", "如何",
    "哪些", "哪张", "哪个", "哪里", "哪儿", "是不是", "有没有", "可不可以",
    "能不能", "可以", "能否", "请问", "告诉", "介绍", "解释", "具体",
    "一下", "多少", "几个", "谁", "吗", "呢", "吧", "啊", "呀"
  ];
  var STOP_CHARS = /[的了吗呢吧啊呀哦嗯]/g;

  // 查询归一：去连字符/标点/空白，便于「Z-选择性」与「Z选择性」等价
  function norm(s) {
    return String(s || "")
      .toLowerCase()
      .replace(/[\s\u3000]+/g, "")
      .replace(/[·・\-–—_/、，,。.；;：:！!？?（）()\[\]【】"“”'‘’《》<>|+*=~`^$#@%&\\]/g, "");
  }

  // 归一后再去功能词，得到「内容串」
  function clean(q) {
    var s = norm(q);
    STOP_PHRASES.forEach(function (p) { s = s.split(p).join(""); });
    s = s.replace(STOP_CHARS, "");
    return s;
  }

  function tokenize(text) {
    var s = String(text || "").toLowerCase();
    var out = [];
    var rest = s.replace(/[a-z0-9]+/g, function (w) {
      if (w.length > 1) out.push(w);
      return " ";
    });
    var run = "";
    for (var i = 0; i < rest.length; i++) {
      var ch = rest[i];
      if (CJK.test(ch)) {
        run += ch;
      } else if (run) { pushCjk(run); run = ""; }
    }
    if (run) pushCjk(run);

    function pushCjk(str) {
      for (var j = 0; j < str.length; j++) {
        out.push(str[j]);
        if (j + 1 < str.length) out.push(str[j] + str[j + 1]);
      }
    }
    return out;
  }

  var TITLE_W = 3;   // 标题命中权重
  var KEY_W = 1.4;   // 关键词字段权重

  function buildIndex(docs) {
    var df = Object.create(null);
    var items = docs.map(function (d) {
      var tf = Object.create(null);
      var len = 0;
      function feed(text, w) {
        if (!text) return;
        var toks = tokenize(text);
        len += toks.length;
        toks.forEach(function (t) { tf[t] = (tf[t] || 0) + w; });
      }
      feed(d.title, TITLE_W);
      feed(d.text, 1);
      feed(d.keys, KEY_W);
      Object.keys(tf).forEach(function (t) { df[t] = (df[t] || 0) + 1; });
      return { doc: d, tf: tf, len: len };
    });
    var total = 0;
    items.forEach(function (it) { total += it.len; });
    return { docs: items, df: df, N: items.length, avgdl: items.length ? total / items.length : 1 };
  }

  // 不同内容类型的先验：阶段与缺口更「像答案」
  var PRIOR = { phase: 0.9, gap: 0.7, overview: 0.5, catalyst: 0.3, figure: 0.15, method: 0.2, paper: 0 };

  // k1=1.4, b=0.72
  function search(idx, query, limit) {
    limit = limit || 8;
    var qStr = clean(query);
    var q = tokenize(qStr);
    if (!q.length) return [];
    var counts = Object.create(null);
    q.forEach(function (t) { counts[t] = (counts[t] || 0) + 1; });

    var scored = idx.docs.map(function (it) {
      var score = PRIOR[it.doc.kind] || 0;
      var strong = 0;
      var matchedStrong = [];
      Object.keys(counts).forEach(function (t) {
        var tf = it.tf[t];
        if (!tf) return;
        var dfv = idx.df[t] || 0;
        var idf = Math.log(1 + (idx.N - dfv + 0.5) / (dfv + 0.5));
        var denom = tf + 1.4 * (1 - 0.72 + 0.72 * it.len / idx.avgdl);
        score += idf * (tf * 2.4) / denom * (1 + 0.25 * (counts[t] - 1));
        if (t.length >= 2) { strong++; matchedStrong.push(t); }
      });
      if (score <= (PRIOR[it.doc.kind] || 0)) return null;
      return { doc: it.doc, score: score, strong: strong, terms: matchedStrong };
    }).filter(Boolean);

    scored.sort(function (a, b) {
      return (b.score + b.strong * 1.2) - (a.score + a.strong * 1.2);
    });
    return scored.slice(0, limit);
  }

  /* 是否命中：给 AI 用的门限。
     判据是「有没有真正的实词重叠」，而不是简单的字符覆盖率——
     否则「今天天气怎么样」会因为「天」「气」这类单字而误命中。 */
  function gate(results) {
    if (!results.length) return { ok: false, reason: "empty" };
    var top = results[0];
    if (!top.strong) return { ok: false, reason: "no-content-term", top: top };
    if (top.strong >= 2 || top.score >= 6) return { ok: true, top: top };
    return { ok: false, reason: "weak", top: top };
  }

  function highlight(text, query) {
    var q = clean(query);
    if (!q) return text;
    var terms = [];
    (q.match(/[a-z0-9]{2,}/g) || []).forEach(function (w) { terms.push(w); });
    var cjkRun = q.replace(/[a-z0-9]/g, "");
    for (var i = 0; i + 1 < cjkRun.length; i++) terms.push(cjkRun.slice(i, i + 2));
    if (!terms.length) return text;
    terms = terms.filter(function (t, i) { return terms.indexOf(t) === i; })
      .sort(function (a, b) { return b.length - a.length; });
    var esc = terms.map(function (t) { return t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); });
    if (!esc.length) return text;
    var re = new RegExp("(" + esc.join("|") + ")", "gi");
    return String(text).replace(re, "<mark>$1</mark>");
  }

  window.Search = {
    norm: norm,
    clean: clean,
    tokenize: tokenize,
    buildIndex: buildIndex,
    search: search,
    gate: gate,
    highlight: highlight
  };
})();
