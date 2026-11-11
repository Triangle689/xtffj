# -*- coding: utf-8 -*-
"""Build the static site data: site/data/site.json + site/data/rag-index.json,
and copy the 23 figures into site/assets/img/.

Source of truth:
  _tools/build_index.py   -> PAPERS / ROWS  (figure metadata)
  _tools/build_lit_xlsx.py-> ROWS           (45 papers)
Narrative text is authored here, one entry per timeline phase.
"""
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import build_index as BI  # noqa: E402
import build_lit_xlsx as LX  # noqa: E402

SITE = os.path.join(BASE, "site")
DATA = os.path.join(SITE, "data")
IMGDIR = os.path.join(SITE, "assets", "img")

# ------------------------------------------------------------------ 阶段叙事
PHASES = [
    dict(id="p1", no="01", period="1955–1978", name="现象 → 机理之争",
         tagline="工业界先看到现象，学术界后给出解释",
         lede=("三家工业实验室各自在自己的装置里看到同一个现象：碳碳双键被切开又重新拼起来。"
               "它们一个叫歧化，一个叫开环聚合，没人意识到是同一件事。"
               "Goodyear 的 Calderon 用均匀催化体系把它从「工业怪现象」变成了「可研究的反应」，"
               "并给出了第一份定量证据——产物分布符合纯随机组合。"
               "随后 Chauvin 在没有直接证据的情况下提出金属亚烷基机理，"
               "Grubbs 与 Katz 两个课题组用同位素实验互相检验。"),
         points=[
             dict(h="命名", t="Calderon 1967 提出 metathesis，并用 W/Al 均匀体系证明烷叉基互换。"),
             dict(h="定量", t="2-戊烯与 6-十二烯的产物分布与理想随机组合完全重合，排除链增长。"),
             dict(h="假设", t="Chauvin 1971 提出「金属亚烷基 + 金属杂环丁烷」，当时该物种尚无法分离。"),
             dict(h="互检", t="Grubbs 1972/1975 与 Katz 1975 用同位素标记给出两条独立证据链。"),
         ],
         insight="现象先于概念，假设先于证据。",
         papers=[1, 2, 3, 4, 5, 6, 7, 8, 9, 25],
         figures=["P2_F2", "P1_F1", "P3_F8", "P1_F4", "P1_F2", "P1_F3"]),
    dict(id="p2", no="02", period="1980–1996", name="结构确立",
         tagline="把假说里的物种，做成一个可以设计的分子",
         lede=("Schrock 组用了十年，把「金属亚烷基」从纸面上的符号变成了可以分离、可以按配体设计的分子。"
               "1980 年的钨氧代亚烷基第一次给出明确结构，1990 年 Mo 亚烷基系列把结构-活性关系建立起来。"
               "与此同时 Grubbs 组把同样的思路搬到钌上：既然 Mo 的强亲氧性让它在空气里就失活，"
               "那就换一个不亲氧的金属——用「不活泼」去换「耐受」。"),
         points=[
             dict(h="1980", t="钨氧代亚烷基配合物，第一次有明确结构的复分解催化剂。"),
             dict(h="1988–1990", t="W/Mo 亚烷基系列系统合成，1988 年 JACS 与 1990 年 JACS 两篇。"),
             dict(h="1995", t="Grubbs Ⅰ 代：PCy₃ 版 RuCl₂(=CHPh)(PCy₃)₂，活性与耐受兼得。"),
             dict(h="1996", t="配体效应系统研究，解释了Ⅰ 代为什么是这个结构。"),
         ],
         insight="结构先于工具：没有可设计的分子，就没有后来的一切。",
         papers=[10, 11, 12, 13, 14, 15, 26],
         figures=["P7_F1", "P7_F2", "P4_F2Achiral", "P4_F2Chiral"]),
    dict(id="p3", no="03", period="1995–2004", name="工具化",
         tagline="从「能反应」到「人人都能用」",
         lede=("有了可设计的分子，接下来是把它变成实验室里的常规试剂。"
               "1999 年 Grubbs 把 Ⅰ 代的一个 PCy₃ 换成 NHC（H₂IMes），Ⅱ 代诞生：给电子更强、引发更快、"
               "催化量降下来。同一年 Hoveyda 型把苄叉改成异丙氧基苄叉，让催化剂能空气稳定、可回收。"
               "2003 年的三卷本手册把这一代知识固化下来。"),
         points=[
             dict(h="1999", t="Ⅱ 代：一个 PCy₃ 换成 H₂IMes，NHC 强 σ 给电子 + 大位阻。"),
             dict(h="1999–2000", t="Hoveyda 型：O→Ru 螯合「锁住」催化剂，空气稳定、可回收。"),
             dict(h="2003", t="《Handbook of Metathesis》三卷本出版，领域有了标准参考。"),
         ],
         insight="催化的进步，往往发生在配体上而不是金属上。",
         papers=[16, 17, 27],
         figures=["P5_S4", "P6_S1", "P4_F3A", "P5_S3"]),
    dict(id="p4", no="04", period="2005–2010", name="诺奖与体系化",
         tagline="三个人改写同一件事的三个层次",
         lede=("2005 年诺贝尔化学奖颁给 Chauvin、Schrock、Grubbs——分别对应机理、结构、工具三个层次。"
               "这在诺奖史上并不常见：多数奖项只奖励一个层次。"
               "随后的几年里，两本 Chem. Rev. 综述与两版手册把散落在各组的催化剂编号、活性数据、"
               "分解路径整理成体系；Hoveyda 与 Zhugralin 在 Nature 上的综述则把应用侧（药物大环、天然产物）"
               "摊开给合成化学界看。"),
         points=[
             dict(h="2005", t="诺奖：Chauvin 机理、Schrock 结构、Grubbs 工具，三者互补不可替代。"),
             dict(h="2006", t="三篇诺奖讲座：得主用第一人称讲自己那条线，包括当年的错误判断。"),
             dict(h="2007", t="Nature 综述：应用全景，含 BILN 2061 的 400 kg 工业规模。"),
             dict(h="2009–2010", t="两本 Chem. Rev. + 两版手册，把体系变成可查的教材。"),
         ],
         insight="诺奖追认的是可被写进教科书的机制，不是被工厂采用的工艺。",
         papers=[18, 19, 20, 21, 22, 23, 24, 28],
         figures=["P4_F1", "P3_F12", "P2_F3", "P2_F6", "P6_F2", "P5_F2"]),
    dict(id="p5", no="05", period="2011–2024", name="选择性时代",
         tagline="问题从「能不能反应」变成「能不能定向」",
         lede=("Ⅱ 代解决了「能不能用」，但留下一个硬伤：交叉复分解的 E/Z 选择性基本是热力学平衡值。"
               "2011 年起，螯合配体（Grubbs 组）与大位阻芳氧基（Schrock/Hoveyda 组）两条路线几乎同时"
               "把 Z-选择性做到可控，并立刻用于大环天然产物合成。"
               "另一条支线把复分解用于「拆」：让交联网络可重排（vitrimer）、让聚烯烃解聚回单体。"
               "近年还有换金属（铁催化 ROMP）与加外场（光热激活）两条新方向。"),
         points=[
             dict(h="2011", t="Z-选择性：Endo & Grubbs 螯合 Ru；Meek/Hoveyda 的 Z-选择性 CM。"),
             dict(h="2012–2013", t="改良版 Z-选择性 Ru 与「便宜版」设计，把选择性做成常规工具。"),
             dict(h="2012–2021", t="化学回收：vitrimer 可重排网络，熔环单体实现闭环解聚。"),
             dict(h="2022–2024", t="铁催化 ROMP、等离激元光热激活、立构受控 ADMET。"),
         ],
         insight="工具先于控制：先有能用的催化剂，才谈得上定向。",
         papers=[29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45],
         figures=["P4_F3B", "P4_F8", "P7_S7"]),
]

