# -*- coding: utf-8 -*-
"""Build 文献清单.xlsx : 45 verified papers, classified R (review) / P (primary)."""
import os
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# (no, type, phase, authors, journal, year, vol, pages, doi, title, why, in_doc)
ROWS = [
    ("P", "1 发现 1955–1978", "Banks, R. L.; Bailey, G. C.", "Ind. Eng. Chem. Prod. Res. Dev.", "1964", "3", "170–173",
     "10.1021/i360011a002", "Olefin Disproportionation. A New Catalytic Process",
     "乙烯→丙烯+丁烯，命名 disproportionation；工业侧最早系统报告", "否"),
    ("P", "1 发现 1955–1978", "Natta, G.; Dall'Asta, G.; Mazzanti, G.", "Angew. Chem. Int. Ed.", "1964", "3", "723–729",
     "10.1002/anie.196407231", "Stereospecific Homopolymerization of Cyclopentene",
     "WCl6/AlEtCl2 使环戊烯开环聚合；分子型催化剂起点", "否"),
    ("P", "1 发现 1955–1978", "Calderon, N.; Chen, H. Y.; Scott, K. W.", "Tetrahedron Lett.", "1967", "8", "3327–3329",
     "10.1016/S0040-4039(01)89881-6", "Olefin metathesis – A novel reaction for skeletal transformations",
     "首次用 W/Al 均匀体系证明烷叉基互换并命名 metathesis", "否"),
    ("P", "1 发现 1955–1978", "Calderon, N.; Ofstead, E. A.; Ward, J. P.", "J. Am. Chem. Soc.", "1968", "90",
     "4133–4140", "10.1021/ja01017a039", "Olefin metathesis. I. Acyclic vinylenic hydrocarbons",
     "无环乙烯基化合物系统研究，确立为一类反应", "否"),
    ("P", "1 发现 1955–1978", "Hérisson, J.-L.; Chauvin, Y.", "Makromol. Chem.", "1971", "141", "161–176",
     "10.1002/macp.1971.021410112", "Catalyse de transformation des oléfines par les complexes du tungstène. II",
     "金属亚烷基机理原始论文；当时无可分离的金属亚烷基", "否"),
    ("P", "1 发现 1955–1978", "Grubbs, R. H.; Brunck, T. K.", "J. Am. Chem. Soc.", "1972", "94", "2538–2540",
     "10.1021/ja00762a073", "Possible intermediate in the tungsten-catalyzed olefin metathesis reaction",
     "Grubbs 组最早的机理证据", "否"),
    ("P", "1 发现 1955–1978", "Katz, T. J.; McGinnis, J.", "J. Am. Chem. Soc.", "1975", "97", "1592–1594",
     "10.1021/ja00839a063", "Mechanism of the olefin metathesis reaction",
     "与金属杂环戊烷路线正面交锋", "否"),
    ("P", "1 发现 1955–1978", "Grubbs, R. H.; Burk, P. L.; Carr, D. D.", "J. Am. Chem. Soc.", "1975", "97",
     "3265–3267", "10.1021/ja00844a082", "Mechanism of the olefin metathesis reaction",
     "同位素标记检验机理；与 Katz 篇构成两种解释", "否"),
    ("P", "1 发现 1955–1978", "Tebbe, F. N.; Parshall, G. W.; Reddy, G. S.", "J. Am. Chem. Soc.", "1978", "100",
     "3611–3613", "10.1021/ja00479a061", "Olefin homologation with titanium methylene compounds",
     "Tebbe 试剂：第一个可用亚甲基转移试剂", "否"),

    ("P", "2 结构 1980–1996", "Wengrovius, J. H.; Schrock, R. R. 等", "J. Am. Chem. Soc.", "1980", "102",
     "4515–4516", "10.1021/ja00533a035", "Multiple metal-carbon bonds. 16. Tungsten-oxo alkylidene complexes",
     "钨氧代亚烷基：第一次有明确结构的复分解催化剂", "否"),
    ("P", "2 结构 1980–1996", "Schrock, R. R.; DePue, R. T.; Feldman, J. 等", "J. Am. Chem. Soc.", "1988", "110",
     "1423–1435", "10.1021/ja00213a014", "Preparation and reactivity of several alkylidene complexes of the type W(CHR')(NAr)(OR)2",
     "W 亚烷基系列系统合成，结构-活性关系成形", "否"),
    ("R", "2 结构 1980–1996", "Schrock, R. R.", "Acc. Chem. Res.", "1990", "23", "158–165", "10.1021/ar00173a007",
     "Living ring-opening metathesis polymerization catalyzed by well-characterized catalysts",
     "活性 ROMP 与结构明确性的方法论总结", "否"),
    ("P", "2 结构 1980–1996", "Schrock, R. R.; Murdzek, J. S.; Bazan, G. C. 等", "J. Am. Chem. Soc.", "1990", "112",
     "3875–3886", "10.1021/ja00166a023", "Synthesis of molybdenum imido alkylidene complexes and some reactions",
     "Mo 亚烷基结构确立；机理由推断变成可设计分子", "否"),
    ("P", "2 结构 1980–1996", "Schwab, P.; France, M. B.; Ziller, J. W.; Grubbs, R. H.", "Angew. Chem. Int. Ed.",
     "1995", "34", "2039–2041", "10.1002/anie.199520391",
     "A Series of Well-Defined Metathesis Catalysts – [RuCl2(=CHR')(PR3)2]",
     "Grubbs Ⅰ 代原始论文：活性与官能团耐受兼得", "否"),
    ("P", "2 结构 1980–1996", "Schwab, P.; Grubbs, R. H.; Ziller, J. W.", "J. Am. Chem. Soc.", "1996", "118",
     "100–110", "10.1021/ja952676d", "Synthesis and Applications of RuCl2(=CHR')(PR3)2",
     "配体效应系统研究：Ⅰ 代为什么长这样", "否"),

    ("P", "3 工具化 1999–2010", "Scholl, M.; Ding, S.; Lee, C. W.; Grubbs, R. H.", "Org. Lett.", "1999", "1",
     "953–956", "10.1021/ol990909q", "Synthesis and Activity of a New Generation of Ruthenium-Based Catalysts",
     "Grubbs Ⅱ 代原始论文：一个 PCy3 换成 H2IMes", "否"),
    ("R", "3 工具化 1999–2010", "Trnka, T. M.; Grubbs, R. H.", "Acc. Chem. Res.", "2001", "34", "18–29",
     "10.1021/ar000114f", "The Development of L2X2Ru=CHR Olefin Metathesis Catalysts",
     "Ru 体系发展史与时间线（报告时间线图源）", "是"),
    ("R", "3 工具化 1999–2010", "Chauvin, Y.", "Angew. Chem. Int. Ed.", "2006", "45", "3740–3747",
     "10.1002/anie.200601234", "Olefin Metathesis: The Early Days (Nobel Lecture)",
     "诺奖讲座：本人标注三条错路 WRONG TURNS", "是"),
    ("R", "3 工具化 1999–2010", "Schrock, R. R.", "Angew. Chem. Int. Ed.", "2006", "45", "3748–3759",
     "10.1002/anie.200600085", "Multiple Metal–Carbon Bonds for Catalytic Metathesis Reactions (Nobel Lecture)",
     "诺奖讲座：金属-碳多重键到催化", "是"),
    ("R", "3 工具化 1999–2010", "Grubbs, R. H.", "Angew. Chem. Int. Ed.", "2006", "45", "3760–3765",
     "10.1002/anie.200600680", "Olefin-Metathesis Catalysts for the Preparation of Molecules and Materials (Nobel Lecture)",
     "诺奖讲座：催化剂设计与工业应用", "是"),
    ("R", "3 工具化 1999–2010", "Hoveyda, A. H.; Zhugralin, A. R.", "Nature", "2007", "450", "243–251",
     "10.1038/nature06351", "The remarkable metal-catalysed olefin metathesis reaction",
     "应用全景：BILN 2061 与天然产物", "是"),
    ("R", "3 工具化 1999–2010", "Samojłowicz, C.; Bieniek, M.; Grela, K.", "Chem. Rev.", "2009", "109",
     "3708–3742", "10.1021/cr800524f", "Ruthenium-Based Olefin Metathesis Catalysts Bearing N-Heterocyclic Carbene Ligands",
     "NHC–Ru 全谱系", "是"),
    ("R", "3 工具化 1999–2010", "Vougioukalakis, G. C.; Grubbs, R. H.", "Chem. Rev.", "2010", "110", "1746–1787",
     "10.1021/cr9002424", "Ruthenium-Based Heterocyclic Carbene-Coordinated Olefin Metathesis Catalysts",
     "互补版本；催化循环图源", "是"),
    ("R", "3 工具化 1999–2010", "Lozano-Vila, A. M.; Monsaert, S.; Bajek, A.; Verpoort, F.", "Chem. Rev.", "2010",
     "110", "4865–4909", "10.1021/cr900346r", "Ruthenium-Based Olefin Metathesis Catalysts Derived from Alkynes",
     "由炔烃制备 Ru 催化剂的独立路线", "是"),
    ("R", "3 工具化 1999–2010", "Calderon, N.", "Acc. Chem. Res.", "1972", "5", "127–132", "10.1021/ar50052a002",
     "Olefin metathesis reaction", "发现期定量证据与机理讨论（图源）", "是"),
    ("R", "3 工具化 1999–2010", "Ivin, K. J.; Mol, J. C.", "Academic Press（专著）", "1997", "—", "—",
     "10.1016/B978-0-12-377045-5.X5000-9", "Olefin Metathesis and Metathesis Polymerization",
     "唯一权威教科书：反应类型与动力学总账", "否"),
    ("R", "3 工具化 1999–2010", "Grubbs, R. H. (Ed.)", "Wiley-VCH（专著，3 卷）", "2003", "—", "—",
     "10.1002/9783527619481", "Handbook of Metathesis (1st ed.)", "2003 年时领域全貌", "否"),
    ("R", "3 工具化 1999–2010", "Grubbs, R. H.; Wenzel, A. G. (Eds.)", "Wiley-VCH（专著，3 卷）", "2015", "—",
     "—", "10.1002/9783527674107", "Handbook of Metathesis (2nd ed.)", "补入 2011 年后选择性工作", "否"),

    ("P", "4 选择性 2011–2024", "Endo, K.; Grubbs, R. H.", "J. Am. Chem. Soc.", "2011", "133", "8525–8527",
     "10.1021/ja202818v", "Chelated Ruthenium Catalysts for Z-Selective Olefin Metathesis",
     "Z-选择性 Ru 的起点：螯合配体把 Z 拉高", "否"),
    ("P", "4 选择性 2011–2024", "Keitz, B. K.; Endo, K.; Patel, P. R. 等", "J. Am. Chem. Soc.", "2012", "134",
     "693–699", "10.1021/ja210225e", "Improved Ruthenium Catalysts for Z-Selective Olefin Metathesis",
     "改进版 Z-选择性 Ru；活性与选择性同升", "否"),
    ("P", "4 选择性 2011–2024", "Meek, S. J.; O'Brien, R. V.; Llaveria, J.; Schrock, R. R.; Hoveyda, A. H.",
     "Nature", "2011", "471", "461–466", "10.1038/nature09957",
     "Catalytic Z-selective olefin cross-metathesis for natural product synthesis",
     "Z-选择性 CM 用于天然产物合成", "否"),
    ("P", "4 选择性 2011–2024", "Yu, M.; Wang, C.; Kyle, A. F. 等", "Nature", "2011", "479", "88–93",
     "10.1038/nature10563", "Synthesis of macrocyclic natural products by catalyst-controlled stereoselective RCM",
     "催化剂控制的大环天然产物合成", "否"),
    ("P", "4 选择性 2011–2024", "Peryshkov, D. V.; Schrock, R. R.", "J. Am. Chem. Soc.", "2011", "133",
     "20754–20757", "10.1021/ja210349m", "Z-Selective Olefin Metathesis Reactions Promoted by Tungsten",
     "W 体系也能调 Z-选择性", "否"),
    ("P", "4 选择性 2011–2024", "Thomas, R. M.; Keitz, B. K.; Champagne, T. M.; Grubbs, R. H.", "J. Am. Chem. Soc.",
     "2011", "133", "7490–7496", "10.1021/ja200246e", "Highly Selective Ruthenium Metathesis Catalysts for Ethenolysis",
     "乙烯解：内烯切成端烯，生物质方向", "否"),
    ("P", "4 选择性 2011–2024", "Keitz, B. K.; Bouffard, J.; Bertrand, G.; Grubbs, R. H.", "J. Am. Chem. Soc.",
     "2011", "133", "8498–8501", "10.1021/ja203070r",
     "Protonolysis of a Ruthenium–Carbene Bond and Applications in Olefin Metathesis",
     "理解「催化剂怎么死」", "否"),
    ("P", "4 选择性 2011–2024", "Marx, V. M.; Herbert, M. B.; Keitz, B. K.; Grubbs, R. H.", "J. Am. Chem. Soc.",
     "2013", "135", "94–97", "10.1021/ja311241q", "Stereoselective Access to Z and E Macrocycles",
     "Z-选择性与底物控制的边界", "否"),
    ("P", "4 选择性 2011–2024", "Occhipinti, G.; Hansen, F. R. 等", "J. Am. Chem. Soc.", "2013", "135",
     "3331–3334", "10.1021/ja311505v", "Simple and Highly Z-Selective Ruthenium-Based Olefin Metathesis Catalysts",
     "把 Z-选择性设计做「便宜」", "否"),
    ("P", "4 选择性 2011–2024", "Koh, M. J.; Nguyen, T. T.; Zhang, H.; Schrock, R. R.; Hoveyda, A. H.", "Nature",
     "2016", "531", "459–465", "10.1038/nature17396",
     "Direct synthesis of Z-alkenyl halides through catalytic cross-metathesis", "Z-烯基卤化物的直接合成", "否"),
    ("P", "4 选择性 2011–2024", "Lu, Y.-X.; Tournilhac, F.; Leibler, L.; Guan, Z.", "J. Am. Chem. Soc.", "2012",
     "134", "8424–8427", "10.1021/ja303356z",
     "Making Insoluble Polymer Networks Malleable via Olefin Metathesis",
     "复分解让交联网络可重排 → vitrimer", "否"),
    ("P", "4 选择性 2011–2024", "Sathe, D.; Zhou, J.; Chen, H. 等", "Nat. Chem.", "2021", "13", "743–750",
     "10.1038/s41557-021-00748-5",
     "Olefin metathesis-based chemically recyclable polymers enabled by fused-ring monomers",
     "化学可回收聚合物：复分解解聚闭环", "否"),
    ("P", "4 选择性 2011–2024", "Takebayashi, S.; Iron, M. A.; Feller, M. 等", "Nat. Catal.", "2022", "5",
     "494–502", "10.1038/s41929-022-00793-4", "Iron-catalysed ring-opening metathesis polymerization",
     "铁催化 ROMP：摆脱贵金属依赖", "否"),
    ("P", "4 选择性 2011–2024", "Lemcoff, N.; Nechmad, N. B.; Eivgi, O. 等", "Nat. Chem.", "2023", "15",
     "475–482", "10.1038/s41557-022-01124-7", "Plasmonic photothermal activation of olefin metathesis",
     "光热激活：外场控制反应开关", "否"),
    ("P", "4 选择性 2011–2024", "Hsu, T.-W.; Kempel, S. J.; Felix, A. 等", "Nat. Chem.", "2023", "15", "14–20",
     "10.1038/s41557-022-01060-6", "Stereocontrolled acyclic diene metathesis polymerization",
     "立构受控 ADMET 聚合", "否"),
    ("R", "4 选择性 2011–2024", "Fürstner, A.", "Science", "2013", "341", "1229713", "10.1126/science.1229713",
     "Teaching Metathesis \"Simple\" Stereochemistry", "选择性问题的纲领性评论", "否"),
    ("P", "4 选择性 2011–2024", "Ibrahim, T.; Ritacco, A.; Nalley, D. 等", "Chem. Commun.", "2024", "60",
     "1361–1371", "10.1039/d3cc05612k", "Chemical recycling of polyolefins via metathesis",
     "复分解路线化学回收聚烯烃最新总结", "否"),
]

