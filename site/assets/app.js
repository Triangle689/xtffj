/* ===========================================================================
   app.js — 站点交互：进度条 / 导航高亮 / 站内搜索 / 图鉴 / 文献详情 / 筛选
   =========================================================================== */
(function () {
  "use strict";

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var data = null;
  var figIndex = {};          // id -> figure
  var figOrder = [];          // 图档顺序
  var paperIndex = {};        // id -> paper

  /* ---------------------------------------------------------------- 工具 */
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  window.esc = esc;

  function flash(el) {
    if (!el) return;
    el.classList.remove("flash");
    void el.offsetWidth;
    el.classList.add("flash");
    setTimeout(function () { el.classList.remove("flash"); }, 1800);
  }

  /* 平滑跳转到锚点并高亮 —— AI 回答也复用它 */
  window.Jump = function (anchor, opts) {
    opts = opts || {};
    var id = String(anchor || "").replace(/^#/, "");
    var el = document.getElementById(id);
    if (!el) return false;
    var top = el.getBoundingClientRect().top + window.pageYOffset
      - (parseInt(getComputedStyle(document.documentElement).getPropertyValue("--header-h"), 10) || 64) - 20;
    window.scrollTo({ top: top, behavior: opts.instant ? "auto" : "smooth" });
    flash(el);
    if (!opts.quiet) history.replaceState(null, "", "#" + id);
    return true;
  };

  /* ---------------------------------------------------------------- 进度条 */
  function initProgress() {
    var bar = $("#progress");
    var toTop = $("#toTop");
    function upd() {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      var p = h > 0 ? (window.pageYOffset / h) * 100 : 0;
      bar.style.width = p.toFixed(2) + "%";
      toTop.classList.toggle("on", window.pageYOffset > 900);
    }
    window.addEventListener("scroll", upd, { passive: true });
    window.addEventListener("resize", upd);
    upd();
    toTop.addEventListener("click", function () {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  /* ---------------------------------------------------------------- 导航高亮 */
  function initNav() {
    var links = $$("[data-nav]");
    var map = {};
    links.forEach(function (a) {
      var id = a.getAttribute("href").slice(1);
      var el = document.getElementById(id);
      if (el) map[id] = a;
    });
    var sections = Object.keys(map).map(function (id) {
      return document.getElementById(id);
    }).filter(Boolean);

    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) return;
        links.forEach(function (a) { a.classList.remove("active"); });
        var a = map[en.target.id];
        if (a) a.classList.add("active");
      });
    }, { rootMargin: "-45% 0px -50% 0px", threshold: 0 });

    sections.forEach(function (s) { io.observe(s); });

    // 时间线节点
    $$(".tl-node").forEach(function (n) {
      n.addEventListener("click", function () {
        window.Jump("#" + n.getAttribute("data-goto"));
      });
    });
  }

  /* ---------------------------------------------------------------- 搜索索引 */
  function buildDocs() {
    var docs = [];
    docs.push({
      kind: "总览", anchor: "#top", title: "关于本站",
      text: "烯烃复分解 1955–2024 研究脉络，45 篇核实文献，23 张原文图，5 个阶段。"
    });
    data.phases.forEach(function (ph) {
      docs.push({
        kind: "阶段", anchor: "#phase-" + ph.id,
        title: ph.period + "　" + ph.name,
        text: ph.tagline + " " + ph.lede + " " + ph.points.map(function (p) {
          return p.h + "：" + p.t;
        }).join(" "),
        keys: ph.insight
      });
    });
    data.papers.forEach(function (p) {
      docs.push({
        kind: "文献", anchor: "#paper-" + p.id, paper: p.id,
        title: p.authors + "（" + p.year + "）",
        text: p.title + " " + p.journal + " " + p.why,
        keys: p.doi
      });
    });
    data.figures.forEach(function (f) {
      docs.push({
        kind: "图", anchor: "#fig-" + f.id, figure: f.id,
        title: "图 " + f.no + "｜" + f.caption.slice(0, 34),
        text: f.caption + " " + f.usage + " " + f.cite,
        keys: f.section
      });
    });
    data.gaps.forEach(function (g) {
      docs.push({
        kind: "缺口", anchor: "#gaps",
        title: "缺口 " + g.no + "：" + g.title,
        text: g.text + " " + g.fix
      });
    });
    docs.push({
      kind: "方法", anchor: "#method", title: "方法与出处",
      text: "图的裁切方式、DOI 核实方法、《有机化学》未核实的说明、AI 问答的边界。"
    });
    return docs;
  }

  /* ---------------------------------------------------------------- 搜索 UI */
  function initSearch() {
    var input = $("#q");
    var box = $("#results");
    var idx = Search.buildIndex(buildDocs());
    var sel = -1;
    var current = [];

    function snippet(text, q) {
      var s = String(text || "");
      var n = Search.norm(q);
      var pos = -1;
      // 找第一个命中位置（用原始片段匹配）
      for (var i = 0; i + 2 <= n.length && pos < 0; i++) {
        pos = s.indexOf(n.slice(i, i + 2));
      }
      var start = pos > 40 ? pos - 40 : 0;
      var piece = s.slice(start, start + 96);
      return (start > 0 ? "…" : "") + Search.highlight(piece, q) + (s.length > start + 96 ? "…" : "");
    }

    function render(q) {
      current = Search.search(idx, q, 12);
      sel = -1;
      if (!q.trim()) { close(); return; }
      if (!current.length) {
        box.innerHTML = '<div class="empty">没有匹配的内容，换个词试试（如「Z-选择性」「Chauvin」「缺口」）</div>';
        open();
        return;
      }
      var groups = {};
      current.forEach(function (r) {
        (groups[r.doc.kind] = groups[r.doc.kind] || []).push(r);
      });
      var html = "";
      ["阶段", "文献", "图", "缺口", "方法", "总览"].forEach(function (k) {
        if (!groups[k]) return;
        html += '<div class="group">' + k + "</div>";
        groups[k].forEach(function (r) {
          var i = current.indexOf(r);
          html += '<a class="result" role="option" data-i="' + i + '" href="' + r.doc.anchor + '">'
            + "<b>" + Search.highlight(esc(r.doc.title), q) + "</b>"
            + "<span>" + snippet(r.doc.text, q) + "</span></a>";
        });
      });
      box.innerHTML = html;
      open();
    }

    function open() { box.classList.add("open"); input.setAttribute("aria-expanded", "true"); }
    function close() { box.classList.remove("open"); input.setAttribute("aria-expanded", "false"); sel = -1; }

    function choose(i) {
      var r = current[i];
      if (!r) return;
      close();
      input.blur();
      var d = r.doc;
      if (d.figure) { window.openFigure(d.figure); return; }
      if (d.paper) { window.openPaper(d.paper); return; }
      window.Jump(d.anchor);
    }

    var t = null;
    input.addEventListener("input", function () {
      clearTimeout(t);
      var v = input.value;
      t = setTimeout(function () { render(v); }, 90);
    });

    input.addEventListener("keydown", function (e) {
      var items = $$(".result", box);
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        if (!items.length) return;
        sel = e.key === "ArrowDown"
          ? Math.min(items.length - 1, sel + 1)
          : Math.max(0, sel - 1);
        items.forEach(function (el) { el.classList.remove("sel"); });
        items[sel].classList.add("sel");
        items[sel].scrollIntoView({ block: "nearest" });
        return;
      }
      if (e.key === "Enter") {
        e.preventDefault();
        if (sel >= 0) { choose(parseInt($$(".result", box)[sel].getAttribute("data-i"), 10)); }
        else if (current.length) { choose(0); }
        return;
      }
      if (e.key === "Escape") { close(); input.blur(); }
    });

    box.addEventListener("click", function (e) {
      var a = e.target.closest(".result");
      if (!a) return;
      e.preventDefault();
      choose(parseInt(a.getAttribute("data-i"), 10));
    });

    document.addEventListener("click", function (e) {
      if (!e.target.closest(".search")) close();
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "/" && !/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) {
        e.preventDefault();
        input.focus();
        input.select();
      }
    });
  }

  /* ---------------------------------------------------------------- 图鉴 */
  function initLightbox() {
    var lb = $("#lightbox");
    var img = $("#lbImg");
    var cur = -1;

    function show(fid) {
      var f = figIndex[fid];
      if (!f) return;
      cur = figOrder.indexOf(fid);
      img.src = (window.__imgFor && window.__imgFor(f.file)) || ("assets/img/" + f.file);
      img.alt = f.caption;
      $("#lbK").textContent = "图 " + f.no + " · " + f.figNo + " · 原文第 " + f.docPage + " 页";
      $("#lbC").textContent = f.caption;
      $("#lbS").innerHTML = f.cite;
      $("#lbU").textContent = "用法：" + f.usage;
      lb.classList.add("open");
      document.body.style.overflow = "hidden";
      $("#lbPrev").style.visibility = cur > 0 ? "visible" : "hidden";
      $("#lbNext").style.visibility = cur < figOrder.length - 1 ? "visible" : "hidden";
    }

    function close() {
      lb.classList.remove("open");
      document.body.style.overflow = "";
      cur = -1;
    }

    function step(d) {
      var n = cur + d;
      if (n < 0 || n >= figOrder.length) return;
      show(figOrder[n]);
    }

    window.openFigure = show;

    document.addEventListener("click", function (e) {
      var b = e.target.closest("[data-open-fig]");
      if (b) { show(b.getAttribute("data-open-fig")); return; }
      if (e.target.closest("[data-close]")) {
        close();
        closePaper();
        return;
      }
      if (e.target === lb) close();
    });

    $("#lbPrev").addEventListener("click", function () { step(-1); });
    $("#lbNext").addEventListener("click", function () { step(1); });

    document.addEventListener("keydown", function (e) {
      if (!lb.classList.contains("open")) return;
      if (e.key === "Escape") close();
      if (e.key === "ArrowLeft") step(-1);
      if (e.key === "ArrowRight") step(1);
    });
  }

  /* ---------------------------------------------------------------- 文献详情 */
  function closePaper() {
    $("#paperModal").classList.remove("open");
    document.body.style.overflow = "";
  }

  function initPaperModal() {
    var box = $("#paperModal");

    window.openPaper = function (pid) {
      var p = paperIndex[pid];
      if (!p) return;
      var ph = data.phases.filter(function (x) { return x.papers.indexOf(pid) >= 0; })[0];
      $("#pmKicker").textContent =
        (p.type === "R" ? "综述 / 专著 / 诺奖讲座" : "原始研究论文") +
        (p.inDoc ? " · 文档原列" : "") + (ph ? " · 阶段 " + ph.no + " " + ph.name : "");
      $("#pmTitle").textContent = p.title;
      $("#pmCite").innerHTML = esc(p.authors) + ". <i>" + esc(p.journal) + "</i> <b>"
        + esc(p.year) + "</b>, " + esc(p.vol) + ", " + esc(p.pages) + ".";
      $("#pmWhy").innerHTML = "<b>为什么重要　</b>" + esc(p.why);
      $("#pmDoi").innerHTML = p.doiUrl
        ? 'DOI: <a href="' + p.doiUrl + '" target="_blank" rel="noopener">' + esc(p.doi) + "</a>"
        : "DOI：本条为中文文献，Crossref 未收录，暂未核实。";
      var row = "";
      if (p.doiUrl) {
        row += '<a class="btn primary" href="' + p.doiUrl + '" target="_blank" rel="noopener">在 doi.org 打开 ↗</a>';
      }
      if (ph) {
        row += '<button class="btn" type="button" data-goto-phase="' + ph.id + '">看这一阶段 →</button>';
      }
      $("#pmRow").innerHTML = row;
      box.classList.add("open");
      document.body.style.overflow = "hidden";
    };

    box.addEventListener("click", function (e) {
      if (e.target === box || e.target.closest("[data-close]")) { closePaper(); return; }
      var g = e.target.closest("[data-goto-phase]");
      if (g) {
        closePaper();
        window.Jump("#phase-" + g.getAttribute("data-goto-phase"));
      }
    });

    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closePaper();
    });

    $("#pBody").addEventListener("click", function (e) {
      var tr = e.target.closest("tr[data-paper]");
      if (tr) window.openPaper(tr.getAttribute("data-paper"));
    });
    $("#pBody").addEventListener("keydown", function (e) {
      var tr = e.target.closest("tr[data-paper]");
      if (tr && (e.key === "Enter" || e.key === " ")) {
        e.preventDefault();
        window.openPaper(tr.getAttribute("data-paper"));
      }
    });
  }

  /* ---------------------------------------------------------------- 文献筛选 */
  function initFilters() {
    var state = { type: "all", doc: false, phase: "" };
    var rows = $$("#pBody tr");
    var count = $("#pCount");

    function apply() {
      var n = 0;
      rows.forEach(function (tr) {
        var ok = true;
        if (state.type !== "all" && tr.getAttribute("data-type") !== state.type) ok = false;
        if (state.doc && !tr.querySelector(".tag.doc")) ok = false;
        if (state.phase && tr.getAttribute("data-phase") !== state.phase) ok = false;
        tr.style.display = ok ? "" : "none";
        if (ok) n++;
      });
      count.textContent = "显示 " + n + " / " + rows.length + " 篇";
      $("#papers").classList.toggle("filtered", !!state.phase);
    }

    $$("#filters .chip").forEach(function (c) {
      c.addEventListener("click", function () {
        $$("#filters .chip").forEach(function (x) { x.classList.remove("on"); });
        c.classList.add("on");
        if (c.hasAttribute("data-f-type")) state.type = c.getAttribute("data-f-type");
        if (c.hasAttribute("data-f-doc")) state.doc = true;
        state.phase = "";
        apply();
      });
    });

    // 从阶段页跳过来时按阶段筛选
    $$("[data-filter-phase]").forEach(function (a) {
      a.addEventListener("click", function (e) {
        e.preventDefault();
        state.type = "all"; state.doc = false;
        state.phase = a.getAttribute("data-filter-phase");
        $$("#filters .chip").forEach(function (x) { x.classList.toggle("on", x.hasAttribute("data-f-type")); });
        apply();
        window.Jump("#papers");
      });
    });

    apply();
  }

  /* ---------------------------------------------------------------- 入场动画 */
  function initReveal() {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var els = $$(".sec-head, .phase, .fig, .cat, .gap, .stat");
    els.forEach(function (el) { el.style.willChange = "opacity, transform"; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (en.isIntersecting) {
          en.target.style.transition = "opacity .5s var(--ease), transform .5s var(--ease)";
          en.target.style.opacity = "1";
          en.target.style.transform = "none";
          io.unobserve(en.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px" });
    els.forEach(function (el, i) {
      el.style.opacity = "0";
      el.style.transform = "translateY(10px)";
      io.observe(el);
    });
  }

  /* ---------------------------------------------------------------- 启动 */
  function boot() {
    figOrder = data.figures.map(function (f) { return f.id; });
    data.figures.forEach(function (f) { figIndex[f.id] = f; });
    data.papers.forEach(function (p) { paperIndex[p.id] = p; });

    initProgress();
    initNav();
    initSearch();
    initLightbox();
    initPaperModal();
    initFilters();
    initReveal();

    // 支持直接带着 #anchor 打开
    if (location.hash && location.hash !== "#") {
      setTimeout(function () { window.Jump(location.hash, { instant: true, quiet: true }); }, 60);
    }
  }

  window.SITE_READY = fetch("data/site.json", { cache: "no-cache" })
    .then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    })
    .then(function (d) {
      data = d;
      window.SITE = d;
      boot();
      return d;
    })
    .catch(function (err) {
      console.error("[site] 数据加载失败", err);
      document.querySelector(".hero-lede").insertAdjacentHTML("afterend",
        '<p style="color:#b3261e;font-size:14px">数据文件加载失败（' + esc(err.message) +
        "）。请通过 HTTP 访问本页（例如本地运行 <code>python -m http.server</code>），"
        + "直接双击打开 HTML 时浏览器会拦截 fetch。</p>");
    });
})();

