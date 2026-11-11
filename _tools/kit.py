# -*- coding: utf-8 -*-
"""Build the deck with a *local copy* of the paper-figures-to-deck engine.

The skill's originals stay untouched in
  D:\\A清华\\文献\\.agents\\skills\\paper-figures-to-deck\\scripts
_tools/deck_kit.py and _tools/deck_explain.py are copies with the fixes noted in
BUGFIX 标记 (caption height, compact text grid, NBSP 换行, end-page line spacing).
"""
import os
import sys
from difflib import SequenceMatcher

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import deck_kit as K           # noqa: E402  (local copy)
import deck_explain as X       # noqa: E402  (local copy)

T_NOTE = K.T_NOTE


def _patch_author_fit():
    """Trnka/Choplin 这类长西文名在 18 pt 里会顶到卡片边。

    按估算行数缩字号（18 → 15 → 13.5 → 12），字号仍在阶梯内。
    """
    orig = K.textbox

    def author_name_size(name, width=3.65):
        for size in (18, 15, 13.5, 12):
            if K.est_lines(name, width, size) <= 2:
                return size
        return 12

    def patched_head(sl, s, i):
        pass

    # 不改引擎源码：在 build 之后统一把作者页姓名框的字号调小
    orig_build = X.build

    def build(spec, out_path):
        n = orig_build(spec, out_path)
        from pptx import Presentation
        from pptx.util import Pt
        prs = Presentation(out_path)
        for sl, s in zip(prs.slides, spec["slides"]):
            if s.get("type") != "author":
                continue
            for sh in sl.shapes:
                if not sh.has_text_frame:
                    continue
                txt = sh.text_frame.text.strip()
                if txt and txt == (s.get("names") or "").strip():
                    sz = author_name_size(txt)
                    for p in sh.text_frame.paragraphs:
                        for r in p.runs:
                            r.font.size = Pt(sz)
        prs.save(out_path)
        return n

    X.build = build


_patch_author_fit()


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def with_toc(spec):
    """重算 toc 页页码（不手写页码）。

    优先级：显式的数字页号 > 分节编号（"01"…）> 用标题相似度找内容页。
    相似度按分节页后的第一张内容页排序，取最高者；相似度太低就报错，绝不静默写到错误页。
    """
    slides = spec["slides"]
    sec_page = {}
    for i, s in enumerate(slides, 1):
        if s.get("type") == "section":
            sec_page[s.get("num")] = i
    for s in slides:
        if s.get("type") != "toc":
            continue
        for e in s["entries"]:
            ref = e[1]
            if isinstance(ref, str) and ref in sec_page:
                e[1] = sec_page[ref]
            elif isinstance(ref, str) and ref.isdigit():
                e[1] = int(ref)
        for e in s["entries"]:
            if not isinstance(e[1], str):
                continue
            scored = []
            for i, t in enumerate(slides, 1):
                if t.get("type") == "section":
                    continue
                r = similar(e[1], t.get("title", ""))
                scored.append((r, -i, i))     # 相似度相同时取靠前的页
            best_r, _, best_i = max(scored)
            assert best_r > 0.30, f"TOC entry not matched: {e[0]} / {e[1]}"
            e[1] = best_i
    return spec


def run(spec, out_path, check_only=False, spec_path=None):
    spec = with_toc(spec)
    import json
    tmp = spec_path or (out_path + ".spec.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)
    spec["_path"] = tmp
    warn = X.check_fit(spec["slides"], "spec")
    if not check_only:
        n = X.build(spec, out_path)
        print(f"saved {out_path} ({n} slides)")
    if warn:
        print("WARN 可能溢出：")
        print("\n".join(warn))
    else:
        print("fit OK")
    return spec