GAPS = [
    dict(id="g1", no="01", title="零原始文献",
         text=("文档 11 条全部是综述、专著或诺奖讲座，没有一篇原始研究论文。"
               "研讨文档 9 个引导问题里的第 1、2、3 问（谁发现、谁解释、谁证实）答案只在原始论文里，"
               "综述只能给结论，给不了「他当时面对什么反证」。"),
         fix="本次补入 31 篇原始论文，按阶段贯穿 1955–2024。"),
    dict(id="g2", no="02", title="断代 1995 前后",
         text=("Grubbs Ⅰ 代（1995 Angew）、Ⅱ 代（1999 Org. Lett.）、Hoveyda 型（1999 JOC / 2000 JACS）"
               "三篇都不在清单里，而它们正是文档子题 3「后周期金属催化剂」的全部内容。"),
         fix="补入第 14、15、16 篇，并配 Ⅰ 代/Ⅱ 代结构图对照。"),
    dict(id="g3", no="03", title="止于 2010",
         text=("清单最晚一篇是 2010 年。而文档子题 4 问「Z/E 选择性如何调控」——"
               "Z-选择性整个是 2011 年之后的成果；化学回收、铁催化、光热激活同样缺席。"),
         fix="补入 2011–2024 年 17 篇，含 4 篇 Nature/Nat. Chem./Nat. Catal.。"),
    dict(id="g4", no="04", title="中文文献无法核实",
         text=("《有机化学》2001/2001/2005/2010/2020 五条，Crossref 未收录，"
               "本次未能取得 DOI 与页码核对。建议按 CNKI 或纸质目录核对后再引用。"),
         fix="站内对这 5 条做了明确标注，不提供 DOI 链接。"),
]

