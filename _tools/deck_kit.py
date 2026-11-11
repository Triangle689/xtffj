# -*- coding: utf-8 -*-
"""deck_kit — 版式原语层（16:9，10.000 × 5.625 in）。

版式取自 `.agents/skills/paper-figures-to-deck` 的参照讲稿
「Catellani 反应的发现与机理确定」（28 页）：白底、微软雅黑、深蓝 #000098、
标题下一条 3 pt + 1.25 pt 的紫蓝双线、正文上方的蓝色论点行、页底一句结论条、
页脚 10.5 pt Arial 引文、右下 12 pt 页码。

所有坐标、字号、颜色都写在这个文件里。SKILL.md 的 Step 8 只是复述；
改版式先改这里，并同步 references/template-spec.md。

页面骨架（单位：英寸）
--------------------
    y=0.14  标题 22 pt bold #000000，左对齐，x=0.433，宽 9.134
    y=0.665 双线（3 pt #492076 + 1.25 pt #492076）
    y=0.80  论点 16 pt bold #000098，居中
    y=1.28  内容区起点
    y=4.72  内容区终点
    y=4.85  结论条 16 pt bold，居中（黑色；强调页用深蓝）
    y=5.28  引文 10.5 pt Arial（西文）+ 微软雅黑（中文），居中，期刊斜体、年份加粗
    y=5.24  页码 12 pt bold，右对齐，右边缘 9.877

Spec (JSON) 见 references/spec-example.json。

    {"cite": "...",
     "slides": [
       {"type": "cover",  "kicker": "...", "title": "...", "subtitle": "...",
                          "author": "...", "affil": "...", "meta": "..."},
       {"type": "toc",    "entries": [["现象与问题", 4, "从…到…"], ...]},
       {"type": "section","num": "01", "title": "...", "sub": "..."},
       {"type": "author", "names": "...", "affil": "...", "roles": [...],
                          "core": "...", "blocks": [...]},
       {"type": "fig_text","title": "...", "core": "...", "img": "a.png",
                          "caption": "...", "blocks": [...], "cards": [[...]]},
       {"type": "fig_steps","title": "...", "core": "...", "img": "a.png",
                          "caption": "...", "steps": [[lead, head, detail], ...]},
       {"type": "fig_wide","title": "...", "core": "...", "img": "a.png",
                          "caption": "...", "blocks": [...]},
       {"type": "text",   "title": "...", "core": "...", "blocks": [...]},
       {"type": "end",    "title": "小结", "core": "...", "blocks": [...],
                          "chain": ["意外产物", "ANP 假说", "..."]}
     ]}
"""
import json
import os
import sys

from PIL import Image
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

# ------------------------------------------------------------------ 字体 / 配色
FONT = "微软雅黑"           # 中日韩统一用微软雅黑，latin / ea / cs 三处都设
LATIN = "Arial"             # 仅引文、图注这类“文献体”西文

NAVY = RGBColor(0x00, 0x00, 0x98)      # 标题蓝：论点、章节号、强调结论
RULE = RGBColor(0x49, 0x20, 0x76)      # 标题下双线的紫蓝
INK = RGBColor(0x00, 0x00, 0x00)       # 正文黑
GRAY = RGBColor(0x59, 0x59, 0x59)      # 次级灰：说明、章节副标题
RED = RGBColor(0xC0, 0x00, 0x00)       # 强调红：关键结论、反例
GREEN = RGBColor(0x00, 0x66, 0x00)     # 点缀绿：被证实的现象
CARD = RGBColor(0xE5, 0xF0, 0xFF)      # 浅蓝卡片
CARD_KEY = RGBColor(0xFB, 0xEA, 0xEA)  # 浅红卡片（关键项）
EDGE = RGBColor(0xE8, 0xE8, 0xE8)      # 卡片描边
EDGE_KEY = RGBColor(0xE8, 0xC8, 0xC8)  # 关键卡片描边
CONN = RGBColor(0xB8, 0xC4, 0xD8)      # 流程图细连线

