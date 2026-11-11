# -*- coding: utf-8 -*-
"""Build 图片索引 (index.xlsx + index.md) for the metathesis topic deck.

One row per image, 1:1 with the PNG files on disk.
"""
import glob
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PAPERS = {
    "P1": dict(short="Calderon 1972", authors="Calderon, N.",
               cite="N. Calderon, *Acc. Chem. Res.* **1972**, 5, 127-132.",
               journal="Acc. Chem. Res.", year="1972", vol="5", pages="127-132",
               file="pdf/10.1021_ar50052a002.pdf"),
    "P2": dict(short="Trnka & Grubbs 2001", authors="Trnka, T. M.; Grubbs, R. H.",
               cite="T. M. Trnka, R. H. Grubbs, *Acc. Chem. Res.* **2001**, 34, 18-29.",
               journal="Acc. Chem. Res.", year="2001", vol="34", pages="18-29",
               file="pdf/10.1021_ar000114f.pdf"),
    "P3": dict(short="Chauvin 2006", authors="Chauvin, Y.",
               cite="Y. Chauvin, *Angew. Chem. Int. Ed.* **2006**, 45, 3740-3747（诺奖讲座）.",
               journal="Angew. Chem. Int. Ed.", year="2006", vol="45", pages="3740-3747",
               file="pdf/10.1002_anie.200601234.pdf"),
    "P4": dict(short="Hoveyda & Zhugralin 2007", authors="Hoveyda, A. H.; Zhugralin, A. R.",
               cite="A. H. Hoveyda, A. R. Zhugralin, *Nature* **2007**, 450, 243-251.",
               journal="Nature", year="2007", vol="450", pages="243-251",
               file="pdf/10.1038_nature06351.pdf"),
    "P5": dict(short="Grubbs 2006", authors="Grubbs, R. H.",
               cite="R. H. Grubbs, *Angew. Chem. Int. Ed.* **2006**, 45, 3760-3765（诺奖讲座）.",
               journal="Angew. Chem. Int. Ed.", year="2006", vol="45", pages="3760-3765",
               file="pdf/10.1002_anie.200600680.pdf"),
    "P6": dict(short="Samojłowicz et al. 2009", authors="Samojłowicz, C.; Bieniek, M.; Grela, K.",
               cite="C. Samojłowicz, M. Bieniek, K. Grela, *Chem. Rev.* **2009**, 109, 3708-3742.",
               journal="Chem. Rev.", year="2009", vol="109", pages="3708-3742",
               file="pdf/10.1021_cr800524f.pdf"),
    "P7": dict(short="Vougioukalakis & Grubbs 2010",
               authors="Vougioukalakis, G. C.; Grubbs, R. H.",
               cite="G. C. Vougioukalakis, R. H. Grubbs, *Chem. Rev.* **2010**, 110, 1746-1787.",
               journal="Chem. Rev.", year="2010", vol="110", pages="1746-1787",
               file="pdf/10.1021_cr9002424.pdf"),
}