CATALYSTS = [
    dict(fig="P4_F2Achiral", name="无手性代表：Mo 1 / Ru 2 / Ru 3",
         note="同一张图里放着前周期（Mo）与后周期（Ru）的对照，是「为什么换金属」最直观的一页。"),
    dict(fig="P4_F2Chiral", name="手性代表：Mo 4 / Ru 5 / Ru 6",
         note="手性配体把 E/Z 与对映选择性变成可调参数，代价是活性下降、底物范围收窄。"),
    dict(fig="P7_F1", name="Grubbs Ⅰ 代（6）",
         note="RuCl₂(=CHPh)(PCy₃)₂。1995 年商品化，用 PCy₃ 换来功能团耐受。"),
    dict(fig="P7_F2", name="Grubbs Ⅱ 代（7）与 H₂IMes",
         note="一个 PCy₃ 换成 NHC，引发更快、催化量更低。"),
    dict(fig="P5_F2", name="Ⅱ 代的商品化形态",
         note="Grubbs 诺奖讲座里的原图，同一骨架、换一个配体就换代。"),
    dict(fig="P6_F2", name="首批只含一个 NHC 的催化剂（15–17）",
         note="Fürstner–Herrmann、Nolan–Grubbs、Grubbs 三组几乎同时报道。"),
]

METHOD = dict(
    title="这座网站是怎么来的",
    paras=[
        ("这座网站的全部内容来自《现代化学创新思维训练》研讨主题 2「烯烃复分解反应」的文献调研结果。"
         "23 张图都从原文 PDF 以 450 dpi 裁出，已去除图注与页眉，未做任何重绘；每张图下方标注原文献出处。"),
        ("45 篇文献逐条经 Crossref 比对题名、刊名、卷、页、年份。英文条目全部核实；"
         "《有机化学》5 条 Crossref 未收录，站内明确标注「待核实」，不提供 DOI 链接，仅供索引。"),
        ("AI 问答只使用站内文本作答。检索在浏览器本地完成（BM25 + 中文二元切分），"
         "命中的片段连同问题一起发给 DeepSeek，模型被要求只用这些片段回答、并标注来源；"
         "站内没有相关内容时它会直接说「站内暂无相关内容」，而不是编造。"),
    ],
    limits=[
        "站内不含中文 5 条的原文，只有条目索引。",
        "AI 回答可能有措辞误差；涉及具体数字与结论请以图注与文献原文为准。",
        "本页所有 DOI 链接指向 doi.org，需要机构订阅才能取全文。",
    ],
)


def resolve_fig_paths():
    """图按源论文归档；返回 {(paper, fn) or fn: relpath}"""
    out = {}
    root = os.path.join(BASE, "图片")
    for p in BI.glob.glob(os.path.join(root, "*", "*.png")):
        out[os.path.basename(p)] = p
    return out