# 兼容旧名（旧脚本里 import 过）
DARK = NAVY
LIGHT = EDGE

# ------------------------------------------------------------------ 版面栅格
W, H = 10.0, 5.625
M = 0.433
CW = W - 2 * M                 # 9.134

Y_TITLE = 0.14
Y_RULE = 0.665
Y_CLAIM = 0.80
Y_TOP = 1.30                   # 内容区
Y_BOT = 4.72
Y_TAKE = 4.85
Y_CITE = 5.28
Y_PAGE = 5.24
RIGHT = W - M                  # 9.567

# 字号阶梯（pt）—— 低于 12 只允许“文献体”10.5，见 set_font 断言
T_COVER = 40
T_COVER_KICK = 20
T_COVER_EN = 14
T_COVER_AUTHOR = 24
T_COVER_AFFIL = 20
T_COVER_META = 16
T_SEC_NUM = 96
T_SEC_TITLE = 36
T_SEC_SUB = 16
T_TITLE = 22
T_CLAIM = 16
T_BODY = 13
T_BODY_TIGHT = 12.5
T_CARD = 13
T_TAKE = 16
T_CITE = 10.5
T_PAGE = 12
T_NOTE = 10.5                  # 图注 / 引文这档“文献体”

A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


# ------------------------------------------------------------------ 基础件
NBSP = "\u00a0"


def pretty(text):
    """排版：把 `：` `=` `→` 两侧的 ASCII 空格换成不换行的窄空格（U+00A0）。

    PowerPoint 在空格处断行，卡片逐字换行时会出现“、”“：”跑到行首的孤字行；
    换成 NBSP 后“标签：内容”“式 = 结构”整段不会被拆开。
    """
    import re
    s = str(text)
    s = re.sub(r"\s*([：=→])\s*", NBSP + r"\1" + NBSP, s)
    return s


def set_font(run, size, bold=False, color=INK, latin=FONT, italic=False):
    """字号断言：正文 ≥ 12 pt；只有 10.5 pt 的文献体（引文/图注）例外。"""
    assert size >= 12 or abs(size - T_NOTE) < 0.01, f"font {size} pt 不在字号阶梯里"
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = latin
    rPr = run._r.get_or_add_rPr()
    for tag in ("ea", "cs"):           # 只设 latin 会让中文回退到别的字体
        el = rPr.find(A + tag)
        if el is None:
            el = etree.SubElement(rPr, A + tag)
        el.set("typeface", FONT)


def textbox(slide, l, t, w, h, text, size, bold=False, color=INK, align=PP_ALIGN.LEFT,
            anchor=MSO_ANCHOR.TOP, spacing=1.0, latin=FONT, name=None):
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, line in enumerate(text.split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        r = p.add_run()
        r.text = line
        set_font(r, size, bold, color, latin)
    if name:
        tb.name = name
    return tb


def rect(slide, l, t, w, h, fill=None, line=None, lw=0.75):
    s = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(l), Inches(t), Inches(w), Inches(h))
    if fill is None:
        s.fill.background()
    else:
        s.fill.solid()
        s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(lw)
    s.shadow.inherit = False
    return s


def hline(slide, l, t, w, color, pt):
    """一条实心细线：用高度 = pt 的矩形画，避免 connector 在旧版 PPT 里跑位。"""
    return rect(slide, l, t, w, pt / 72.0, color)


def rule(slide, y=Y_RULE):
    """标题下的双线：3 pt 粗线 + 1.25 pt 细线，色 #492076。"""
    hline(slide, M, y, CW, RULE, 3.0)
    hline(slide, M, y + 0.0477, CW, RULE, 1.25)


def head(slide, title, claim=None):
    """内容页页眉：22 pt 标题 + 双线 + 可选 16 pt 论点。"""
    textbox(slide, M, Y_TITLE, CW, 0.44, title, T_TITLE, True, INK)
    rule(slide)
    if claim:
        textbox(slide, M + 0.55, Y_CLAIM, CW - 1.10, 0.34, claim, T_CLAIM, True, NAVY,
                PP_ALIGN.CENTER)


