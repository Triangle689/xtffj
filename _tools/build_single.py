# -*- coding: utf-8 -*-
"""把 site/ 打成**一个**自包含 HTML：CSS/JS/数据内联，图片转 base64 data URI。

打开方式：双击即可（不需要服务器）。AI 问答仍需自备 Key；若浏览器的 file:// 源
不被接口接受，用 python -m http.server 起本地服务即可。

用法：python _tools/build_single.py [输出路径]
"""
import base64
import io
import json
import os
import re
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.dirname(HERE)
SITE = os.path.join(BASE, "site")

MAX_W = 1400          # 单文件版限宽，屏幕上足够
PALETTE = 48          # PNG-8 调色板色数（线稿足够，且不虚）


def data_uri_png(fn):
    """限宽 + 调色板量化（无抖动），返回 data URI。"""
    path = os.path.join(SITE, "assets", "img", fn)
    im = Image.open(path).convert("RGB")
    w, h = im.size
    if w > MAX_W:
        im = im.resize((MAX_W, max(1, round(h * MAX_W / w))), Image.LANCZOS)
    q = im.quantize(colors=PALETTE, method=Image.Quantize.MEDIANCUT,
                    dither=Image.Dither.NONE)
    buf = io.BytesIO()
    q.save(buf, "PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return "data:image/png;base64," + b64, len(buf.getvalue()), (w, h), q.size


def read(p):
    with open(p, encoding="utf-8") as fh:
        return fh.read()


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE, "烯烃复分解.html")

    html = read(os.path.join(SITE, "index.html"))
    css = read(os.path.join(SITE, "assets", "style.css"))
    js_search = read(os.path.join(SITE, "assets", "search.js"))
    js_app = read(os.path.join(SITE, "assets", "app.js"))
    js_ai = read(os.path.join(SITE, "assets", "ai.js"))
    site = json.loads(read(os.path.join(SITE, "data", "site.json")))
    rag = json.loads(read(os.path.join(SITE, "data", "rag-index.json")))

    # ---------- 图片：替换 <img src="assets/img/x.png">
    uris = {}
    total = 0
    report = []
    for m in sorted(set(re.findall(r'src="assets/img/([^"]+)"', html))):
        uri, nbytes, orig, newsize = data_uri_png(m)
        uris[m] = uri
        total += nbytes
        report.append((m, orig, newsize, nbytes))

    def repl_src(mo):
        fn = mo.group(1)
        return 'src="%s"' % uris[fn]

    html = re.sub(r'src="assets/img/([^"]+)"', repl_src, html)

    # ---------- favicon 内联
    fav = os.path.join(SITE, "assets", "favicon.svg")
    if os.path.exists(fav):
        svg = read(fav).strip()
        b64 = base64.b64encode(svg.encode("utf-8")).decode("ascii")
        html = html.replace('href="assets/favicon.svg"',
                            'href="data:image/svg+xml;base64,%s"' % b64)

    # ---------- CSS 内联
    html = html.replace('<link rel="stylesheet" href="assets/style.css">',
                        "<style>\n%s\n</style>" % css)

    # ---------- 数据 + 取图映射 + fetch 垫片 + 三段 JS
    inline = [
        "<script>",
        # 不重复存 base64：灯箱直接从页面里已有的 <img data-img> 取同一份 data URI
        "window.__imgFor = function (file) {",
        "  var el = document.querySelector('[data-img=\"' + file + '\"]');",
        "  if (!el) return null;",
        "  var s = el.getAttribute('src') || el.currentSrc || '';",
        "  return s.indexOf('data:') === 0 ? s : null;",
        "};",
        "window.__SITE_DATA = %s;" % json.dumps(site, ensure_ascii=False, separators=(",", ":")),
        "window.__RAG_DATA = %s;" % json.dumps(rag, ensure_ascii=False, separators=(",", ":")),
        # 让站点代码里的 fetch('data/...') 命中内联数据
        "(function () {",
        "  var orig = window.fetch ? window.fetch.bind(window) : null;",
        "  window.fetch = function (u, o) {",
        "    var s = String((u && u.url) || u || '');",
        "    if (s.indexOf('data/site.json') >= 0) {",
        "      return Promise.resolve(new Response(JSON.stringify(window.__SITE_DATA),",
        "        { status: 200, headers: { 'Content-Type': 'application/json' } }));",
        "    }",
        "    if (s.indexOf('data/rag-index.json') >= 0) {",
        "      return Promise.resolve(new Response(JSON.stringify(window.__RAG_DATA),",
        "        { status: 200, headers: { 'Content-Type': 'application/json' } }));",
        "    }",
        "    return orig ? orig(u, o) : Promise.reject(new Error('fetch unavailable'));",
        "  };",
        "})();",
        "</script>",
    ]
    scripts = ("\n".join(inline)
               + "\n<script>\n" + js_search + "\n</script>"
               + "\n<script>\n" + js_app + "\n</script>"
               + "\n<script>\n" + js_ai + "\n</script>")

    html = re.sub(
        r'<script src="assets/search\.js" defer></script>\s*'
        r'<script src="assets/app\.js" defer></script>\s*'
        r'<script src="assets/ai\.js" defer></script>',
        lambda _m: scripts, html)

    # 单文件版在标题里标注一下
    html = html.replace("</title>", " · 单文件版</title>")

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    size = os.path.getsize(out)
    print("wrote %s  (%.2f MB)" % (out, size / 1e6))
    print("  %-34s %-11s %-11s %s" % ("file", "orig", "packed", "KB"))
    for fn, orig, newsize, nbytes in sorted(report, key=lambda r: -r[3]):
        print("  %-34s %-11s %-11s %d" % (fn, "%dx%d" % orig, "%dx%d" % newsize, nbytes // 1024))
    print("  images total: %.2f MB (from %.2f MB)" % (
        total / 1e6,
        sum(os.path.getsize(os.path.join(SITE, "assets", "img", f))
            for f in os.listdir(os.path.join(SITE, "assets", "img"))) / 1e6))
    leftover = re.findall(r'(?:src|href)="(?!#|data:)([^"]+)"', html)
    print("  remaining external refs:", sorted(set(leftover)) or "none")


if __name__ == "__main__":
    main()

