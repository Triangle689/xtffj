# -*- coding: utf-8 -*-
"""deck_explain — 幻灯引擎（版式照「Catellani 反应」参照讲稿）。

页面只放**短句**：标题 + 蓝色论点 + 2–4 张浅蓝卡片（或短要点）+ 页底结论条。
需要展开的推理、结构说明、数据出处，写进 `"notes"`（PowerPoint 备注 / 演讲者视图），
不占版面。模板本身就是这么用的：卡片写“A · 传统偶联 —— 仅 ipso 官能化”，
讲的人在备注里展开。

页面类型
--------
  cover     封面（课题行 / 主标题 40 / 英文副题 14 / 报告人 24 / 单位 20 / 日期 16）
  toc       叙事线（两栏编号目录，页码按 section 自动算）
  section   分节页（96 pt 编号 / 36 pt 标题 / 16 pt 灰副题）
  author    通讯作者页（左侧信息卡 + 右侧短要点）
  fig_text  图左 + 右侧 2–4 张短句卡片（或短要点 `points`）
  fig_steps 图左 + 右侧 2–5 张编号步骤卡（①…）
  fig_wide  整幅横排图 + 图下一行 2–3 张卡片
  text      2–4 栏短条目（细线 + 小标题 + 一句说明），即讲稿第 27 页那种
  end       小结：2–3 栏“编号卡 + 短条目” + 可选箭头链

短句规格（audit_deck.py 会检查）
------------------------------
  卡片 / 条目 ≤ 46 字（13 pt 两行，卡片高 0.66 in）
  步骤卡细节 ≤ 40 字
  标题 ≤ 29 字，论点 ≤ 36 字，结论条 ≤ 40 字
  一页可见正文 40–320 字；再多的内容属于备注

字段：`cards` / `points` / `steps` / `items` / `cols` / `chain`、
`cite`（页脚引文，*期刊* 斜体、**年份** 加粗）、`caption`（图注）、
`takeaway`（结论条）、`notes`（备注：讲解词，可多段）。

用法
----
  python deck_explain.py spec.json out.pptx            # 生成
  python deck_explain.py spec.json out.pptx --check    # 只做容量估算
"""
import json
import os
import sys

from PIL import Image
from pptx import Presentation
from pptx.util import Inches

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deck_kit as K  # noqa: E402

NAVY, INK, GRAY = K.NAVY, K.INK, K.GRAY
W, H, M, CW = K.W, K.H, K.M, K.CW
Y_TOP, Y_BOT = K.Y_TOP, K.Y_BOT
BODY_H = Y_BOT - Y_TOP                    # 3.42 in

BODY = K.T_BODY            # 13
GRID_BODY = 12             # 细线网格页的说明行

MAX_ITEM = 46              # 卡片 / 条目上限（两行）
MAX_STEP = 40              # 步骤卡细节上限
MAX_TOTAL = 320            # 一页可见正文字数上限


# ---------------------------------------------------------------- 估算
_est_lines = K.est_lines
_card_h = K.card_h


def _lines_for(c, width):
    """卡片行数：三段式（标签 + 粗体 + 灰释文）的释文独占一行，要单独算。"""
    c = list(c) + ["", ""]
    lead, head, detail = c[0], c[1], c[2]
    n = _est_lines(f"{lead} {head}", width - 0.20, BODY)
    if detail:
        n += _est_lines(detail, width - 0.20, BODY)
    return n


def _h_for(lines):
    return min(1.10, max(0.50, 0.30 + lines * BODY * 1.10 / 72.0))


def _stack(heights, gap_max=0.34, gap_min=0.10):
    """卡片竖向排布：总高不够就撑开间距，太多就压到最小间距。返回 (y 列表, gap)。"""
    n = len(heights)
    total = sum(heights)
    gap = gap_max if n == 1 else max(gap_min, min(gap_max, (BODY_H - total) / (n - 1)))
    gap = min(gap, gap_max) if n > 1 else 0
    block = total + gap * (n - 1)
    y = Y_TOP + max(0.0, (BODY_H - block) / 2)
    out = []
    for h in heights:
        out.append(y)
        y += h + gap
    return out, gap


