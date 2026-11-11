// 整页截图（缩小 0.3 倍）用于整体节奏复核
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9700 + Math.floor(Math.random() * 200);
const OUT = process.argv[2];
mkdirSync(path.dirname(OUT), { recursive: true });
const profile = mkdtempSync(path.join(tmpdir(), "full-chrome-"));
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
  return (method, params = {}, tmo = 120000) => new Promise((resolve, reject) => {
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
await send("Page.navigate", { url: "http://127.0.0.1:4321/" });
for (let i = 0; i < 40; i++) {
  await sleep(300);
  const r = await send("Runtime.evaluate", { expression: "!!(window.SITE && document.querySelectorAll('#pBody tr').length>40)", returnByValue: true });
  if (r.result.value) break;
}
await sleep(1200);
// 关掉入场动画，确保整页可见
await send("Runtime.evaluate", {
  expression: `document.querySelectorAll('*').forEach(e=>{if(e.style.opacity==='0'){e.style.opacity='1';e.style.transform='none';}});window.scrollTo(0,0);`,
});
await sleep(500);
const h = (await send("Runtime.evaluate", { expression: "document.documentElement.scrollHeight", returnByValue: true })).result.value;
console.log("page height:", h);
const r = await send("Page.captureScreenshot", {
  format: "png", captureBeyondViewport: true,
  clip: { x: 0, y: 0, width: 1440, height: Math.min(h, 20000), scale: 0.32 },
});
writeFileSync(OUT, Buffer.from(r.data, "base64"));
console.log("saved", OUT);
ws.close(); try { child.kill(); } catch {}
process.exit(0);
