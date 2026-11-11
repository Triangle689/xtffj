// CDP-driven QA for the static site: scroll to sections, open the AI drawer,
// run retrieval checks, and capture PNGs.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync, mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

const CHROME = "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const PORT = 9500 + Math.floor(Math.random() * 200);
const OUT = process.argv[2] || "D:\\A清华\\现代化学创新思维训练\\_qa\\site2";
const BASE = "http://127.0.0.1:4321/";
mkdirSync(OUT, { recursive: true });

const profile = mkdtempSync(path.join(tmpdir(), "qa-chrome-"));
const child = spawn(CHROME, [
  `--remote-debugging-port=${PORT}`,
  `--user-data-dir=${profile}`,
  "--no-first-run", "--no-default-browser-check", "--disable-gpu",
  "--headless=new", "--hide-scrollbars", "--window-size=1440,1000",
  "--disable-blink-features=AutomationControlled",
], { stdio: "ignore" });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function jget(u, opts = {}, tries = 60) {
  let last;
  for (let i = 0; i < tries; i++) {
    try {
      const r = await fetch(u, opts);
      return { status: r.status, json: await r.json() };
    } catch (e) { last = e; await sleep(250); }
  }
  throw new Error("cdp unreachable: " + last?.message);
}

await jget(`http://127.0.0.1:${PORT}/json/version`);
await sleep(400);

let seq = 0;
function mkClient(ws) {
  const pending = new Map();
  ws.addEventListener("message", (ev) => {
    let msg; try { msg = JSON.parse(ev.data); } catch { return; }
    if (msg.id && pending.has(msg.id)) {
      const { resolve, reject } = pending.get(msg.id);
      pending.delete(msg.id);
      msg.error ? reject(new Error(JSON.stringify(msg.error))) : resolve(msg.result);
    }
  });
  return (method, params = {}, tmo = 90000) => new Promise((resolve, reject) => {
    const id = ++seq;
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error("timeout " + method)); } }, tmo);
  });
}

const created = await jget(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" });
const ws = new WebSocket(created.json.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.addEventListener("open", res); ws.addEventListener("error", rej); });
const send = mkClient(ws);

await send("Page.enable");
await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", {
  width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false,
});

async function evalJS(expr, awaitPromise = false) {
  const r = await send("Runtime.evaluate", {
    expression: expr, returnByValue: true, awaitPromise,
  });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 400));
  return r.result.value;
}

async function goto(url) {
  await send("Page.navigate", { url });
  // 等数据加载完成
  for (let i = 0; i < 40; i++) {
    await sleep(250);
    const ok = await evalJS("!!(window.SITE && document.querySelectorAll('#pBody tr').length > 40)").catch(() => false);
    if (ok) break;
  }
  await sleep(700);
}

