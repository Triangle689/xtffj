# -*- coding: utf-8 -*-
"""Render site/index.html from site/data/site.json (pre-rendered, no-JS readable)."""
import html
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SITE = os.path.join(BASE, "site")
DATA = os.path.join(SITE, "data")

NAV = [
    ("#thread", "研究脉络"),
    ("#phase-p1", "五个阶段"),
    ("#catalysts", "催化剂谱系"),
    ("#gaps", "文献缺口"),
    ("#papers", "文献总览"),
    ("#figures", "图片档案"),
    ("#method", "方法与出处"),
]


def esc(s):
    return html.escape(str(s), quote=True)


def rich(s):
    """把 *斜体* / **加粗** 转成标签（先转义）。"""
    s = esc(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    return s


def dims(fn):
    p = os.path.join(SITE, "assets", "img", fn)
    with Image.open(p) as im:
        return im.size


def main():
    site = json.load(open(os.path.join(DATA, "site.json"), encoding="utf-8"))
    figs = {f["id"]: f for f in site["figures"]}
    papers = {p["id"]: p for p in site["papers"]}
    m = site["meta"]

    # ---------------- 图
    def figure(fid, lead=False):
        f = figs[fid]
        w, h = dims(f["file"])
        return f"""
      <figure class="fig{' fig-lead' if lead else ''}" id="fig-{f['id']}">
        <button class="fig-img" type="button" data-open-fig="{f['id']}"
                aria-label="放大查看图 {f['no']}">
          <img src="assets/img/{f['file']}" alt="{esc(f['caption'])}"
               width="{w}" height="{h}" loading="lazy" decoding="async">
          <span class="zoom">点击放大</span>
        </button>
        <figcaption>
          <div class="fig-no">图 {f['no']} · {esc(f['figNo'])}</div>
          <div class="fig-cap">{esc(f['caption'])}</div>
          <div class="fig-src">{rich(f['cite'])} · 原文第 {f['docPage']} 页 · {esc(f['section'])}</div>
        </figcaption>
      </figure>"""

    # ---------------- 阶段
    phase_html = []
    for ph in site["phases"]:
        pts = "\n".join(
            f'<li class="point"><h4>{esc(p["h"])}</h4><p>{esc(p["t"])}</p></li>'
            for p in ph["points"])
        fids = ph["figures"]
        lead_f = figure(fids[0], lead=True)
        rest = "\n".join(figure(x) for x in fids[1:])
        rest_block = f'<div class="figs g2">{rest}</div>' if rest else ""
        n_papers = len(ph["papers"])
        phase_html.append(f"""
    <section class="phase" id="phase-{ph['id']}" data-phase="{ph['id']}">
      <div class="wrap">
        <div class="phase-grid">
          <aside class="phase-aside">
            <div class="phase-no">{ph['no']}</div>
            <div class="phase-period">{esc(ph['period'])}</div>
            <h2 class="phase-name">{esc(ph['name'])}</h2>
            <p class="phase-tag">{esc(ph['tagline'])}</p>
            <blockquote class="phase-insight">{esc(ph['insight'])}</blockquote>
          </aside>
          <div class="phase-body">
            <p class="lede">{esc(ph['lede'])}</p>
            <ul class="points">{pts}</ul>
            <div class="figs fig-lead-wrap">{lead_f}</div>
            {rest_block}
            <p class="fig-src" style="margin-top:22px">
              本阶段关联 {n_papers} 篇文献 ·
              <a href="#papers" data-filter-phase="{ph['id']}">在文献总览中查看 →</a>
            </p>
          </div>
        </div>
      </div>
    </section>""")

    # ---------------- 时间线
    tl = "\n".join(f"""
        <button class="tl-node" type="button" data-goto="phase-{ph['id']}">
          <span class="tl-dot"></span>
          <span class="tl-period">{esc(ph['period'])}</span>
          <span class="tl-name">{esc(ph['name'])}</span>
          <span class="tl-tag">{esc(ph['tagline'])}</span>
        </button>""" for ph in site["phases"])

    # ---------------- 催化剂
    cats = []
    for c in site["catalysts"]:
        f = figs[c["fig"]]
        w, h = dims(f["file"])
        cats.append(f"""
        <article class="cat">
          <button class="fig-img" type="button" data-open-fig="{f['id']}" aria-label="放大查看">
            <img src="assets/img/{f['file']}" alt="{esc(f['caption'])}" width="{w}" height="{h}"
                 loading="lazy" decoding="async">
            <span class="zoom">点击放大</span>
          </button>
          <h4>{esc(c['name'])}</h4>
          <p>{esc(c['note'])}</p>
        </article>""")

    # ---------------- 缺口
    gaps = "\n".join(f"""
        <article class="gap" id="gap-{g['id']}">
          <div class="n">缺口 {g['no']}</div>
          <h4>{esc(g['title'])}</h4>
          <p>{esc(g['text'])}</p>
          <div class="fix">本次处理：{esc(g['fix'])}</div>
        </article>""" for g in site["gaps"])

    # ---------------- 文献表
    phase_short = {ph["id"]: f"{ph['no']} {ph['name']}" for ph in site["phases"]}
    paper_of_phase = {}
    for ph in site["phases"]:
        for pid in ph["papers"]:
            paper_of_phase[pid] = ph["id"]
    rows = []
    for p in site["papers"]:
        tag = ('<span class="tag r">综述</span>' if p["type"] == "R"
               else '<span class="tag p">原始</span>')
        doc = '<span class="tag doc">文档原列</span>' if p["inDoc"] else ""
        ph = paper_of_phase.get(p["id"], "")
        rows.append(f"""
          <tr id="paper-{p['id']}" data-paper="{p['id']}" data-type="{p['type']}"
              data-phase="{ph}" tabindex="0">
            <td class="t-year">{p['year']}</td>
            <td>{tag}{doc}</td>
            <td class="t-authors">{esc(p['authors'])}</td>
            <td class="t-journal">{esc(p['journal'])}</td>
            <td class="t-title">{esc(p['title'])}</td>
            <td class="t-phase">{esc(phase_short.get(ph, ''))}</td>
          </tr>""")

    # ---------------- 图档
    arch = "\n".join(figure(f["id"]) for f in site["figures"])

    # ---------------- 方法
    method_paras = "\n".join(f"<p>{esc(x)}</p>" for x in site["method"]["paras"])
    method_limits = "\n".join(f"<li>{esc(x)}</li>" for x in site["method"]["limits"])

    # ---------------- 统计
    stats = "\n".join(f"""
          <div class="stat">
            <b>{esc(s['v'])}</b><span>{esc(s['l'])}</span><em>{esc(s['n'])}</em>
          </div>""" for s in site["stats"])

    nav = "\n".join(f'<a href="{h}" data-nav>{esc(t)}</a>' for h, t in NAV)

    payload = json.dumps(dict(
        papers=site["papers"], figures=site["figures"],
        phases=[dict(id=p["id"], no=p["no"], name=p["name"], period=p["period"]) for p in site["phases"]],
    ), ensure_ascii=False, separators=(",", ":"))

    doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(m['title'])} · {esc(m['subtitle'])}</title>
