import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Users\\d\\.agent-browser\\browsers\\chrome-156.0.8078.47\\chrome.exe';
const PORT = 9458;
const SCREENSHOT_DIR = 'C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\screenshots';

const chrome = spawn(CHROME_PATH, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:\\Users\\d\\.agent-browser\\poc-profile-b4',
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

while (!loadFired) await new Promise(r => setTimeout(r, 100));
await new Promise(r => setTimeout(r, 2000));

// 1. Check 'tapi' (Batch 4 upgraded with 3 messages)
await evalJs(`(() => {
  const input = document.getElementById('search');
  input.value = 'tapi';
  input.dispatchEvent(new Event('input', { bubbles: true }));
})()`);
await new Promise(r => setTimeout(r, 400));
await evalJs(`document.querySelector('.word-item[data-word="tapi"]')?.click()`);
await new Promise(r => setTimeout(r, 1000));

const tapiData = await evalJs(`(() => {
  const title = document.querySelector('.word-title')?.textContent;
  const bubbles = document.querySelectorAll('.chat-bubble').length;
  const speakers = Array.from(document.querySelectorAll('.chat-speaker')).map(e => e.textContent.trim());
  return { title, bubbles, speakers };
})()`);

console.log('Verified tapi:', tapiData);

const ssTapi = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(path.join(SCREENSHOT_DIR, '11_sample_tapi_codex_dialogue.png'), Buffer.from(ssTapi.data, 'base64'));
console.log('Saved 11_sample_tapi_codex_dialogue.png');

// 2. Check 'akhirnya' (linked root Jawi)
await evalJs(`(() => {
  const input = document.getElementById('search');
  input.value = 'akhirnya';
  input.dispatchEvent(new Event('input', { bubbles: true }));
})()`);
await new Promise(r => setTimeout(r, 400));
await evalJs(`document.querySelector('.word-item[data-word="akhirnya"]')?.click()`);
await new Promise(r => setTimeout(r, 1000));

const akhirnyaData = await evalJs(`(() => {
  const title = document.querySelector('.word-title')?.textContent;
  const morphNote = document.querySelector('.morph-note')?.textContent || '';
  return { title, hasRootJawi: morphNote.includes('اخير') };
})()`);

console.log('Verified akhirnya:', akhirnyaData);

const ssAkhirnya = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(path.join(SCREENSHOT_DIR, '12_sample_akhirnya_root_jawi.png'), Buffer.from(ssAkhirnya.data, 'base64'));
console.log('Saved 12_sample_akhirnya_root_jawi.png');

ws.close();
chrome.kill();

const pass = tapiData.title === 'tapi' && tapiData.bubbles >= 2 && akhirnyaData.hasRootJawi;
console.log('BATCH 4 & ROOT JAWI VERIFIED GREEN:', pass);
process.exit(pass ? 0 : 1);