async function shot(name) {
  const r = await send("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  const file = path.join(OUT, name + ".png");
  writeFileSync(file, Buffer.from(r.data, "base64"));
  console.log("shot", name, Date.now());
}

async function scrollTo(id) {
  const found = await evalJS(`(() => {
    const el = document.getElementById(${JSON.stringify(id)});
    if (!el) return false;
    const h = 64;
    const y = el.getBoundingClientRect().top + window.pageYOffset - h - 20;
    window.scrollTo({ top: y, behavior: 'instant' });
    return true;
  })()`);
  await sleep(650);
  return found;
}

await goto(BASE);
await shot("01-hero");

const ids = [
  ["02-thread", "thread"],
  ["03-phase1", "phase-p1"],
  ["04-phase3", "phase-p3"],
  ["05-catalysts", "catalysts"],
  ["06-gaps", "gaps"],
  ["07-papers", "papers"],
  ["08-figures", "figures"],
  ["09-method", "method"],
];
for (const [name, id] of ids) {
  const ok = await scrollTo(id);
  if (!ok) console.log("MISSING anchor", id);
  await shot(name);
}

// ---- 交互：搜索
await evalJS("window.scrollTo({top:0,behavior:'instant'})");
await sleep(400);
await evalJS(`(() => {
  const q = document.getElementById('q');
  q.focus(); q.value = 'Z-选择性';
  q.dispatchEvent(new Event('input', {bubbles:true}));
  return true;
})()`);
await sleep(600);
await shot("10-search");

const searchCount = await evalJS("document.querySelectorAll('#results .result').length");
console.log("search results:", searchCount);

// ---- 交互：文献筛选
await evalJS(`(() => {
  document.getElementById('q').value=''; document.getElementById('q').blur();
  document.getElementById('results').classList.remove('open');
  document.querySelector('[data-f-type="P"]').click();
  return true;
})()`);
await scrollTo("papers");
await shot("11-filter");
const visible = await evalJS(
  "Array.from(document.querySelectorAll('#pBody tr')).filter(t=>t.style.display!=='none').length");
console.log("visible primary rows:", visible);

// ---- 交互：图鉴
await evalJS("window.openFigure('P1_F1')");
await sleep(600);
await shot("12-lightbox");
await evalJS("document.getElementById('lightbox').classList.remove('open'); document.body.style.overflow='';");

// ---- 交互：文献详情
await evalJS("window.openPaper('P05')");
await sleep(500);
await shot("13-paper-modal");
await evalJS("document.getElementById('paperModal').classList.remove('open'); document.body.style.overflow='';");

// ---- AI 抽屉
await evalJS("document.getElementById('aiOpen').click()");
await sleep(700);
await shot("14-ai-intro");

// ---- 检索门控自测（不调用模型）
const probes = [
  "Chauvin 的机理为什么难验证？",
  "文档给的文献缺了什么？",
  "Grubbs Ⅰ 代和 Ⅱ 代差在哪？",
  "Z-选择性是什么时候做出来的？",
  "哪张图和索烃有关？",
  "今天天气怎么样？",
  "如何做红烧肉？",
];
for (const p of probes) {
  const r = await evalJS(`window.__ai.retrieve(${JSON.stringify(p)})`, true);
  console.log("PROBE", JSON.stringify({
    q: p, ok: r.gate.ok, reason: r.gate.reason,
    top: r.hits[0] ? r.hits[0].title + " s=" + r.hits[0].score + " strong=" + r.hits[0].strong : null,
    n: r.hits.length,
  }));
}

// ---- 模拟一条回答，检查排版（不调用模型）
await evalJS(`(() => {
  const body = document.getElementById('aiBody');
  body.innerHTML = '';
  const mk = (cls, who, html) => {
    const w = document.createElement('div');
    w.className = 'msg ' + cls;
    w.innerHTML = '<div class="who">' + who + '</div><div class="bubble">' + html + '</div>';
    body.appendChild(w); return w;
  };
  mk('user','你','Chauvin 的机理为什么难验证？');
  const b = mk('bot','站内助手','<p><strong>因为提出时金属亚烷基还没有可分离的实例。</strong>Chauvin 在 1971 年提出「金属亚烷基 + 金属杂环丁烷」循环，但当时没有任何可分离的金属亚烷基，只能靠同位素分布间接证明[来源 1]。</p><p>直到 1990 年 Schrock 组拿到可分离的 Mo 亚烷基，机理才由推断变成可检验的分子[来源 2]。</p><div class="sources"><button class="source-btn" type="button" data-anchor="#phase-p1">1 · 1955–1978 现象 → 机理之争</button><button class="source-btn" type="button" data-anchor="#paper-P13">2 · Schrock 等（1990）</button></div>');
  document.getElementById('aiScroll').scrollTop = 0;
  return true;
})()`);
await sleep(300);
await shot("15-ai-answer");

// ---- 设置面板
await evalJS(`document.getElementById('aiCfg').click()`);
await sleep(500);
await shot("16-ai-settings");

// ---- 未命中提示
await evalJS(`document.getElementById('aiBody').innerHTML = '<div class="msg bot"><div class="bubble"><div class="miss"><b>站内暂无相关内容。</b><br>这个问题在站内资料里找不到足够依据，所以没有调用模型（避免它用外部知识作答）。</div></div></div>';`);
await shot("17-ai-nohit");

// ---- 历史面板
await evalJS(`localStorage.setItem('om.ai.history.v1', JSON.stringify([
  {id:'h1', q:'Chauvin 的机理为什么难验证？', a:'…', sources:[{anchor:'#phase-p1',title:'1955–1978'}], ts: Date.now()-3600e3},
  {id:'h2', q:'文档给的文献缺了什么？', a:'…', sources:[], ts: Date.now()-7200e3},
  {id:'h3', q:'Z-选择性是什么时候做出来的？', a:'…', sources:[], ts: Date.now()-86400e3}
])); location.reload();`);
await sleep(2500);
await evalJS("document.getElementById('aiOpen').click()");
await sleep(600);
await evalJS("document.getElementById('aiHist').click()");
await sleep(400);
await shot("18-ai-history");

// 移动端
await send("Emulation.setDeviceMetricsOverride", {
  width: 390, height: 844, deviceScaleFactor: 2, mobile: true,
});
await evalJS("window.scrollTo({top:0,behavior:'instant'})");
await sleep(800);
await shot("19-mobile-hero");
await scrollTo("phase-p1");
await shot("20-mobile-phase");

// 控制台错误
const errors = await evalJS("JSON.stringify(window.__errs || [])");
console.log("page errors:", errors);

ws.close();
try { child.kill(); } catch {}
process.exit(0);