DOC_LISTED = [
    ("R", "文档原列", "Chauvin / Schrock / Grubbs", "Angew. Chem. Int. Ed.", "2006", "45", "3740–3765",
     "（合集）", "三篇诺奖讲座合订", "文档原文条目", "是"),
    ("R", "文档原列", "Calderon, N.", "Acc. Chem. Res.", "1972", "5", "127–132", "10.1021/ar50052a002",
     "Olefin metathesis reaction", "同上表第 25 条", "是"),
    ("R", "文档原列", "Trnka, T. M.; Grubbs, R. H.", "Acc. Chem. Res.", "2001", "34", "18–29",
     "10.1021/ar000114f", "The Development of L2X2Ru=CHR Olefin Metathesis Catalysts", "同上表第 17 条", "是"),
    ("R", "文档原列", "Hoveyda, A. H.; Zhugralin, A. R.", "Nature", "2007", "450", "243–251",
     "10.1038/nature06351", "The remarkable metal-catalysed olefin metathesis reaction", "同上表第 21 条", "是"),
    ("R", "文档原列", "Samojłowicz, C.; Bieniek, M.; Grela, K.", "Chem. Rev.", "2009", "109", "3708–3742",
     "10.1021/cr800524f", "NHC-bearing Ru catalysts", "同上表第 22 条", "是"),
    ("R", "文档原列", "Lozano-Vila, A. M. 等", "Chem. Rev.", "2010", "110", "4865–4909", "10.1021/cr900346r",
     "Ru catalysts derived from alkynes", "同上表第 24 条", "是"),
    ("R", "文档原列", "Vougioukalakis, G. C.; Grubbs, R. H.", "Chem. Rev.", "2010", "110", "1746–1787",
     "10.1021/cr9002424", "Heterocyclic carbene-coordinated Ru catalysts", "同上表第 23 条", "是"),
]