# ---------------------------------------------------------------- 体检
def check_fit(slides, tag=""):
    """估算：标题/论点/结论条是否折行，卡片是否会撑破内容区。"""
    warn = []
    for i, s in enumerate(slides, 1):
        if not s:
            continue
        t = s["type"]
        title = s.get("title", "")
        if t != "cover" and t != "section" and _est_lines(title, CW, K.T_TITLE) > 1:
            warn.append(f"{tag} p{i}: 标题“{title}”超过一行（22 pt 约 29 字）")
        if _est_lines(s.get("core", ""), CW - 1.10, K.T_CLAIM) > 1:
            warn.append(f"{tag} p{i}: 论点超过一行（16 pt 约 36 字）")
        if s.get("takeaway") and len(s["takeaway"]) > 40:
            warn.append(f"{tag} p{i}: 结论条 {len(s['takeaway'])} 字（> 40）")

        def cw_of(img_w):
            return W - M - (M + img_w + 0.38)

        if t in ("fig_text", "fig_wide") and s.get("cards"):
            tw = cw_of(s.get("img_w", 4.5)) if t == "fig_text" else \
                (CW - 0.20 * (len(s["cards"]) - 1)) / len(s["cards"])
            hs = [_h_for(_lines_for(c, tw)) for c in s["cards"]]
            for c, h in zip(s["cards"], hs):
                txt = " ".join(str(x) for x in c if x)
                if len(txt) > MAX_ITEM:
                    warn.append(f"{tag} p{i}: 卡片 {len(txt)} 字（> {MAX_ITEM}）——拆卡或写进备注")
            if t == "fig_text" and sum(hs) + 0.10 * (len(hs) - 1) > BODY_H:
                warn.append(f"{tag} p{i}: {len(hs)} 张卡放不下")
        if t == "fig_steps":
            tw = cw_of(s.get("img_w", 4.35))
            for st in s["steps"]:
                st = list(st) + [""]
                if len(st[1]) > MAX_STEP:
                    warn.append(f"{tag} p{i}: 步骤“{st[0]}”{len(st[1])} 字（> {MAX_STEP}）")
            hs = [_h_for(_lines_for([st[0], "", (list(st) + [""])[1]], tw)) for st in s["steps"]]
            if sum(hs) + 0.10 * (len(hs) - 1) > BODY_H:
                warn.append(f"{tag} p{i}: {len(hs)} 张步骤卡放不下")
        if t == "text":
            for it in s.get("items", []):
                it = list(it) + ["", ""]
                if len(it[2]) > MAX_ITEM:
                    warn.append(f"{tag} p{i}: 条目“{it[0]}”说明 {len(it[2])} 字（> {MAX_ITEM}）")
        if t == "end" and s.get("cols"):
            for head, bullets in s["cols"]:
                for b in bullets:
                    if len(b) > 30:
                        warn.append(f"{tag} p{i}: 小结条目“{b[:12]}…”{len(b)} 字（> 30）")
    return warn


# ---------------------------------------------------------------- 页型
def _cards(sl, x, y0, w, cards, key_last=True, max_h=None):
    hs = [_h_for(_lines_for(c, w)) for c in cards]
    # 卡片总高超过可支配高度时，按字数压缩高度（把间距交给 _stack 去分配）
    if max_h and sum(hs) > max_h:
        k = max_h / sum(hs)
        hs = [max(0.50, h * k) for h in hs]
    ys, _ = _stack(hs)
    for k, c in enumerate(cards):
        c = list(c) + ["", ""]
        K.card(sl, x, ys[k], w, hs[k], c[0], c[1], c[2],
               key=bool(k == len(cards) - 1 and key_last))


def _points(sl, x, y, w, h, items, size=BODY, gap=8):
    K.rich(sl, x, y, w, h, [tuple(i) if isinstance(i, (list, tuple)) else ("", i)
                            for i in items], size=size, gap=gap)


