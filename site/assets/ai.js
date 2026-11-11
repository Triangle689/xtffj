/* ===========================================================================
   ai.js — 抽屉式 AI 问答（严格基于站内内容）
   流程：问题 → 本地 BM25 检索 → 命中门控 → 拼装站内片段 → DeepSeek 流式回答
        → 标注 [来源 n] → 自动跳转到最相关章节 → 问答写入 localStorage
   =========================================================================== */
(function () {
  "use strict";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var LS_SET = "om.ai.settings.v1";
  var LS_HIS = "om.ai.history.v1";
  var MAX_HISTORY = 120;
  var TOP_K = 5;

  var DEFAULT_SETTINGS = {
    apiKey: "",
    model: "deepseek-chat",
    endpoint: "https://api.deepseek.com/chat/completions",
    autoJump: true
  };

  var settings = loadSettings();
  var history = loadHistory();
  var ragIndex = null;      // { chunks, idx }
  var busy = false;
  var lastSources = [];

  /* ---------------------------------------------------------------- 存储 */
  function loadSettings() {
    try {
      var s = JSON.parse(localStorage.getItem(LS_SET) || "{}");
      return Object.assign({}, DEFAULT_SETTINGS, s);
    } catch (e) { return Object.assign({}, DEFAULT_SETTINGS); }
  }
  function saveSettings() {
    try { localStorage.setItem(LS_SET, JSON.stringify(settings)); } catch (e) {}
  }
  function loadHistory() {
    try {
      var h = JSON.parse(localStorage.getItem(LS_HIS) || "[]");
      return Array.isArray(h) ? h : [];
    } catch (e) { return []; }
  }
  function saveHistory() {
    try {
      if (history.length > MAX_HISTORY) history = history.slice(0, MAX_HISTORY);
      localStorage.setItem(LS_HIS, JSON.stringify(history));
    } catch (e) {
      console.warn("[ai] 历史写入失败（可能超出配额）", e);
    }
  }

  /* ---------------------------------------------------------------- 检索 */
  function loadRag() {
    if (ragIndex) return Promise.resolve(ragIndex);
    return fetch("data/rag-index.json", { cache: "force-cache" })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        ragIndex = { chunks: d.chunks, idx: Search.buildIndex(d.chunks) };
        return ragIndex;
      });
  }

  function retrieve(q) {
    var res = Search.search(ragIndex.idx, q, TOP_K);
    // 只保留相对前几名不至于太弱的，避免噪声
    if (res.length > 1) {
      var cut = res[0].score * 0.18;
      res = res.filter(function (r, i) { return i === 0 || r.score >= cut; });
    }
    return res;
  }

  /* ---------------------------------------------------------------- 提示词 */
  var SYSTEM_PROMPT = [
    "你是「烯烃复分解」学术展示站的站内问答助手。读者正在浏览这座网站。",
    "",
    "【硬性规则 · 违反即视为回答失败】",
    "1. 只能依据用户消息里 <站内资料> 提供的内容作答。",
    "   禁止使用你自身训练得到的知识、常识补全、推理外推，或任何联网/外部信息。",
    "2. 如果 <站内资料> 不足以回答问题，只回复：「站内暂无相关内容。」",
    "   可以在后面用一句话建议 1–2 个站内可尝试的关键词。不要用外部知识勉强作答，不要猜测。",
    "3. 每个论断后必须用 [来源 N] 标注依据的片段编号（N 为资料中的编号）。",
    "   没有资料支撑的句子一律不要写。",
    "4. 不得编造或改写文献作者、年份、卷期页码、DOI、产率、温度等任何数字。",
    "   资料里没有的数字，一个都不要出现在回答里。",
    "5. 用简体中文。先给 1–2 句结论，再给 2–4 条依据。总长不超过 220 字。",
    "6. 不要出现「根据资料」「上下文」「作为 AI」「我无法」这类话术，直接陈述站内内容。",
    "7. 若问题与本站主题（烯烃复分解及其文献）无关，直接回复「站内暂无相关内容。」"
  ].join("\n");

  function buildMessages(question, hits) {
    var blocks = hits.map(function (h, i) {
      var c = h.doc;
      return "[来源 " + (i + 1) + "] " + c.title + "（锚点：" + c.anchor + "）\n" + c.text;
    }).join("\n\n");
    var user = "<站内资料>\n" + blocks + "\n</站内资料>\n\n问题：" + question;
    return [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: user }
    ];
  }

  /* ---------------------------------------------------------------- 渲染 */
  var NO_HIT = { text: "站内暂无相关内容。" };

  function renderRich(text) {
    // 转义 → **加粗** → [来源 n] 变成可点击 chip → 换行
    var s = esc(text);
    s = s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\[来源\s*(\d+)\]/g, function (m, n) {
      return '<button class="cite-chip" type="button" data-cite="' + n + '">来源 ' + n + "</button>";
    });
    s = s.split(/\n{2,}/).map(function (p) {
      p = p.trim();
      if (!p) return "";
      return "<p>" + p.replace(/\n/g, "<br>") + "</p>";
    }).join("");
    return s;
  }

  function addMsg(role, html, opts) {
    var wrap = document.createElement("div");
    wrap.className = "msg " + role;
    if (opts && opts.id) wrap.id = opts.id;
    wrap.innerHTML = '<div class="who">' + (role === "user" ? "你" : "站内助手") + "</div>"
      + '<div class="bubble">' + html + "</div>";
    $("#aiBody").appendChild(wrap);
    scrollBottom();
    return wrap;
  }

  function scrollBottom() {
    var el = $("#aiScroll");
    el.scrollTop = el.scrollHeight;
  }

  function sourcesHtml(hits) {
    return '<div class="sources">' + hits.map(function (h, i) {
      var c = h.doc;
      return '<button class="source-btn" type="button" data-anchor="' + c.anchor + '" title="'
        + esc(c.title) + '">' + (i + 1) + " · " + esc(c.title.length > 26 ? c.title.slice(0, 26) + "…" : c.title)
        + "</button>";
    }).join("") + "</div>";
  }

  function renderIntro() {
    var body = $("#aiBody");
    body.innerHTML = ""
      + '<div class="qa-intro">'
      + "<p>这个助手只读站内内容：45 篇文献、23 张原文图、5 个研究阶段与缺口分析。<b>不会联网，也不会使用模型自己的知识。</b></p>"
      + '<div class="rule">回答里如果出现 <b>[来源 n]</b>，点击它会跳转到对应章节；'
      + "站内没有的问题，它会直接说「站内暂无相关内容」，而不是编一个答案。</div>"
      + '<div class="sugg">'
      + ["Chauvin 的机理为什么难验证？",
         "文档给的文献缺了什么？",
         "Grubbs Ⅰ 代和 Ⅱ 代差在哪？",
         "Z-选择性是什么时候做出来的？",
         "哪张图和索烃有关？"].map(function (q) {
          return '<button type="button" data-ask="' + esc(q) + '">' + esc(q) + "</button>";
        }).join("")
      + "</div></div>";
    var cfgMissing = !settings.apiKey;
    if (cfgMissing) {
      body.insertAdjacentHTML("beforeend",
        '<div class="msg bot" style="margin-top:16px"><div class="bubble">'
        + '还没有配置 DeepSeek API Key。点右上角 <b>⚙</b> 填入即可（只保存在本机浏览器，不会上传到别处）。'
        + "</div></div>");
    }
  }

  function renderHistoryPanel() {
    var body = $("#aiBody");
    if (!history.length) {
      body.innerHTML = '<div class="qa-intro">还没有记录。问过的每个问题与回答都会存在本机浏览器里。</div>';
      return;
    }
    var html = '<div class="qa-intro"><p>共 ' + history.length + " 条记录（仅存本机）。点任一条回看并跳转。</p></div>";
    html += history.map(function (h) {
      var t = new Date(h.ts);
      var time = (t.getMonth() + 1) + "/" + t.getDate() + " " + String(t.getHours()).padStart(2, "0")
        + ":" + String(t.getMinutes()).padStart(2, "0");
      return '<div class="hist-item" data-hid="' + h.id + '">'
        + '<span class="q" title="' + esc(h.q) + '">' + esc(h.q) + "</span>"
        + "<time>" + time + "</time>"
        + '<button class="del" type="button" data-del="' + h.id + '" aria-label="删除">✕</button>'
        + "</div>";
    }).join("");
    html += '<div class="settings"><div class="row2">'
      + '<button class="btn" type="button" id="expHist">导出 JSON</button>'
      + '<button class="btn" type="button" id="clrHist">清空全部</button></div></div>';
    body.innerHTML = html;
  }

  function renderSettings() {
    var body = $("#aiBody");
    body.innerHTML = ""
      + '<div class="settings">'
      + '<p style="margin-top:0">AI 问答需要你自己的 DeepSeek API Key。Key 只写进本机 localStorage，'
      + "请求直接发往 DeepSeek，本站没有后端。</p>"
      + '<label for="setKey">DeepSeek API Key</label>'
      + '<input id="setKey" type="password" placeholder="sk-..." value="' + esc(settings.apiKey) + '" autocomplete="off">'
      + '<div class="hint">在 <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener">platform.deepseek.com</a> 创建。'
      + "填入后可点「测试连接」验证。</div>"
      + '<label for="setModel">模型</label>'
      + '<select id="setModel">'
      + '<option value="deepseek-chat">deepseek-chat（快，够用）</option>'
      + '<option value="deepseek-reasoner">deepseek-reasoner（慢，推理更强）</option>'
      + "</select>"
      + '<label for="setEp">接口地址</label>'
      + '<input id="setEp" value="' + esc(settings.endpoint) + '">'
      + '<div class="hint">默认直连官方接口（已验证支持浏览器跨域）。若改用自建代理，填代理的完整 URL。</div>'
      + '<label style="display:flex;gap:8px;align-items:center;font-weight:400;margin-top:16px">'
      + '<input type="checkbox" id="setJump" style="width:auto;height:auto"'
      + (settings.autoJump ? " checked" : "") + "> 回答时自动跳转到最相关章节</label>"
      + '<div class="row2">'
      + '<button class="btn primary" type="button" id="saveCfg">保存</button>'
      + '<button class="btn" type="button" id="testCfg">测试连接</button>'
      + '<button class="btn" type="button" id="backCfg">返回</button>'
      + "</div>"
      + '<div class="hint" id="cfgMsg" style="margin-top:10px"></div>'
      + "</div>";
    $("#setModel").value = settings.model;
  }

  /* ---------------------------------------------------------------- 请求 */
  function askModel(messages, onDelta) {
    var key = settings.apiKey.trim();
    if (!key) return Promise.reject(new Error("NO_KEY"));

    var body = {
      model: settings.model,
      messages: messages,
      temperature: 0.1,
      stream: true,
      max_tokens: 700
    };

    return fetch(settings.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + key
      },
      body: JSON.stringify(body)
    }).then(function (res) {
      if (!res.ok) {
        return res.text().then(function (t) {
          var err = new Error("HTTP " + res.status + " " + t.slice(0, 200));
          err.status = res.status;
          throw err;
        });
      }
      if (!res.body || !res.body.getReader) {
        // 不支持流式的环境：退回整体解析
        return res.json().then(function (j) {
          var txt = j.choices && j.choices[0] && j.choices[0].message.content || "";
          onDelta(txt, true);
          return txt;
        });
      }
      var reader = res.body.getReader();
      var decoder = new TextDecoder("utf-8");
      var buf = "";
      var full = "";

      function pump() {
        return reader.read().then(function (r) {
          if (r.done) { onDelta("", true); return full; }
          buf += decoder.decode(r.value, { stream: true });
          var lines = buf.split("\n");
          buf = lines.pop();
          lines.forEach(function (line) {
            line = line.trim();
            if (!line || line.indexOf("data:") !== 0) return;
            var payload = line.slice(5).trim();
            if (payload === "[DONE]") return;
            try {
              var j = JSON.parse(payload);
              var d = j.choices && j.choices[0] && j.choices[0].delta;
              var piece = d && d.content;
              if (piece) { full += piece; onDelta(piece, false); }
            } catch (e) { /* 忽略不完整行 */ }
          });
          return pump();
        });
      }
      return pump();
    });
  }

  function describeError(err) {
    if (err.message === "NO_KEY") {
      return "还没有填 API Key。点右上角 <b>⚙</b> 填入 DeepSeek 的 Key 后再问。";
    }
    if (err.status === 401) return "API Key 无效或已过期（401）。请到 ⚙ 里重新填写。";
    if (err.status === 402) return "DeepSeek 账户余额不足（402）。";
    if (err.status === 429) return "请求太频繁或额度用尽（429），稍后再试。";
    if (err.status === 400) return "请求被拒绝（400）：" + esc(err.message.slice(0, 160));
    if (/Failed to fetch|NetworkError|Load failed/i.test(err.message)) {
      return "网络请求失败。可能是接口地址被墙/被拦截，或用了不支持跨域的自建代理。"
        + "可在 ⚙ 里换接口地址后重试。";
    }
    return "请求出错：" + esc(err.message.slice(0, 200));
  }

  /* ---------------------------------------------------------------- 提问主流程 */
  function ask(q) {
    if (busy) return;
    q = String(q || "").trim();
    if (!q) return;
    if (!settings.apiKey.trim()) {
      addMsg("bot", '<div class="miss">还没有填 API Key。点右上角 <b>⚙</b> 填入 DeepSeek 的 Key 后再问。</div>');
      return;
    }

    busy = true;
    $("#aiSend").disabled = true;
    $("#aiInput").value = "";
    autosize();

    addMsg("user", esc(q));
    var bot = addMsg("bot", '<span class="typing"><i></i><i></i><i></i></span>');
    var bubble = $(".bubble", bot);

    loadRag().then(function () {
      var hits = retrieve(q);
      var g = Search.gate(hits);

      if (!g.ok) {
        // 未命中：不调用模型，直接说明站内没有
        var near = (hits || []).slice(0, 3).map(function (h) {
          return '<button class="source-btn" type="button" data-anchor="' + h.doc.anchor + '">'
            + esc(h.doc.title) + "</button>";
        }).join("");
        bubble.innerHTML = '<div class="miss"><b>站内暂无相关内容。</b><br>'
          + "这个问题在站内资料里找不到足够依据，所以没有调用模型（避免它用外部知识作答）。"
          + (near ? "<br><br>可能相关：" + near : "")
          + "</div>";
        pushHistory(q, "站内暂无相关内容。", []);
        return;
      }

      lastSources = hits.map(function (h) {
        return { anchor: h.doc.anchor, title: h.doc.title, kind: h.doc.kind };
      });

      // ③ 命中即跳转：滚到最相关章节
      if (settings.autoJump) {
        window.Jump(hits[0].doc.anchor, { quiet: true });
      }

      var acc = "";
      bubble.innerHTML = "";
      return askModel(buildMessages(q, hits), function (piece, done) {
        acc += piece;
        bubble.innerHTML = renderRich(acc) + (done ? sourcesHtml(hits) : "");
        scrollBottom();
        if (done) {
          pushHistory(q, acc, lastSources);
        }
      }).catch(function (err) {
        bubble.innerHTML = '<div class="miss">' + describeError(err) + "</div>";
        console.error("[ai]", err);
      });
    }).catch(function (err) {
      bubble.innerHTML = '<div class="miss">站内索引加载失败：' + esc(err.message)
        + "。请通过 HTTP 访问本页。</div>";
    }).then(function () {
      busy = false;
      $("#aiSend").disabled = false;
      scrollBottom();
    });
  }

  function pushHistory(q, a, sources) {
    history.unshift({
      id: "h" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      q: q, a: a, sources: sources || [], ts: Date.now()
    });
    saveHistory();
  }

  /* ---------------------------------------------------------------- 抽屉控制 */
  function openDrawer(view) {
    $("#drawer").classList.add("on");
    $("#scrim").classList.add("on");
    document.body.style.overflow = "hidden";
    if (view === "history") renderHistoryPanel();
    else if (view === "settings") renderSettings();
    else renderIntro();
    setTimeout(function () { $("#aiInput").focus(); }, 260);
  }
  function closeDrawer() {
    $("#drawer").classList.remove("on");
    $("#scrim").classList.remove("on");
    document.body.style.overflow = "";
  }

  function autosize() {
    var t = $("#aiInput");
    t.style.height = "auto";
    t.style.height = Math.min(132, t.scrollHeight) + "px";
  }

  /* ---------------------------------------------------------------- 绑定 */
  function bind() {
    $("#aiOpen").addEventListener("click", function () { openDrawer("intro"); });
    $("#aiClose").addEventListener("click", closeDrawer);
    $("#scrim").addEventListener("click", closeDrawer);
    $("#aiHist").addEventListener("click", function () { renderHistoryPanel(); });
    $("#aiCfg").addEventListener("click", function () { renderSettings(); });
    $("#aiClear").addEventListener("click", function (e) {
      e.preventDefault();
      if (confirm("清空当前对话？（历史记录仍保留在「☰」里）")) renderIntro();
    });

    $("#aiSend").addEventListener("click", function () { ask($("#aiInput").value); });

    $("#aiInput").addEventListener("input", autosize);
    $("#aiInput").addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        ask($("#aiInput").value);
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && $("#drawer").classList.contains("on")
          && !$("#lightbox").classList.contains("open")
          && !$("#paperModal").classList.contains("open")) {
        closeDrawer();
      }
    });

    // 抽屉内所有交互（事件委托）
    $("#aiBody").addEventListener("click", function (e) {
      var t = e.target;

      var askBtn = t.closest("[data-ask]");
      if (askBtn) { ask(askBtn.getAttribute("data-ask")); return; }

      var anchorBtn = t.closest("[data-anchor]");
      if (anchorBtn) {
        window.Jump(anchorBtn.getAttribute("data-anchor"));
        if (window.innerWidth < 900) closeDrawer();
        return;
      }

      var chip = t.closest("[data-cite]");
      if (chip) {
        var n = parseInt(chip.getAttribute("data-cite"), 10) - 1;
        var s = lastSources[n];
        if (s) window.Jump(s.anchor);
        return;
      }

      var del = t.closest("[data-del]");
      if (del) {
        var id = del.getAttribute("data-del");
        history = history.filter(function (h) { return h.id !== id; });
        saveHistory();
        renderHistoryPanel();
        return;
      }

      var hist = t.closest("[data-hid]");
      if (hist) {
        var h = history.filter(function (x) { return x.id === hist.getAttribute("data-hid"); })[0];
        if (!h) return;
        $("#aiBody").innerHTML = "";
        addMsg("user", esc(h.q));
        var b = addMsg("bot", renderRich(h.a));
        if (h.sources && h.sources.length) {
          $(".bubble", b).insertAdjacentHTML("beforeend", sourcesHtml(
            h.sources.map(function (s) { return { doc: s }; })));
        }
        lastSources = h.sources || [];
        return;
      }

      if (t.id === "expHist") {
        var blob = new Blob([JSON.stringify({
          exportedAt: new Date().toISOString(),
          site: "olefin-metathesis",
          history: history
        }, null, 2)], { type: "application/json" });
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "qa-history-" + new Date().toISOString().slice(0, 10) + ".json";
        a.click();
        URL.revokeObjectURL(a.href);
        return;
      }
      if (t.id === "clrHist") {
        if (confirm("清空全部 " + history.length + " 条记录？不可恢复。")) {
          history = [];
          saveHistory();
          renderHistoryPanel();
        }
        return;
      }

      if (t.id === "saveCfg") {
        settings.apiKey = $("#setKey").value.trim();
        settings.model = $("#setModel").value;
        settings.endpoint = $("#setEp").value.trim() || DEFAULT_SETTINGS.endpoint;
        settings.autoJump = $("#setJump").checked;
        saveSettings();
        $("#cfgMsg").innerHTML = '<span style="color:#166534">已保存到本机。</span>';
        return;
      }
      if (t.id === "backCfg") { renderIntro(); return; }
      if (t.id === "testCfg") {
        var msg = $("#cfgMsg");
        var key = $("#setKey").value.trim();
        var ep = $("#setEp").value.trim() || DEFAULT_SETTINGS.endpoint;
        if (!key) { msg.innerHTML = '<span style="color:#b3261e">先填 Key。</span>'; return; }
        msg.textContent = "测试中…";
        fetch(ep, {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": "Bearer " + key },
          body: JSON.stringify({
            model: $("#setModel").value,
            messages: [{ role: "user", content: "ping" }],
            max_tokens: 1,
            stream: false
          })
        }).then(function (r) {
          if (r.ok) {
            msg.innerHTML = '<span style="color:#166534">连接成功，可以用了。</span>';
          } else if (r.status === 401) {
            msg.innerHTML = '<span style="color:#b3261e">Key 无效（401）。</span>';
          } else if (r.status === 402) {
            msg.innerHTML = '<span style="color:#b3261e">余额不足（402）。</span>';
          } else {
            msg.innerHTML = '<span style="color:#b3261e">返回 ' + r.status + "，请检查模型或接口地址。</span>";
          }
        }).catch(function () {
          msg.innerHTML = '<span style="color:#b3261e">连不上：可能是网络或跨域限制。</span>';
        });
        return;
      }
    });
  }

  function boot() {
    bind();
    // 供自测/排障：在控制台里验证检索与门控，不改变页面行为
    window.__ai = {
      loadRag: loadRag,
      retrieve: function (q) {
        return loadRag().then(function () {
          var hits = retrieve(q);
          return {
            query: q,
            gate: Search.gate(hits),
            hits: hits.map(function (h) {
              return { score: +h.score.toFixed(2), strong: h.strong,
                       kind: h.doc.kind, anchor: h.doc.anchor, title: h.doc.title };
            })
          };
        });
      },
      ask: ask,
      settings: function () { return settings; }
    };
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