def main():
    os.makedirs(DATA, exist_ok=True)
    os.makedirs(IMGDIR, exist_ok=True)

    # ---------------- 论文
    papers = []
    for i, r in enumerate(LX.ROWS, 1):
        (ptype, phase, authors, journal, year, vol, pages, doi, title, why, in_doc) = r
        papers.append(dict(
            id=f"P{i:02d}", no=i, type=ptype, phase=phase, authors=authors,
            journal=journal, year=int(year) if str(year).isdigit() else year,
            vol=vol, pages=pages, doi=doi, title=title, why=why, inDoc=(in_doc == "是"),
            doiUrl=("https://doi.org/" + doi) if doi.startswith("10.") else "",
        ))

    # ---------------- 图
    mapping = resolve_fig_paths()
    figures = []
    for i, (paper, key, num, fn, page, section, caption, usage) in enumerate(BI.ROWS, 1):
        src = mapping.get(fn)
        assert src, f"missing image {fn}"
        dst = os.path.join(IMGDIR, fn)
        if not os.path.exists(dst) or os.path.getmtime(src) > os.path.getmtime(dst):
            shutil.copy2(src, dst)
        meta = BI.PAPERS[paper]
        figures.append(dict(
            id=os.path.splitext(fn)[0], no=i, file=fn, paperKey=paper,
            paper=f"{meta['authors']} ({meta['year']})",
            paperShort=meta["short"],
            journal=meta["journal"], year=meta["year"], vol=meta["vol"],
            pages=meta["pages"], cite=meta["cite"],
            figNo=num, docPage=page, section=section,
            caption=caption, usage=usage,
        ))

    # ---------------- 阶段绑定
    by_fig = {f["id"]: f for f in figures}
    by_paper_no = {p["no"]: p for p in papers}
    phases_out = []
    used_papers = set()
    for ph in PHASES:
        figs = []
        for fid in ph["figures"]:
            assert fid in by_fig, f"unknown figure {fid}"
            figs.append(fid)
            by_fig[fid]["phase"] = ph["id"]
        plist = [by_paper_no[n]["id"] for n in ph["papers"]]
        used_papers |= set(ph["papers"])
        phases_out.append(dict(
            id=ph["id"], no=ph["no"], period=ph["period"], name=ph["name"],
            tagline=ph["tagline"], lede=ph["lede"], points=ph["points"],
            insight=ph["insight"], papers=plist, figures=figs,
        ))
    missing_paper = set(range(1, 46)) - used_papers
    assert not missing_paper, f"papers not assigned to a phase: {sorted(missing_paper)}"
    assert len(used_papers) == 45
    fig_ids = {f["id"] for f in figures}
    assigned = {fid for ph in PHASES for fid in ph["figures"]}
    assert fig_ids == assigned, f"figure phase mismatch: {fig_ids ^ assigned}"

    site = dict(
        meta=dict(
            title="烯烃复分解",
            subtitle="从偶然发现到合成工具",
            en="Olefin Metathesis — Discovery, Mechanism and Catalysts",
            course="现代化学创新思维训练 · 研讨主题 2",
            updated="2026-11",
        ),
        stats=[
            dict(v="45", l="核实文献", n="14 综述/专著 + 31 原始论文"),
            dict(v="23", l="原始图", n="450 dpi，取自原文 PDF"),
            dict(v="5", l="研究阶段", n="1955–2024"),
            dict(v="4", l="原始清单缺口", n="零原始文献最要紧"),
        ],
        phases=phases_out,
        gaps=GAPS,
        catalysts=CATALYSTS,
        papers=papers,
        figures=figures,
        method=METHOD,
    )
    with open(os.path.join(DATA, "site.json"), "w", encoding="utf-8") as fh:
        json.dump(site, fh, ensure_ascii=False, indent=1)

    # ---------------- RAG chunks
    chunks = []

    def add(cid, anchor, kind, title, text, keys=""):
        chunks.append(dict(id=cid, anchor=anchor, kind=kind, title=title,
                           text=text, keys=keys))

    add("overview", "#top", "overview", "网站总览",
        "本网站围绕烯烃复分解反应，梳理 1955–2024 年的研究脉络。"
        "共核实 45 篇文献（14 篇综述/专著/诺奖讲座，31 篇原始研究论文），收录 23 张取自原文的图。"
        "内容分为五个阶段：现象与机理之争（1955–1978）、结构确立（1980–1996）、工具化（1995–2004）、"
        "诺奖与体系化（2005–2010）、选择性时代（2011–2024）。"
        "此外还有催化剂谱系、文献总览、图片档案与文献缺口分析。",
        "烯烃复分解 总览 简介 复分解 是什么")

    for ph in phases_out:
        pts = "；".join(f"{p['h']}：{p['t']}" for p in ph["points"])
        add(f"phase-{ph['id']}", f"#phase-{ph['id']}", "phase",
            f"{ph['period']} {ph['name']}",
            f"{ph['period']}，{ph['name']}。{ph['tagline']}。{ph['lede']}核心进展：{pts}"
            f"一句话概括：{ph['insight']}",
            f"{ph['period']} {ph['name']} 阶段 时期")

    for p in papers:
        doi = f" DOI {p['doi']}。" if p["doiUrl"] else ""
        add(f"paper-{p['id']}", f"#paper-{p['id']}", "paper",
            f"{p['authors']}（{p['year']}）",
            f"{p['authors']}. {p['title']}. {p['journal']} {p['year']}, {p['vol']}, {p['pages']}.{doi}"
            f"类型：{'综述/专著/诺奖讲座' if p['type'] == 'R' else '原始研究论文'}。"
            f"为什么重要：{p['why']}。所属阶段：{p['phase']}。",
            " ".join([p["authors"], p["title"], p["journal"], str(p["year"]), p["why"]]))

    for f in figures:
        add(f"fig-{f['id']}", f"#fig-{f['id']}", "figure",
            f"图 {f['figNo']}｜{f['caption']}",
            f"图 {f['figNo']}，出自 {f['cite']}，原文第 {f['docPage']} 页，章节「{f['section']}」。"
            f"图注：{f['caption']}。用法说明：{f['usage']}。",
            f"{f['figNo']} {f['caption']} {f['paperShort']} 图")

    for g in GAPS:
        add(f"gap-{g['id']}", f"#gaps", "gap", f"文献缺口 {g['no']}：{g['title']}",
            f"缺口{g['no']}：{g['title']}。{g['text']}本次处理：{g['fix']}",
            "缺口 文档 清单 不足 缺什么")

    add("gaps-summary", "#gaps", "gap", "文献缺口总结",
        "研讨文档原列 11 条文献，全部是综述、专著或诺奖讲座，原始研究论文 0 篇。"
        "四个缺口：零原始文献、断代 1995 前后、止于 2010、中文文献无法核实。"
        "本次共补入 38 篇，总数达到 45 篇。",
        "缺口 文档 11条 原始文献 不足")

    add("catalysts", "#catalysts", "catalyst", "催化剂谱系",
        "催化剂谱系收录三代代表性结构："
        "无手性代表（Mo 1、Ru 2、Ru 3）、手性代表（Mo 4、Ru 5、Ru 6）、"
        "Grubbs Ⅰ 代（6）、Grubbs Ⅱ 代（7）与 H₂IMes 配体、Ⅱ 代的商品化形态，"
        "以及首批只含一个 NHC 的催化剂（15–17）。"
        "设计线索：Mo 给结构与高活性，Ru 给耐受，NHC 给引发速率，手性配体给选择性。",
        "催化剂 谱系 Grubbs Schrock Hoveyda NHC 配体")

    add("method", "#method", "method", "方法与出处",
        "23 张图均从原文 PDF 以 450 dpi 裁出，去除图注与页眉，未重绘。"
        "45 篇文献经 Crossref 逐条核实题名、刊名、卷、页、年份。"
        "《有机化学》5 条 Crossref 未收录，标注为待核实且不提供 DOI 链接。"
        "AI 问答只使用站内文本作答，站内没有的内容会直接说明没有。",
        "方法 出处 来源 怎么做的 核实")

    with open(os.path.join(DATA, "rag-index.json"), "w", encoding="utf-8") as fh:
        json.dump(dict(version=1, chunks=chunks), fh, ensure_ascii=False, indent=1)

    print(f"papers   : {len(papers)}")
    print(f"figures  : {len(figures)}")
    print(f"phases   : {len(phases_out)}")
    print(f"chunks   : {len(chunks)}")
    print(f"images   : {len(os.listdir(IMGDIR))} files in site/assets/img")
    print(f"data     : {DATA}")


if __name__ == "__main__":
    main()

