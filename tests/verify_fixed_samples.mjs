import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Users\\d\\.agent-browser\\browsers\\chrome-156.0.8078.47\\chrome.exe';
const PORT = 9456;
const SCREENSHOT_DIR = 'C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\screenshots';

const chrome = spawn(CHROME_PATH, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:\\Users\\d\\.agent-browser\\poc-profile-verify6',
  '--disable-gpu',
  '--window-size=1280,800',
  'about:blank'
]);

await new Promise(r => setTimeout(r, 1600));

const targets = await new Promise((resolve, reject) => {
  http.get(`http://127.0.0.1:${PORT}/json/list`, res => {
    let d = '';
    res.on('data', c => d += c);
    res.on('end', () => resolve(JSON.parse(d)));
  }).on('error', reject);
});

const pageTarget = targets.find(t => t.type === 'page');
const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

let idCounter = 1;
const pending = new Map();
let loadFired = false;

ws.onmessage = event => {
  const msg = JSON.parse(event.data);
  if (msg.method === 'Page.loadEventFired') loadFired = true;
  if (msg.id && pending.has(msg.id)) {
    const { resolve, reject } = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) reject(msg.error);
    else resolve(msg.result);
  }
};

await new Promise(r => ws.onopen = r);

function send(method, params = {}) {
  const id = idCounter++;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}

async function evalJs(expr) {
  const res = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  return res.result?.value;
}

await send('Page.enable');
await send('Runtime.enable');
await send('Page.navigate', { url: 'http://127.0.0.1:8766/' });

while (!loadFired) {
  await new Promise(r => setTimeout(r, 100));
}
await new Promise(r => setTimeout(r, 2000));

async function checkWord(w) {
  await evalJs(`(() => {
    const input = document.getElementById('search');
    input.value = ${JSON.stringify(w)};
    input.dispatchEvent(new Event('input', { bubbles: true }));
  })()`);
  await new Promise(r => setTimeout(r, 400));
  await evalJs(`(() => {
    const item = document.querySelector('.word-item[data-word="${w}"]');
    if (item) item.click();
  })()`);
  await new Promise(r => setTimeout(r, 800));

  return await evalJs(`(() => {
    const head = document.querySelector('.word-title')?.textContent;
    const jawi = document.querySelector('.jawi-title')?.textContent || document.querySelector('.jawi-pending')?.textContent;
    const msDef = document.querySelector('.sense-ms-quote')?.textContent || '';
    return { head, jawi, msDef: msDef.trim() };
  })()`);
}

const results = {};
for (const word of ['bimbang', 'ok', 'panggilan', 'joe', 'me', 'oliver']) {
  results[word] = await checkWord(word);
  console.log(`Verified [${word}]:`, results[word]);
}

// Screenshot bimbang as evidence of newly recovered Jawi
const ss = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(path.join(SCREENSHOT_DIR, '10_sample_bimbang_recovered_jawi.png'), Buffer.from(ss.data, 'base64'));
console.log('Saved 10_sample_bimbang_recovered_jawi.png');

ws.close();
chrome.kill();

const okPass = results['bimbang'].jawi === 'بيمبڠ' &&
               results['ok'].jawi === 'اءوق' &&
               results['panggilan'].jawi === '\u06a4\u06a0\u06af\u064a\u0644\u0646' &&
               results['joe'].msDef.includes('DBP 官方词典未单独收录') &&
               results['me'].msDef.includes('DBP 官方词典未单独收录') &&
               results['oliver'].msDef.includes('DBP 官方词典未单独收录');

console.log('ALL 6 DEFECTS VERIFIED GREEN:', okPass);
process.exit(okPass ? 0 : 1);