def takeaway(slide, text, navy=False):
    """页底结论条：一句话说清本页结论，16 pt bold 居中。"""
    if text:
        textbox(slide, M, Y_TAKE, CW, 0.32, text, T_TAKE, True, NAVY if navy else INK,
                PP_ALIGN.CENTER)


def pageno(slide, i):
    textbox(slide, W - M - 0.63, Y_PAGE, 0.63, 0.28, str(i), T_PAGE, True, INK,
            PP_ALIGN.RIGHT)


def notes(slide, text):
    """写进 PowerPoint 备注（演讲者视图）：展开的推理、数据出处、口径说明都放这里。"""
    if not text:
        return None
    tf = slide.notes_slide.notes_text_frame
    tf.text = ""
    for i, line in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = PP_ALIGN.LEFT
        p.line_spacing = 1.2
        r = p.add_run()
        r.text = line
        set_font(r, 12, False, INK)
    return tf


_TOK = None


def _runs(paragraph, text, size, color=INK, latin=LATIN):
    """把 `*斜体*` / `**加粗**` 拆成 run；引文与图注共用。"""
    global _TOK
    if _TOK is None:
        import re
        _TOK = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*)")
    for part in _TOK.split(text or ""):
        if not part:
            continue
        bold = part.startswith("**")
        ital = part.startswith("*") and not bold
        r = paragraph.add_run()
        r.text = part.strip("*")
        set_font(r, size, bold, color, latin, ital)


def cite(slide, text, y=Y_CITE):
    """页脚引文：10.5 pt，Arial 西文 + 微软雅黑中文；*期刊*/**年份** 走斜体/加粗。"""
    tb = slide.shapes.add_textbox(Inches(M), Inches(y), Inches(CW), Inches(0.30))
    tb.name = "cite"
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    p.line_spacing = 1.0
    _runs(p, text, T_CITE)
    return tb


def caption(slide, text, left, top, width):
    """图注：图下 0.03 in，10.5 pt 灰，居中，宽度随图（过窄时至少 4.3 in）。"""
    tb = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(0.26))
    tb.name = "caption"
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    _runs(p, text, T_NOTE, GRAY)
    return tb