# (paper, key, 图号, 文件名, 页码(印刷页), 章节, 图题, 备注/用法)
ROWS = [
    ("P1", "F1", "Figure 1", "P1_F1.png", 129, "Random Distribution of Alkylidene Groups",
     "2-戊烯与 6-十二烯复分解：产物分布符合纯随机重排",
     "封面后的第一张定量证据：实线是理想随机分布，点是实测值。讲“复分解 = 碎片随机组合”，关掉交换机制。"),
    ("P1", "F2", "Figure 2", "P1_F2.png", 130, "The Transalkylidenation Step",
     "金属配体 SA/AS 电子重定位，使“准环丁烷”过渡态在轨道对称性上被允许",
     "讲“为什么当时只能想到四元环”：四中心过渡态不是真环丁烷。一张图替代一段轨道对称性论证。"),
    ("P1", "F3", "Figure 3", "P1_F3.png", 131, "The Transalkylidenation Step",
     "四亚甲基-金属过渡态（A→B→C）",
     "与 F2 二选一；建议 F2 主用，F3 用于回答“那键是怎么断的”。"),
    ("P1", "F4", "Figure 4", "P1_F4.png", 132, "Macrocyclics and Catenanes",
     "索烃的生成：环形链经 360° 扭转与复分解缝合",
     "讲“早期只当工业反应太可惜”的注脚；可作备讲页，呼应高分子主题。"),

    ("P2", "F2", "Figure 2", "P2_F2.png", 19, "Background",
     "里程碑时间线：1956–2003 催化剂与机理的关键节点",
     "全篇叙事骨架，用一页把 2005 诺奖前的五十年串起来。讲到哪一步就指哪一行。"),
    ("P2", "F3", "Figure 3", "P2_F3.png", 19, "Background",
     "Chauvin 提出的金属亚烷基（卡宾）+ 金属杂环丁烷机理",
     "机理页的核心图；与 P3_F12 配合：这张给“结论”，P3_F12 给“为什么”。"),
    ("P2", "F6", "Figure 6", "P2_F6.png", 24, "Mechanistic Studies",
     "Grubbs 催化剂的引发机理：膦解离型（A）与亚烷基/膦结合型 4 两条路",
     "解释“Ⅱ 代为什么更强却被苯乙烯卡住”：Hoveyda 型靠 O→Ru 解离引发。"),

    ("P3", "F8", "Figure 8", "P3_F8.png", 3744, "Olefin Metathesis: Discovery and First Achievements",
     "初期的“错误转向”：环丁烷、四亚甲基、重排金属杂环戊烷中间体（后被否定）",
     "讲“四条路只有一条活下来”：三个被否定的中间体并列，比一段文字有力。"),
    ("P3", "F12", "Figure 12", "P3_F12.png", 3746, "Olefin Metathesis: Discovery and First Achievements",
     "一个卡宾机理统一三类反应：歧化、开环聚合、调聚",
     "Chauvin 自己的示意（中性版机理），配色干净，适合投影；F8 与它相邻放。"),

    ("P4", "F1", "Figure 1", "P4_F1.png", 243, "Olefin metathesis and its importance",
     "三类复分解的通用图式：交叉（CM）、关环（RCM）、开环/交叉（ROCM 型）",
     "全篇第 2 页的“地图”：C1=C2 与 C3=C4 两个片段三种重新分配。宽幅图，用 fig_wide。"),
    ("P4", "F2A", "Figure 2 (top)", "P4_F2Achiral.png", 244, "Catalysts that make it possible",
     "无手性代表性催化剂：Mo 1、Ru 2（Grubbs I 型）、Ru 3（Hoveyda 型）",
     "页：前后周期对照——Mo 1 与 Ru 2/3 同框；Mes = 米基（mesityl）也在此定义。"),
    ("P4", "F2B", "Figure 2 (bottom)", "P4_F2Chiral.png", 244, "Catalysts that make it possible",
     "手性代表性催化剂：手性 Mo 4、手性 Ru 5、受限构象 Ru 6",
     "页：立体选择性——手性配体把“哪个烯烃先反应”变成选择性工具。"),
    ("P4", "F3A", "Figure 3A", "P4_F3A.png", 245, "Catalytic ring-closing metathesis",
     "关环复分解的通式机理：引发期 + 增长期，pathway a/b",
     "机理主场。讲清 pathway b：环内第二个 C=C 被裂解，这才是关环而非交叉。"),
    ("P4", "F3B", "Figure 3B", "P4_F3B.png", 245, "Catalytic ring-closing metathesis",
     "关环复分解合成天然产物：黄曲霉毒素 fl uvirucin B1（92%）与 cylindrocyclophane F（72%）",
     "证明“反应有用”：一步关 14 元环。可与 P4_F8 合并成“应用”页。"),
    ("P4", "F8", "Figure 8", "P4_F8.png", 248, "Catalytic olefin metathesis and a better quality of life",
     "工业级应用：BILN 2061（丙型肝炎药物）核心环 400 kg 规模，83%，>99% 顺式",
     "“学术反应 → 工业资产”的最强证据；讲选择性（>99% cis）与放大。"),

    ("P5", "F2", "Figure 2", "P5_F2.png", 3763, "第二章",
     "第二代商品化催化剂（Grubbs II，7）：一个 PCy3 换成 NHC",
     "“换一个配体 = 换一代催化剂”的视觉证据；配合 P6_F2 讲 H2IMes。"),
    ("P5", "S7", "Scheme 7", "P7_S7.png", 3764, "第二章",
     "无溶剂交叉复分解制备“绿色”化合物：1-己烯 + 乙酸己烯酯",
     "讲交叉复分解为什么难：50% 收率、85:15 E/Z——同源二聚竞争。"),

    ("P6", "S3", "Scheme 3", "P5_S3.png", 3710, "2. Early Ruthenium Alkylidene Complexes",
     "复分解的基准反应：RCM / CM / 烯炔 RCM / ROMOP / ROMP",
     "一页建立“五类反应”的共同语法；备讲页，时间紧可跳过。"),
    ("P6", "S4", "Scheme 4", "P5_S4.png", 3711, "3. Modern Ruthenium Alkylidene Complexes",
     "含 Ru 预催化剂的完整催化循环：引发（两条路）+ 增长",
     "机理页首选：同一张图同框给出引发与增长，箭头清楚。"),
    ("P6", "F2", "Figure 2", "P6_F2.png", 3711, "3. Modern Ruthenium Alkylidene Complexes",
     "首批只含一个 NHC 的催化剂（15 Fürstner–Herrmann，16 Nolan–Grubbs，17 Grubbs）",
     "“NHC 时代”起点；与 P5_F2 合看：7/17 即 Grubbs II 的结构式。"),

    ("P7", "F1", "Figure 1", "P7_F1.png", 3763, "第二章（Grubbs 诺奖讲座）",
     "第一代商品化催化剂 Grubbs I（6）：RuCl2(=CHPh)(PCy3)2 的原图",
     "“一代/二代同框”的左半边；与 P7_F2 成对使用。"),
    ("P7", "F2", "Figure 2", "P7_F2.png", 1748, "2. Introduction to the Use of HCs",
     "一代（2/4）与二代（3/5）Ru 催化剂；H2IMes 的结构",
     "把“一代/二代 = 同一骨架换一个配体”讲成一句话；H2IMes 定义放在这里。"),
    ("P7", "S1", "Scheme 1", "P6_S1.png", 1747, "1. Brief Introduction to Olefin Metathesis",
     "复分解的催化循环（金属亚烷基 + 金属杂环丁烷）",
     "机理备选图；与 P6_S4 同源，选一张即可。"),
]