<meta name="description" content="烯烃复分解反应 1955–2024 研究脉络：45 篇核实文献、23 张原文图、5 个阶段。含站内 AI 问答。">
<meta name="color-scheme" content="light">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>

<div class="progress" id="progress" aria-hidden="true"></div>

<header class="topbar">
  <a class="brand" href="#top">
    <span class="brand-mark">C=C</span>
    <span class="brand-text"><b>烯烃复分解</b><em>Olefin Metathesis</em></span>
  </a>
  <nav class="nav" id="nav" aria-label="主导航">{nav}</nav>
  <div class="search" role="search">
    <input id="q" type="search" placeholder="搜索文献、图、阶段…" autocomplete="off"
           aria-label="站内搜索" aria-expanded="false" aria-controls="results">
    <span class="kbd">/</span>
    <div class="results" id="results" role="listbox" aria-label="搜索结果"></div>
  </div>
  <button class="ai-btn" id="aiOpen" type="button">
    <span class="dot" aria-hidden="true"></span><span class="lbl">AI 问答</span>
  </button>
</header>

<main>
  <!-- ============================================================ HERO -->
  <section class="hero" id="top">
    <div class="wrap">
      <span class="hero-kicker">{esc(m['course'])}</span>
      <h1>{esc(m['title'])}<br><span class="thin">{esc(m['subtitle'])}</span></h1>
      <p class="hero-en">{esc(m['en'])}</p>
      <p class="hero-lede">
        碳碳双键被切开，再以另一种方式拼起来。这个反应 1955 年在三家工业实验室里被各自看见，
        1971 年得到一个当时<span class="hl">还无法被验证</span>的机理假设，
        1990 年才第一次拿到可以分离的分子，1995 年后成为合成路线图上的常规工具，
        2011 年之后问题变成「能不能定向」。
      </p>
      <div class="stats">{stats}</div>
    </div>
  </section>

  <!-- ============================================================ 脉络 -->
  <section class="sec sec-surface" id="thread">
    <div class="wrap">
      <div class="sec-head">
        <div class="sec-no">§1</div>
        <div style="flex:1 1 420px">
          <h2 class="sec-title">研究脉络</h2>
          <p class="sec-sub">五个阶段，六个转折点。每次进步都不是新反应，而是给同一个反应补上一块原来缺的证据或配体。</p>
        </div>
      </div>
      <div class="timeline">
        <div class="tl-rail" id="tlRail">{tl}
        </div>
      </div>
      <p class="fig-src" style="margin-top:26px">
        点击任一时间点跳到对应阶段。脉络的另一种读法：
        <b>现象先于概念</b>（1955–1967）→ <b>假设先于证据</b>（1971–1990）→
        <b>结构先于工具</b>（1990–1995）→ <b>工具先于控制</b>（1999–2011）。
      </p>
    </div>
  </section>

  <!-- ============================================================ 阶段 -->
  {''.join(phase_html)}

  <!-- ============================================================ 催化剂 -->
  <section class="sec sec-surface" id="catalysts">
    <div class="wrap">
      <div class="sec-head">
        <div class="sec-no">§3</div>
        <div style="flex:1 1 420px">
          <h2 class="sec-title">催化剂谱系</h2>
          <p class="sec-sub">把「为什么换金属、为什么换配体」摊在同一组结构图上：Mo 给结构与活性，Ru 给耐受，NHC 给引发速率，手性配体给选择性。</p>
        </div>
      </div>
      <div class="cats">{''.join(cats)}
      </div>
    </div>
  </section>

  <!-- ============================================================ 缺口 -->
  <section class="sec" id="gaps">
    <div class="wrap">
      <div class="sec-head">
        <div class="sec-no">§4</div>
        <div style="flex:1 1 420px">
          <h2 class="sec-title">原始清单缺了什么</h2>
          <p class="sec-sub">研讨文档给了 11 条文献：7 条英文（3 篇诺奖讲座合集 + 4 篇综述）+ 5 条中文综述。全部是二手总结，<b>原始研究论文 0 篇</b>。</p>
        </div>
      </div>
      <div class="gaps">{gaps}
      </div>
    </div>
  </section>

  <!-- ============================================================ 文献 -->
  <section class="sec sec-surface" id="papers">
    <div class="wrap">
      <div class="sec-head">
        <div class="sec-no">§5</div>
        <div style="flex:1 1 420px">
          <h2 class="sec-title">文献总览</h2>
          <p class="sec-sub">45 篇，英文条目全部经 Crossref 比对题名、刊名、卷、页、年份。点击任一行查看详情与 DOI。</p>
        </div>
      </div>
      <div class="filters" id="filters">
        <button class="chip on" type="button" data-f-type="all">全部 45</button>
        <button class="chip" type="button" data-f-type="R">综述 14</button>
        <button class="chip" type="button" data-f-type="P">原始论文 31</button>
        <button class="chip" type="button" data-f-doc="1">文档原列 7</button>
        <span class="count" id="pCount"></span>
      </div>
      <div class="table-wrap">
        <table class="papers">
          <thead>
            <tr>
              <th scope="col">年份</th><th scope="col">类型</th><th scope="col">作者</th>
              <th scope="col">期刊</th><th scope="col">标题</th><th scope="col">阶段</th>
            </tr>
          </thead>
          <tbody id="pBody">{''.join(rows)}
          </tbody>
        </table>
      </div>
    </div>
  </section>

  <!-- ============================================================ 图档 -->
  <section class="sec" id="figures">
    <div class="wrap">
      <div class="sec-head">
        <div class="sec-no">§6</div>
        <div style="flex:1 1 420px">
          <h2 class="sec-title">图片档案</h2>
          <p class="sec-sub">23 张图全部取自原文 PDF，450 dpi，已去除图注与页眉，未做任何重绘。点击放大，可左右翻页。</p>
        </div>
      </div>
      <div class="arch">{arch}
      </div>
    </div>
  </section>

  <!-- ============================================================ 方法 -->
  <section class="sec sec-surface" id="method">
    <div class="wrap">
      <div class="sec-head">
        <div class="sec-no">§7</div>
        <div style="flex:1 1 420px">
          <h2 class="sec-title">{esc(site['method']['title'])}</h2>
          <p class="sec-sub">数据、图与 AI 问答各自的边界。</p>
        </div>
      </div>
      <div class="method method-grid">
        <div>{method_paras}</div>
        <aside class="limits">
          <h4>已知局限</h4>
          <ul>{method_limits}</ul>
        </aside>
      </div>
    </div>
  </section>