def est_lines(text, width_in, size):
    """估算行数：中文按 1 em、西文按 0.55 em。"""
    em = size / 72.0
    cap = max(6, int(width_in / em))
    wsum = 0.0
    for seg in str(text).split("\n"):
        wsum = max(wsum, sum(1.0 if ord(ch) > 0x2E80 else 0.55 for ch in seg))
    return max(1, -(-int(wsum * 100) // int(cap * 100)))


def card_h(text, width, size=T_CARD, pad=0.30):
    """短句卡片的高度：一行 0.50 in、两行 0.70 in，最多 1.10 in。"""
    n = est_lines(text, width - 0.20, size)
    return min(1.10, max(0.50, pad + n * size * 1.10 / 72.0))


def fit_image(slide, path, box):
    """等比缩放 + 居中，绝不拉伸。"""
    l, t, w, h = box
    iw, ih = Image.open(path).size
    k = min(w / iw, h / ih)
    nw, nh = iw * k, ih * k
    return slide.shapes.add_picture(path, Inches(l + (w - nw) / 2), Inches(t + (h - nh) / 2),
                                    Inches(nw), Inches(nh))


def place_image(slide, path, box, cap=None):
    """图 + （必须的）图注；返回 (图片, 内容区底部)。"""
    pic = fit_image(slide, path, box)
    left, width = pic.left / 914400, pic.width / 914400
    bottom = (pic.top + pic.height) / 914400
    if cap:
        cw = min(max(width, 4.30), CW)
        cx = min(max(left + width / 2 - cw / 2, M), M + CW - cw)
        caption(slide, cap, cx, bottom + 0.03, cw)
        bottom += 0.30
    return pic, bottom


# ------------------------------------------------------------------ 卡片
def card(slide, l, t, w, h, lead, head_text="", detail="", key=False, size=T_CARD,
         align=PP_ALIGN.LEFT, pad=0.10):
    """浅蓝卡片：深蓝引导词 + 黑色粗体主张 + 灰色释文；关键项用浅红卡片。"""
    rect(slide, l, t, w, h, CARD_KEY if key else CARD, EDGE_KEY if key else EDGE)
    tb = slide.shapes.add_textbox(Inches(l + pad), Inches(t + 0.03), Inches(w - 2 * pad),
                                  Inches(h - 0.06))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = 1.1
    if lead:
        r = p.add_run()
        sep = "" if lead[-1] in "：:·，、 " else (" " if head_text.startswith("=") else "：")
        r.text = lead + sep
        set_font(r, size, True, NAVY)
    if head_text:
        r = p.add_run()
        r.text = head_text
        set_font(r, size, True, RED if key else INK)
    if detail:
        r = p.add_run()
        r.text = ("\n" if head_text else "") + detail
        set_font(r, size, False, RED if key else GRAY)
    return tb


def step_card(slide, l, t, w, h, i, head_text, detail, key=False):
    """机理步骤卡：① 深蓝 + 粗体步骤名 + 灰释文。"""
    glyphs = "①②③④⑤⑥⑦⑧"
    lead = glyphs[i] if i < len(glyphs) else f"{i + 1}."
    rect(slide, l, t, w, h, CARD_KEY if key else CARD, EDGE_KEY if key else EDGE)
    tb = slide.shapes.add_textbox(Inches(l + 0.10), Inches(t + 0.03), Inches(w - 0.20),
                                  Inches(h - 0.06))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]
    p.line_spacing = 1.1
    r = p.add_run()
    r.text = lead + " "
    set_font(r, T_CARD, True, NAVY)
    r = p.add_run()
    r.text = head_text
    set_font(r, T_CARD, True, INK)
    if detail:
        r = p.add_run()
        r.text = "\n" + detail
        set_font(r, T_CARD - 0.5, False, GRAY)
    return tb


# ------------------------------------------------------------------ 段落
def rich(slide, l, t, w, h, blocks, size=T_BODY, gap=6, spacing=1.15, color=INK):
    """(lead, body) 段落组；lead 深蓝粗体，body 黑色。也接受纯字符串条目。"""
    tb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.TOP
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    first = True
    for item in blocks:
        lead, body = item if isinstance(item, (list, tuple)) else ("", item)
        if isinstance(body, (list, tuple)):
            body = " ".join(str(x) for x in body)
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap)
        p.line_spacing = spacing
        p.alignment = PP_ALIGN.LEFT
        if lead:
            r = p.add_run()
            r.text = lead
            set_font(r, size, True, NAVY)
        for j, line in enumerate(str(body).split("\n")):
            r = p.add_run()
            r.text = ("\n" if (j and not lead) else "") + line
            set_font(r, size, False, color)
    return tb


def bullets(slide, l, t, w, h, items, size=T_BODY, color=INK, gap=8):
    """圆点列表（只在“小结/延伸”这类允许列表的页用）。"""
    return rich(slide, l, t, w, h, [("· ", it) for it in items], size=size, gap=gap,
                color=color)


# ------------------------------------------------------------------ 页型
def cover_slide(slide, s, i=1):
    textbox(slide, 2.0, 0.30, 6.0, 0.42, s.get("kicker", ""), T_COVER_KICK, True, INK,
            PP_ALIGN.CENTER)
    rule(slide)
    textbox(slide, 0.20, 1.22, 9.60, 0.88, s.get("title", ""), T_COVER, True, NAVY,
            PP_ALIGN.CENTER)
    textbox(slide, 0.40, 2.12, 9.20, 0.34, s.get("subtitle", ""), T_COVER_EN, False, INK,
            PP_ALIGN.CENTER)
    hline(slide, 0.47, 2.72, 9.05, INK, 1.5)
    textbox(slide, 3.0, 3.05, 4.0, 0.46, s.get("author", ""), T_COVER_AUTHOR, True, NAVY,
            PP_ALIGN.CENTER)
    textbox(slide, 3.0, 3.82, 4.0, 0.78, s.get("affil", ""), T_COVER_AFFIL, True, INK,
            PP_ALIGN.CENTER, spacing=1.05)
    textbox(slide, 3.0, 4.95, 4.0, 0.40, s.get("meta", ""), T_COVER_META, True, INK,
            PP_ALIGN.CENTER)
    pageno(slide, i)