def main():
    outdir = os.path.join(BASE, "图片")
    on_disk = {os.path.basename(p): p for p in glob.glob(os.path.join(outdir, "*", "*.png"))}
    disk_keys = set()
    for p in glob.glob(os.path.join(outdir, "*", "*.png")):
        disk_keys.add(f"{os.path.basename(os.path.dirname(p))}/{os.path.basename(p)}")
    rows = []
    for paper, key, num, fn, page, section, caption, usage in ROWS:
        # 图源论文目录（图片按源文件归档，同一张官方图可能被两篇综述共用）
        src = paper if f"{paper}/{fn}" in disk_keys else None
        if src is None:
            cand = [k for k in disk_keys if k.endswith("/" + fn)]
            assert cand, f"missing image {fn}"
            src = cand[0].split("/")[0]
        meta = PAPERS[paper]
        rows.append(dict(paper=paper, short=meta["short"], num=num, fn=fn,
                         rel=f"图片/{src}/{fn}", page=page, section=section,
                         caption=caption, usage=usage, meta=meta))
    used = {r["rel"].replace("图片/", "") for r in rows}
    missing = disk_keys - used
    assert not missing, f"images without an index row: {missing}"

    wb = Workbook()
    ws = wb.active
    ws.title = "图片索引"
    head = ["序号", "论文", "图号", "文件名", "页码", "所属章节", "图题", "备注（用法）"]
    ws.append(head)
    for i, r in enumerate(rows, 1):
        ws.append([i, r["short"], r["num"], r["rel"], r["page"], r["section"],
                   r["caption"], r["usage"]])
    thin = Side(style="thin", color="D9D9D9")
    navy = PatternFill("solid", fgColor="000098")
    for c in range(1, len(head) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
    widths = [6, 24, 12, 26, 7, 34, 52, 62]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2, max_row=len(rows) + 1):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        ws.row_dimensions[row[0].row].height = 34
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:H{len(rows) + 1}"
    xlsx = os.path.join(BASE, "index.xlsx")
    wb.save(xlsx)

    # ---------------- index.md
    md = ["# 图片索引 — 烯烃复分解反应（研讨主题 2）", "",
          f"共 {len(rows)} 张图，与 `图片/` 下文件一一对应（450 dpi，已裁去图注与页眉，分面图已拆分）。",
          "全部取自本主题「主要参考文献」所列文献的原文 PDF。", ""]
    for paper in PAPERS:
        sub = [r for r in rows if r["paper"] == paper]
        if not sub:
            continue
        m = PAPERS[paper]
        md.append(f"## {paper} · {m['cite']}")
        md.append("")
        md.append("| 序号 | 图号 | 图片 | 页码 | 章节 | 图题 | 备注（用法） |")
        md.append("|---|---|---|---|---|---|---|")
        for r in sub:
            i = rows.index(r) + 1
            md.append(f"| {i} | {r['num']} | ![{r['fn']}]({r['rel']}) | {r['page']} | "
                      f"{r['section']} | {r['caption']} | {r['usage']} |")
        md.append("")
    mdthe = os.path.join(BASE, "index.md")
    open(mdthe, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"index.xlsx ({len(rows)} rows), index.md written")
    for r in rows:
        print(" ", r["fn"], r["num"], "p" + str(r["page"]))


if __name__ == "__main__":
    main()