</main>

<footer>
  <div class="wrap foot-grid">
    <div class="meta">
      <b>烯烃复分解 · 从偶然发现到合成工具</b><br>
      现代化学创新思维训练 · 研讨主题 2 · 更新 {esc(m['updated'])}<br>
      45 篇文献 · 23 张原文图 · 5 个研究阶段
    </div>
    <div class="meta" style="text-align:right">
      DOI 链接跳转 <a href="https://doi.org" target="_blank" rel="noopener">doi.org</a>，需机构订阅<br>
      AI 问答仅使用站内内容，不联网、不使用模型自身知识
    </div>
  </div>
</footer>

<button class="to-top" id="toTop" type="button" aria-label="回到顶部">↑</button>

<!-- ============================================================ 浮层 -->
<div class="overlay" id="lightbox" role="dialog" aria-modal="true" aria-label="图片查看">
  <div class="lightbox-panel">
    <button class="x" type="button" data-close aria-label="关闭">✕</button>
    <button class="lb-nav lb-prev" type="button" id="lbPrev" aria-label="上一张">‹</button>
    <button class="lb-nav lb-next" type="button" id="lbNext" aria-label="下一张">›</button>
    <img id="lbImg" alt="">
    <div class="lb-cap">
      <div class="k" id="lbK"></div>
      <div class="c" id="lbC"></div>
      <div class="s" id="lbS"></div>
      <div class="u" id="lbU"></div>
    </div>
  </div>