def toc_slide(slide, meta, entries, accent=None, title="叙事线", subtitle=""):
    head(slide, title, subtitle or None)
    n = len(entries)
    per = (n + 1) // 2
    sw = (CW - 0.55) / 2
    for c in range(2):
        part = entries[c * per:(c + 1) * per]
        x = M + c * (sw + 0.55)
        y = 1.34
        for k, e in enumerate(part):
            name, page = e[0], e[1]
            desc = e[2] if len(e) > 2 else ""
            num = c * per + k + 1
            textbox(slide, x, y + 0.02, 0.40, 0.28, f"{num}", T_BODY, True, NAVY)
            textbox(slide, x + 0.36, y, sw - 0.95, 0.30, name, T_BODY, True, INK)
            textbox(slide, x + sw - 0.55, y, 0.55, 0.28, f"P{page}", T_PAGE, True, GRAY,
                    PP_ALIGN.RIGHT)
            if desc:
                textbox(slide, x + 0.36, y + 0.26, sw - 0.95, 0.24, desc, T_PAGE, False, GRAY)
            y += 0.60 if desc else 0.40


def section_slide(slide, s, i=1):
    rule(slide)
    textbox(slide, 0.90, 1.90, 2.60, 1.70, s.get("num", "01"), T_SEC_NUM, True, NAVY)
    textbox(slide, 3.40, 2.15, 6.00, 0.78, s.get("title", ""), T_SEC_TITLE, True, INK)
    hline(slide, 3.50, 3.05, 5.20, NAVY, 1.5)
    textbox(slide, 3.50, 3.30, 5.40, 0.44, s.get("sub", ""), T_SEC_SUB, False, GRAY,
            spacing=1.1)
    pageno(slide, i)


def header(slide, meta, title, core, section, accent):
    """兼容旧签名：新版的页眉就是“标题 + 双线 + 论点”，不再画面包屑。"""
    head(slide, title, core)


def nav(slide, meta, section, accent):
    """新版没有面包屑：领域与章节由封面/分节页承担，来源由页脚引文承担。"""
    return None


def footer(slide, cite_text, idx=0, total=0):
    """兼容旧签名：新版页脚只有引文 + 页码。"""
    if cite_text:
        cite(slide, cite_text)
    if idx:
        pageno(slide, idx)


