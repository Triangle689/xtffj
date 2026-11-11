// 子路径部署验证：把站放在 /site/ 下加载，检查图、数据、搜索、灯箱是否正常
import { spawn } from "node:child_process";
import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9800 + Math.floor(Math.random() * 100);
const URL = process.argv[2].startsWith("file:") ? process.argv[2] : (process.argv[2].startsWith("http") ? process.argv[2] : pathToFileURL(process.argv[2]).href);
const profile = mkdtempSync(path.join(tmpdir(), "sub-chrome-"));
const child = spawn(CHROME, [
  `--remote-debugging-port=${PORT}`, `--user-data-dir=${profile}`,
  "--headless=new", "--hide-scrollbars", "--disable-gpu",
  "--window-size=1440,1000", "--no-first-run",
], { stdio: "ignore" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function jget(u, o = {}, t = 60) {
  let last;
  for (let i = 0; i < t; i++) {
    try { const r = await fetch(u, o); return { json: await r.json() }; } catch (e) { last = e; await sleep(250); }
  }
  throw new Error("cdp: " + last?.message);
}
await jget(`http://127.0.0.1:${PORT}/json/version`);
await sleep(400);
let seq = 0;
function mk(ws) {
  const p = new Map();
  ws.addEventListener("message", (ev) => {
    let m; try { m = JSON.parse(ev.data); } catch { return; }
    if (m.id && p.has(m.id)) { const { resolve, reject } = p.get(m.id); p.delete(m.id); m.error ? reject(new Error(JSON.stringify(m.error))) : resolve(m.result); }
  });
  return (method, params = {}, tmo = 90000) => new Promise((resolve, reject) => {
    const id = ++seq; p.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (p.has(id)) { p.delete(id); reject(new Error("t " + method)); } }, tmo);
  });
}
const c = await jget(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" });
const ws = new WebSocket(c.json.webSocketDebuggerUrl);
await new Promise((r, j) => { ws.addEventListener("open", r); ws.addEventListener("error", j); });
const send = mk(ws);
await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });

const errs = [];
ws.addEventListener("message", (ev) => {
  let m; try { m = JSON.parse(ev.data); } catch { return; }
  if (m.method === "Log.entryAdded" && m.params.entry.level === "error") errs.push(m.params.entry.text);
  if (m.method === "Runtime.exceptionThrown") errs.push(m.params.exceptionDetails.text);
});
await send("Log.enable");

await send("Page.navigate", { url: URL });
for (let i = 0; i < 40; i++) {
  await sleep(300);
  const r = await send("Runtime.evaluate", { expression: "!!(window.SITE && document.querySelectorAll('#pBody tr').length>40)", returnByValue: true });
  if (r.result.value) break;
}
await sleep(1000);

const probe = await send("Runtime.evaluate", {
  returnByValue: true, awaitPromise: true,
  expression: `(async () => {
    const imgs = Array.from(document.images);
    // 触发懒加载：滚到底再回来
    window.scrollTo(0, document.body.scrollHeight); await new Promise(r=>setTimeout(r,800));
    window.scrollTo(0, 0); await new Promise(r=>setTimeout(r,600));
    const broken = imgs.filter(i => i.complete && i.naturalWidth === 0).map(i => i.getAttribute('src'));
    const searchRes = (() => {
      const q = document.getElementById('q');
      q.value = 'Grubbs'; q.dispatchEvent(new Event('input', {bubbles:true}));
      return document.querySelectorAll('#results .result').length;
    })();
    await new Promise(r=>setTimeout(r,300));
    const ai = await window.__ai.retrieve('Z-选择性是什么时候做出来的？');
    return {
      rows: document.querySelectorAll('#pBody tr').length,
      figs: document.querySelectorAll('.fig, .cat').length,
      imgTotal: imgs.length,
      imgBrokenCount: broken.length,
      searchRes,
      aiOk: ai.gate.ok,
      aiTop: ai.hits[0] ? ai.hits[0].title : null,
      base: location.href
    };
  })()`,
});
console.log(JSON.stringify(probe.result.value, null, 1));
console.log("console errors:", errs.length ? errs : "none");

// 再确认灯箱里的图能加载
await send("Runtime.evaluate", { expression: "window.openFigure('P3_F12')" });
await sleep(700);
const lb = await send("Runtime.evaluate", {
  returnByValue: true,
  expression: "(() => { const i = document.getElementById('lbImg'); const s = i.getAttribute('src')||''; return {kind: s.slice(0,22), len: s.length, w: i.naturalWidth, ok: i.complete && i.naturalWidth>0}; })()",
});
console.log("lightbox:", JSON.stringify(lb.result.value));

ws.close(); try { child.kill(); } catch {}
process.exit(0);