CN = [
    ("《有机化学》2001, 21, 445–452", "中文综述", "Crossref 未收录，未核实"),
    ("《有机化学》2001, 21, 541–548", "中文综述", "Crossref 未收录，未核实"),
    ("《有机化学》2005, 25, 1334–1341", "中文综述", "Crossref 未收录，未核实"),
    ("《有机化学》2010, 30, 968–980", "中文综述", "Crossref 未收录，未核实"),
    ("《有机化学》2020, 40, 2725–2741", "中文综述", "Crossref 未收录，未核实"),
]


def main():
    wb = Workbook()
    ws = wb.active
    ws.title = "45篇核心文献"
    head = ["序号", "类型", "阶段", "作者", "期刊/出版", "年份", "卷", "页", "DOI", "标题", "为什么重要", "文档原列"]
    ws.append(head)
    for i, r in enumerate(ROWS, 1):
        ws.append([i] + list(r))

    thin = Side(style="thin", color="D9D9D9")
    navy = PatternFill("solid", fgColor="000098")
    for c in range(1, len(head) + 1):
        cell = ws.cell(row=1, column=c)
        cell.font = Font(bold=True, color="FFFFFF", size=11)
        cell.fill = navy
        cell.alignment = Alignment(horizontal="center", vertical="center")
    widths = [5, 6, 18, 40, 26, 6, 6, 12, 30, 52, 46, 9]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    for row in ws.iter_rows(min_row=2, max_row=len(ROWS) + 1):
        rtype = row[1].value
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
        if rtype == "R":
            for cell in row:
                cell.fill = PatternFill("solid", fgColor="E5F0FF")
        ws.row_dimensions[row[0].row].height = 32
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:L{len(ROWS) + 1}"

    # sheet 2: 统计
    ws2 = wb.create_sheet("统计与缺口")
    ws2.append(["项目", "数量", "说明"])
    nR = sum(1 for r in ROWS if r[0] == "R")
    nP = sum(1 for r in ROWS if r[0] == "P")
    ws2.append(["综述 / 专著 / 诺奖讲座（R）", nR, "二手总结，给结论"])
    ws2.append(["原始研究论文（P）", nP, "一手证据，给过程"])
    ws2.append(["合计", len(ROWS), "全部经 Crossref 逐条核实"])
    ws2.append(["文档原列", 11, "7 英文 + 5 中文；其中原始论文 0 篇"])
    ws2.append(["文档列为综述的比例", "11/11", "100% 二手文献"])
    ws2.append(["本次新增", len(ROWS) - 7, "含 31 篇原始论文 + 7 篇补充综述/专著"])
    ws2.append(["中文文献未核实", 5, "Crossref 未收录，需按 CNKI 核对"])
    for c in range(1, 4):
        ws2.cell(row=1, column=c).font = Font(bold=True, color="FFFFFF", size=11)
        ws2.cell(row=1, column=c).fill = navy
    ws2.column_dimensions["A"].width = 34
    ws2.column_dimensions["B"].width = 10
    ws2.column_dimensions["C"].width = 56
    for row in ws2.iter_rows(min_row=2, max_row=8):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # sheet 3: 文档原列
    ws3 = wb.create_sheet("文档原列11条")
    ws3.append(["序号", "类型", "条目", "核实状态"])
    for i, c in enumerate(CN, 1):
        ws3.append([i, "中文综述", c[0], c[2]])
    for i, r in enumerate(DOC_LISTED, len(CN) + 1):
        ws3.append([i, "英文综述/讲座", f"{r[3]} {r[5]}, {r[6]}, {r[7]}", f"已核实 DOI {r[8]}"])
    for c in range(1, 5):
        ws3.cell(row=1, column=c).font = Font(bold=True, color="FFFFFF", size=11)
        ws3.cell(row=1, column=c).fill = navy
    ws3.column_dimensions["A"].width = 6
    ws3.column_dimensions["B"].width = 18
    ws3.column_dimensions["C"].width = 52
    ws3.column_dimensions["D"].width = 40

    out = os.path.join(BASE, "文献清单.xlsx")
    wb.save(out)
    print(f"saved {out}")
    print(f"  R={nR}  P={nP}  total={len(ROWS)}")


if __name__ == "__main__":
    main()