# ------------------------------------------------------------------ 快速装配
def build(spec, out_path):
    """简版装配器（无正文讲解能力）：cover / toc / section / author / img / two /
    img_txt / end。讲解型 deck 请用 deck_explain.py。"""
    base = os.path.dirname(os.path.abspath(spec.get("_path", ".")))
    cite_default = spec.get("cite", "")
    meta = spec.get("nav", {})
    slides = spec["slides"]
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(W), Inches(H)
    total = len(slides)
    for i, s in enumerate(slides, 1):
        sl = prs.slides.add_slide(prs.slide_layouts[6])
        t = s.get("type", "img_txt")
        p = lambda f: os.path.join(base, f)  # noqa: E731

        if t == "cover":
            cover_slide(sl, s, i)
        elif t == "toc":
            toc_slide(sl, meta, s["entries"], None, s.get("title", "叙事线"), s.get("subtitle", ""))
        elif t == "section":
            section_slide(sl, s, i)
        elif t == "author":
            head(sl, s.get("title", "作者与课题组"), s.get("core", ""))
            rect(sl, M, 1.32, 4.15, 3.36, CARD, EDGE)
            textbox(sl, M + 0.18, 1.50, 3.75, 0.24, "通讯作者", T_PAGE, True, GRAY)
            textbox(sl, M + 0.18, 1.80, 3.75, 0.70, s.get("names", ""), 18, True, NAVY,
                    spacing=1.1)
            textbox(sl, M + 0.18, 2.56, 3.75, 0.80, s.get("affil", ""), T_PAGE, False, GRAY,
                    spacing=1.15)
            rich(sl, M + 0.18, 3.40, 3.75, 1.20, [("", r) for r in s.get("roles", [])],
                 size=T_PAGE, gap=4)
            rich(sl, 4.90, 1.34, W - M - 4.90, 3.34,
                 [tuple(b) for b in s.get("blocks", s.get("bullets", []))], size=T_BODY, gap=8)
        elif t == "end":
            head(sl, s.get("title", "小结与延伸"), s.get("core", ""))
            blocks = s.get("blocks", [])
            per = (len(blocks) + 1) // 2
            cw = (CW - 0.5) / 2
            for c in range(2):
                part = blocks[c * per:(c + 1) * per]
                if part:
                    rich(sl, M + c * (cw + 0.5), 1.34, cw, 3.34, part, size=T_BODY, gap=8)
        elif t == "img":
            head(sl, s["title"], s.get("core", ""))
            place_image(sl, p(s["img"]), (M, Y_TOP, CW, Y_BOT - Y_TOP), s.get("caption"))
        elif t == "two":
            head(sl, s["title"], s.get("core", ""))
            a1 = Image.open(p(s["imgs"][0])).size[0] / Image.open(p(s["imgs"][0])).size[1]
            a2 = Image.open(p(s["imgs"][1])).size[0] / Image.open(p(s["imgs"][1])).size[1]
            if min(a1, a2) >= 2.0:
                place_image(sl, p(s["imgs"][0]), (M, Y_TOP, CW, 1.55), s.get("caption"))
                place_image(sl, p(s["imgs"][1]), (M, 3.05, CW, 1.55), s.get("caption2"))
            else:
                half = (CW - 0.30) / 2
                place_image(sl, p(s["imgs"][0]), (M, Y_TOP, half, Y_BOT - Y_TOP), s.get("caption"))
                place_image(sl, p(s["imgs"][1]), (M + half + 0.30, Y_TOP, half, Y_BOT - Y_TOP),
                            s.get("caption2"))
        else:                                        # img_txt
            head(sl, s["title"], s.get("core", ""))
            iw = s.get("img_w", 4.55)
            place_image(sl, p(s["img"]), (M, Y_TOP, iw, 3.30),
                        s.get("caption") or s.get("cap"))
            tx = M + iw + 0.38
            tw = W - M - tx
            cards = s.get("cards")
            if cards:
                hs = [card_h(" ".join(str(z) for z in c if z), tw) for c in cards]
                total = sum(hs)
                gap = min(0.34, (Y_BOT - Y_TOP - total) / max(1, len(cards) - 1))
                y = Y_TOP + max(0.0, (Y_BOT - Y_TOP - total - gap * (len(cards) - 1)) / 2)
                for k, c in enumerate(cards):
                    lead, hd, det = (list(c) + ["", ""])[:3]
                    card(sl, tx, y, tw, hs[k], lead, hd, det,
                         key=bool(k == len(cards) - 1 and s.get("key", True)))
                    y += hs[k] + gap
            else:
                rich(sl, tx, Y_TOP, tw, Y_BOT - Y_TOP, s.get("points", s.get("blocks", [])),
                     size=T_BODY, gap=6)
        takeaway(sl, s.get("takeaway", ""), s.get("navy", False))
        if t not in ("cover", "section"):
            cite(sl, s.get("cite", cite_default))
            pageno(sl, i)
        else:
            cite(sl, s.get("cite", "")) if s.get("cite") else None
        notes(sl, s.get("notes", ""))
    prs.save(out_path)
    return len(prs.slides._sldIdLst)


if __name__ == "__main__":
    spec = json.load(open(sys.argv[1], encoding="utf-8-sig"))  # 兼容 PowerShell 写出的 BOM
    spec["_path"] = sys.argv[1]
    n = build(spec, sys.argv[2])
    print(f"saved {sys.argv[2]} ({n} slides)")

