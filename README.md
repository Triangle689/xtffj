# 烯烃复分解 · 学术展示站

围绕**烯烃复分解反应**（Olefin Metathesis）的静态学术展示站：1955–2024 年研究脉络、
45 篇核实文献、23 张取自原文 PDF 的图，外加一个**只读站内内容**的 AI 问答抽屉。

> 站点：`site/`（纯静态，无构建、无后端）
> 内容来源：《现代化学创新思维训练》研讨主题 2「烯烃复分解反应」的文献调研

---

## 站点内容

| 区块 | 内容 |
|---|---|
| 首页 | 一句话概括 + 4 个关键数字 |
| §1 研究脉络 | 5 个阶段的时间线，可点击跳转 |
| §2 五个阶段 | 每阶段：导语、4 条核心进展、原文图、关联文献 |
| §3 催化剂谱系 | 6 组结构图对照（Mo / Ru / Ⅰ 代 / Ⅱ 代 / NHC / 手性） |
| §4 文献缺口 | 研讨文档 11 条清单的四个缺口 |
| §5 文献总览 | 45 篇可筛选表格（综述 / 原始 / 文档原列），点开看摘要与 DOI |
| §6 图片档案 | 23 张图，灯箱放大、左右翻页、逐张标注出处 |
| §7 方法与出处 | 图的裁切方式、DOI 核实方法、已知局限 |

**每张图都标注原文献出处**（作者、刊名、年份、卷、页、原文页码、章节）。
**站内搜索**：标题栏搜索框（快捷键 `/`），结果按「阶段 / 文献 / 图 / 缺口」分组并高亮。

## AI 问答

- 抽屉式面板，右下角「AI 问答」或标题栏按钮打开；
- **只依据站内 81 个文本片段作答**：先本地 BM25 检索，检索不到实词重叠就**不调用模型**，直接说「站内暂无相关内容」；
- 命中后**先跳转**到最相关章节，再流式输出回答，每个论断带 `[来源 N]`，可点击回跳；
- 问题与回答存在浏览器本地（localStorage），可回看、单条删除、导出 JSON；
- 需要自备 DeepSeek API Key（存在本机，不进仓库）。

设计与实现细节见 **[docs/AI问答方案.md](docs/AI问答方案.md)**。

---

## 本地预览

```bash
# 任意静态服务器都行，必须在 http:// 下打开（页面会 fetch 数据文件）
cd site && python -m http.server 4321
# 浏览器打开 http://127.0.0.1:4321/
```

> 直接双击 `site/index.html` 会被浏览器的 `file://` 策略拦住 `fetch`，页面会给出提示。

## 重新生成站点

```bash
python _tools/build_site_data.py   # site/data/site.json + rag-index.json，并拷贝 23 张图
python _tools/build_site.py        # 渲染 site/index.html
```

依赖：`python`（含 `openpyxl`、`Pillow`）；数据源为 `_tools/build_index.py`（图元数据）与
`_tools/build_lit_xlsx.py`（45 篇文献）。

## 部署到 GitHub Pages

仓库已带工作流 `.github/workflows/pages.yml`，推上去后：

1. 推到 `main`；
2. 仓库 **Settings → Pages → Build and deployment → Source** 选 **GitHub Actions**；
3. 首次 push 会自动跑 `Deploy site to Pages`，完成后地址形如
   `https://<用户名>.github.io/<仓库名>/`。

因为站内所有路径都是相对的（`assets/…`、`data/…`），放在**项目子路径**下也能正常工作，不需要改任何配置。

命令行推送（首次）：

```bash
git remote add origin https://github.com/<用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

---

## 目录

```
site/                       # ← 部署这一个目录即可
  index.html                #   预渲染，无 JS 也能读
  assets/style.css
  assets/search.js          #   BM25（站内搜索与 AI 检索共用）
  assets/app.js             #   页面交互
  assets/ai.js              #   AI 抽屉
  assets/img/               #   23 张图（450 dpi，已去图注与页眉）
  data/site.json            #   站点数据
  data/rag-index.json       #   81 个检索片段
_tools/                     # 构建与 QA 脚本
docs/AI问答方案.md           # AI 问答的方案规划
文献调研与研究脉络.md          # 45 篇文献 + 四阶段脉络 + 缺口分析
文献清单.xlsx                # 可筛选的文献清单（3 个表）
index.xlsx / index.md       # 图的索引（图号、页码、章节、用法）
```

## 已知局限

- 《有机化学》5 条中文文献 Crossref 未收录，站内只做索引，**不提供 DOI 链接**，引用前请按 CNKI 核对；
- AI 回答可能有措辞误差，涉及数字与结论请以图注与原文为准；
- 站内图片取自期刊原文，仅用于课堂研讨与教学展示；如涉版权问题请自行移除 `site/assets/img/`。

## 单文件版（离线可开）

```bash
python _tools/build_single.py     # → 烯烃复分解.html
```

把 CSS / JS / 数据全部内联、23 张图转成 base64，产出一个约 4.4 MB 的**单一 HTML**：
双击即可打开，不需要服务器、不加载任何外部资源（字体用系统字体，无 CDN）。

- 图片限宽 1400、PNG-8 48 色量化（线稿不虚），总体积 1.5 MB；
- 与多文件站功能一致：时间线、阶段、图档灯箱、文献表、搜索、AI 抽屉；
- 唯一区别：AI 提问若在 `file://` 下被接口的跨域策略拒绝，改用本地 http 服务打开即可。