</div>

<div class="overlay" id="paperModal" role="dialog" aria-modal="true" aria-label="文献详情">
  <div class="lightbox-panel paper-panel">
    <button class="x" type="button" data-close aria-label="关闭">✕</button>
    <div class="kicker" id="pmKicker"></div>
    <h3 id="pmTitle"></h3>
    <p class="cite" id="pmCite"></p>
    <div class="why" id="pmWhy"></div>
    <div class="doi" id="pmDoi"></div>
    <div class="row" id="pmRow"></div>
  </div>
</div>

<!-- ============================================================ AI 抽屉 -->
<div class="drawer-scrim" id="scrim"></div>
<aside class="drawer" id="drawer" role="dialog" aria-modal="true" aria-label="AI 问答">
  <div class="drawer-head">
    <h3>AI 问答</h3>
    <span class="badge" id="aiBadge">站内</span>
    <span class="sp"></span>
    <button class="icon-btn" type="button" id="aiHist" title="历史记录" aria-label="历史记录">☰</button>
    <button class="icon-btn" type="button" id="aiCfg" title="设置" aria-label="设置">⚙</button>
    <button class="icon-btn" type="button" id="aiClose" title="关闭" aria-label="关闭">✕</button>
  </div>
  <div class="drawer-scroll" id="aiScroll">
    <div id="aiBody"></div>
  </div>
  <div class="drawer-foot">
    <div class="ask-row">
      <textarea id="aiInput" rows="1" placeholder="问点什么，例如：Chauvin 的机理为什么难验证？"></textarea>
      <button class="send" id="aiSend" type="button" aria-label="发送">↑</button>
    </div>
    <div class="foot-note">
      <span>仅用站内内容作答 ·</span>
      <a href="#" id="aiClear">清空对话</a>
    </div>
  </div>
</aside>

<script src="assets/search.js" defer></script>
<script src="assets/app.js" defer></script>
<script src="assets/ai.js" defer></script>
</body>
</html>
"""
    out = os.path.join(SITE, "index.html")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(doc)
    print("wrote", out, len(doc), "bytes")


if __name__ == "__main__":
    main()