def build(spec, out_path):
    base = os.path.dirname(os.path.abspath(spec["_path"]))
    cite_default = spec.get("cite", "")
    slides = spec["slides"]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)

    def p(f):
        return os.path.join(base, f)

    for i, s in enumerate(slides, 1):
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        t = s["type"]

        if t == "cover":
            K.cover_slide(sl, s, i)
            if s.get("cite"):
                K.cite(sl, s["cite"])

        elif t == "toc":
            K.toc_slide(sl, spec.get("nav", {}), s["entries"], None,
                        s.get("title", "叙事线"), s.get("subtitle", ""))
            K.pageno(sl, i)

        elif t == "section":
            K.section_slide(sl, s, i)

        elif t == "author":
            K.head(sl, s.get("title", "作者与课题组"), s.get("core", ""))
            K.rect(sl, M, Y_TOP, 4.05, BODY_H, K.CARD, K.EDGE)
            K.textbox(sl, M + 0.18, Y_TOP + 0.16, 3.65, 0.24, "通讯作者", K.T_PAGE, True, GRAY)
            K.textbox(sl, M + 0.18, Y_TOP + 0.44, 3.65, 0.72, s.get("names", ""), 18, True,
                      NAVY, spacing=1.1)
            K.textbox(sl, M + 0.18, Y_TOP + 1.18, 3.65, 0.80, s.get("affil", ""), K.T_PAGE,
                      False, GRAY, spacing=1.15)
            _points(sl, M + 0.18, Y_TOP + 2.00, 3.65, 1.30,
                    [("• ", r) for r in s.get("roles", [])],
                    size=K.T_PAGE, gap=3)
            _points(sl, 4.75, Y_TOP, W - M - 4.75, BODY_H,
                    s.get("points") or s.get("blocks") or [], size=BODY, gap=10)
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        elif t == "fig_text":
            K.head(sl, s["title"], s["core"])
            iw = s.get("img_w", 4.5)
            cap = s.get("caption")
            # 图注占的高度按宽度估算：窄图上的长图注会折成两行，否则会顶到结论条
            cap_h = max(0.30, K.est_lines(cap or "", min(max(iw, 4.30), CW), K.T_NOTE) * 0.20 + 0.10)
            K.place_image(sl, p(s["img"]), (M, Y_TOP, iw, BODY_H - (cap_h if cap else 0)), cap)
            tx = M + iw + 0.38
            tw = W - M - tx
            if s.get("cards"):
                _cards(sl, tx, Y_TOP, tw, s["cards"], s.get("key", True),
                       max_h=BODY_H - 0.10)
            else:
                _points(sl, tx, Y_TOP, tw, BODY_H, s.get("points") or s.get("blocks") or [])
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        elif t == "fig_steps":
            K.head(sl, s["title"], s["core"])
            iw = s.get("img_w", 4.35)
            cap = s.get("caption")
            cap_h = max(0.30, K.est_lines(cap or "", min(max(iw, 4.30), CW), K.T_NOTE) * 0.20 + 0.10)
            K.place_image(sl, p(s["img"]), (M, Y_TOP, iw, BODY_H - (cap_h if cap else 0)), cap)
            tx = M + iw + 0.38
            tw = W - M - tx
            steps = [list(st) + [""] for st in s["steps"]]
            hs = [_h_for(_lines_for([st[0], "", st[1]], tw)) for st in steps]
            ys, _ = _stack(hs, gap_max=0.24)
            for k, st in enumerate(steps):
                K.step_card(sl, tx, ys[k], tw, hs[k], k, st[0], st[1],
                            key=bool(k == len(steps) - 1 and s.get("key_step", True)))
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        elif t == "fig_wide":
            K.head(sl, s["title"], s["core"])
            path = p(s["img"])
            iw_px, ih_px = Image.open(path).size
            cap = s.get("caption")
            cards = s.get("cards") or []
            band = 0.74 if cards else 0.0
            cap_h = max(0.32, K.est_lines(cap or "", CW, K.T_NOTE) * 0.20 + 0.10)
            h_max = Y_BOT - Y_TOP - (cap_h if cap else 0) - 0.06 - band
            h0 = min(s.get("img_h", 1.95), CW * ih_px / iw_px, h_max)
            w0 = h0 * iw_px / ih_px
            _, bottom = K.place_image(sl, path, (M + (CW - w0) / 2, Y_TOP, w0, h0), cap)
            if cards:
                n = len(cards)
                gap = 0.20
                cw = (CW - gap * (n - 1)) / n
                y = bottom + 0.14
                ch = min(max(_h_for(_lines_for(c, cw)) for c in cards), Y_BOT - y)
                for k, c in enumerate(cards):
                    c = list(c) + ["", ""]
                    K.card(sl, M + k * (cw + gap), y, cw, ch, c[0], c[1], c[2],
                           key=bool(k == n - 1 and s.get("key", True)))
            else:
                _points(sl, M, bottom + 0.14, CW, Y_BOT - bottom - 0.14,
                        s.get("points") or s.get("blocks") or [], size=GRID_BODY, gap=5)
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        elif t == "text":
            K.head(sl, s["title"], s.get("core", ""))
            if s.get("items"):
                # 紧凑四栏（可选）：字号按最大内容自适应，四种字号都在阶梯里
                items = [list(it) + ["", ""] for it in s["items"]]
                n = len(items)
                gap = 0.28
                cw = (CW - gap * (n - 1)) / n
                mode = s.get("grid", "ref")
                sizes = None
                if mode == "compact":
                    # "fill": 尽量用大字号把内容区撑满（无图页面不留大片空白）
                    cands = ((17, 13), (16, 13), (15, 12.5), (15, 12), (14, 12), (13.5, 12),
                             (13, 12), (12.5, 12), (12, 12))
                    if s.get("fill"):
                        for hs, bs in cands:
                            need = max(K.est_lines(it[0], cw, hs) * hs * 1.20 / 72.0
                                       + (K.est_lines(it[1], cw, bs) * bs * 1.20 / 72.0
                                          if it[1] else 0)
                                       + K.est_lines(it[2], cw, bs) * bs * 1.42 / 73.0 + 0.34
                                       for it in items)
                            if need <= BODY_H - 0.14:
                                sizes = (hs, bs)
                                break
                    else:
                        for hs, bs in ((15, 12), (14, 12), (13.5, 12), (13, 12), (12.5, 12),
                                       (12, 12)):
                            need = max(K.est_lines(it[0], cw, hs) * hs * 1.20 / 72.0
                                       + (K.est_lines(it[1], cw, 12) * 12 * 1.20 / 72.0
                                          if it[1] else 0)
                                       + K.est_lines(it[2], cw, bs) * bs * 1.32 / 73.0 + 0.30
                                       for it in items)
                            if need <= BODY_H - 0.14:
                                sizes = (hs, bs)
                                break
                    if sizes is None:
                        sizes = (12, 12)
                for k, it in enumerate(items):
                    x = M + k * (cw + gap)
                    K.hline(sl, x, Y_TOP + 0.10, cw, NAVY, 2.5)
                    if sizes:
                        hs, bs = sizes
                        y = Y_TOP + 0.24
                        h1 = K.est_lines(it[0], cw, hs) * hs * 1.20 / 72.0 + 0.06
                        K.textbox(sl, x, y, cw, h1, it[0], hs, True, INK)
                        y += h1
                        if it[1]:
                            h2 = K.est_lines(it[1], cw, bs) * bs * 1.20 / 72.0 + 0.04
                            K.textbox(sl, x, y, cw, h2, it[1], bs, True, NAVY)
                            y += h2
                        K.textbox(sl, x, y, cw, Y_TOP + BODY_H - y, it[2], bs, False, INK,
                                  spacing=1.38 if s.get("fill") else 1.32)
                    else:
                        K.textbox(sl, x, Y_TOP + 0.24, cw, 0.30, it[0], 15, True, INK)
                        if it[1]:
                            K.textbox(sl, x, Y_TOP + 0.62, cw, 0.26, it[1], K.T_PAGE, True, NAVY)
                        K.textbox(sl, x, Y_TOP + (0.94 if it[1] else 0.62), cw,
                                  BODY_H - (0.94 if it[1] else 0.62), it[2], GRID_BODY, False, INK,
                                  spacing=1.25)
            else:
                cols = s.get("cols", 2)
                gap = 0.55
                cw = (CW - gap * (cols - 1)) / cols
                pts = s.get("points") or s.get("blocks") or []
                per = -(-len(pts) // cols)
                for c in range(cols):
                    part = pts[c * per:(c + 1) * per]
                    if part:
                        _points(sl, M + c * (cw + gap), Y_TOP, cw, BODY_H, part)
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        elif t == "timeline":
            # 研究脉络图：一条横向时间轴 + N 个阶段，每阶段给年份、名目、2–3 条关键工作
            K.head(sl, s["title"], s.get("core", ""))
            phases = s["phases"]
            n = len(phases)
            gap = 0.16 if n <= 5 else 0.10
            cw = (CW - gap * (n - 1)) / n
            y_axis = 1.97
            K.hline(sl, M, y_axis, CW, K.RULE, 2.25)
            for k, ph in enumerate(phases):
                x = M + k * (cw + gap)
                cx = x + cw / 2
                K.textbox(sl, x, y_axis - 0.40, cw, 0.28, ph["year"], 13.5, True, NAVY,
                          K.PP_ALIGN.CENTER)
                dot = 0.15
                oval = sl.shapes.add_shape(K.MSO_SHAPE.OVAL, Inches(cx - dot / 2),
                                           Inches(y_axis - dot / 2 + 0.012), Inches(dot), Inches(dot))
                oval.fill.solid()
                oval.fill.fore_color.rgb = NAVY
                oval.line.fill.background()
                oval.shadow.inherit = False
                K.textbox(sl, x, y_axis + 0.20, cw, 0.28, ph["name"], 13, True, K.INK,
                          K.PP_ALIGN.CENTER)
                K.textbox(sl, x, y_axis + 0.56, cw, Y_BOT - y_axis - 0.56,
                          "\n".join("· " + it for it in ph["items"]), 12, False, K.GRAY,
                          spacing=1.32)
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        elif t == "ladder":
            # 叙事线逻辑图：N 层竖向递进，层间用箭头，最后一条结论条
            K.head(sl, s["title"], s.get("core", ""))
            rows = s["rows"]
            n = len(rows)
            avail = Y_BOT - Y_TOP - 0.04
            vgap = 0.26 if n <= 4 else 0.18
            rh = min(0.74, (avail - vgap * (n - 1)) / n)
            block = rh * n + vgap * (n - 1)
            y = Y_TOP + max(0.0, (avail - block) / 2)
            chip = 0.52
            for k, (num, name, claim) in enumerate(rows):
                K.rect(sl, M, y, chip, rh, K.CARD if k < n - 1 else K.CARD_KEY,
                       K.EDGE if k < n - 1 else K.EDGE_KEY)
                K.textbox(sl, M, y, chip, rh, num, 14.5, True, NAVY,
                          K.PP_ALIGN.CENTER, K.MSO_ANCHOR.MIDDLE)
                tw = CW - chip - 0.26
                K.textbox(sl, M + chip + 0.18, y, 1.36, rh, name, 15, True,
                          K.INK if k < n - 1 else K.RED, K.PP_ALIGN.LEFT,
                          K.MSO_ANCHOR.MIDDLE)
                K.textbox(sl, M + chip + 1.62, y, tw - 1.44, rh, claim, 13, False, K.GRAY,
                          K.PP_ALIGN.LEFT, K.MSO_ANCHOR.MIDDLE)
                if k < n - 1:
                    K.textbox(sl, M + chip / 2 - 0.12, y + rh, 0.24, vgap,
                              "↓", 13, True, NAVY, K.PP_ALIGN.CENTER, K.MSO_ANCHOR.MIDDLE)
                y += rh + vgap
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        elif t == "end":
            K.head(sl, s.get("title", "小结"), s.get("core", ""))
            cols = s.get("cols")
            if cols:
                n = len(cols)
                gap = 0.28
                cw = (CW - gap * (n - 1)) / n
                for k, (head, bullets) in enumerate(cols):
                    x = M + k * (cw + gap)
                    K.rect(sl, x, Y_TOP, cw, 0.50, K.CARD, K.EDGE)
                    K.textbox(sl, x + 0.12, Y_TOP, cw - 0.24, 0.50,
                              f"{k + 1:02d}　{head}", 14.5, True, NAVY,
                              K.PP_ALIGN.CENTER, K.MSO_ANCHOR.MIDDLE)
                    tb = sl.shapes.add_textbox(Inches(x + 0.12), Inches(Y_TOP + 0.66),
                                               Inches(cw - 0.24), Inches(2.36))
                    tf = tb.text_frame
                    tf.word_wrap = True
                    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                    # 条目字号：全部能单行 → 13 pt；否则整栏降到能放下的最大字号
                    bsize = BODY
                    for cand in (13, 12.5, 12):
                        lines = sum(K.est_lines("• " + b, cw - 0.24, cand) for b in bullets)
                        if all(K.est_lines("• " + b, cw - 0.24, cand) <= 1 for b in bullets) \
                                and lines * cand * 1.25 / 72.0 <= 2.30:
                            bsize = cand
                            break
                    n_b = max(1, len(bullets))
                    spacing = min(1.5, (2.30 - n_b * bsize * 1.2 / 72.0) / max(0.01, n_b * bsize / 72.0))
                    spacing = max(1.15, spacing)
                    for j, b in enumerate(bullets):
                        pp = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                        pp.line_spacing = spacing
                        r = pp.add_run()
                        r.text = "• "
                        K.set_font(r, bsize, True, NAVY)
                        r = pp.add_run()
                        r.text = b
                        K.set_font(r, bsize, False, INK)
            else:
                pts = s.get("points") or s.get("blocks") or []
                per = -(-len(pts) // 2)
                cw = (CW - 0.5) / 2
                for c in range(2):
                    part = pts[c * per:(c + 1) * per]
                    if part:
                        _points(sl, M + c * (cw + 0.5), Y_TOP, cw, BODY_H, part, gap=8)
            chain = s.get("chain") or []
            if chain:
                n = len(chain)
                arrow = 0.34
                bw = (CW - arrow * (n - 1)) / n
                y = 3.98
                for k, label in enumerate(chain):
                    x = M + k * (bw + arrow)
                    K.rect(sl, x, y, bw, 0.44, K.CARD, K.EDGE)
                    K.textbox(sl, x + 0.04, y, bw - 0.08, 0.44, label, BODY, True, NAVY,
                              K.PP_ALIGN.CENTER, K.MSO_ANCHOR.MIDDLE)
                    if k < n - 1:
                        K.textbox(sl, x + bw, y, arrow, 0.44, "→", K.T_TAKE, True, NAVY,
                                  K.PP_ALIGN.CENTER, K.MSO_ANCHOR.MIDDLE)
            K.takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
            K.cite(sl, s.get("cite", cite_default))
            K.pageno(sl, i)

        else:
            raise ValueError(f"unknown slide type {t!r} on page {i}")

        # 备注：讲解词写在这里，不占版面
        K.notes(sl, s.get("notes", ""))

    prs.save(out_path)
    return len(prs.slides._sldIdLst)


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    spec = json.load(open(sys.argv[1], encoding="utf-8-sig"))  # 兼容 PowerShell 写出的 BOM
    spec["_path"] = sys.argv[1]
    warn = check_fit(spec["slides"], "spec")
    if "--check" in sys.argv:
        print("\n".join(warn) if warn else "fit OK")
        return
    n = build(spec, sys.argv[2])
    print(f"saved {sys.argv[2]} ({n} slides)")
    if warn:
        print("WARN 可能溢出：")
        print("\n".join(warn))


if __name__ == "__main__":
    main()


