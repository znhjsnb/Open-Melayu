import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Users\\d\\.agent-browser\\browsers\\chrome-156.0.8078.47\\chrome.exe';
const PORT = 9461;
const SCREENSHOT_DIR = 'C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\screenshots';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

console.log('[*] Launching headless Chrome CDP on port', PORT);
const chrome = spawn(CHROME_PATH, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:\\Users\\d\\.agent-browser\\poc-profile-to2000',
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

async function checkWord(w) {
  await evalJs(`(() => {
    const input = document.getElementById('search');
    input.value = ${JSON.stringify(w)};
    input.dispatchEvent(new Event('input', { bubbles: true }));
  })()`);
  await new Promise(r => setTimeout(r, 500));
  await evalJs(`document.querySelector('.word-item[data-word="${w}"]')?.click()`);
  await new Promise(r => setTimeout(r, 1200));

  return await evalJs(`(() => {
    const title = document.querySelector('.word-title')?.textContent?.trim();
    const audioButtons = document.querySelectorAll('.audio-pill, .pronounce-btn, button[title*="发音"]').length;
    const bubbles = document.querySelectorAll('.chat-bubble').length;
    const speakers = Array.from(document.querySelectorAll('.chat-speaker')).map(e => e.textContent.trim());
    const historicalStory = document.querySelector('.history-story, .story-text, [data-dimension="etymology"]')?.textContent?.length || 0;
    return { title, audioButtons, bubbles, speakers, historicalStory };
  })()`);
}

// Sample words from the expanded range up to 2000
const target1 = 'dewasa'; // ~1331
const sample1 = await checkWord(target1);
console.log(`[CDP] Sample [${target1}]:`, sample1);

const ss1 = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(path.join(SCREENSHOT_DIR, '16_top2000_sample_dewasa.png'), Buffer.from(ss1.data, 'base64'));
console.log('[+] Saved 16_top2000_sample_dewasa.png');

const target2 = 'senyum'; // ~1950
const sample2 = await checkWord(target2);
console.log(`[CDP] Sample [${target2}]:`, sample2);

const ss2 = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync(path.join(SCREENSHOT_DIR, '17_top2000_sample_senyum.png'), Buffer.from(ss2.data, 'base64'));
console.log('[+] Saved 17_top2000_sample_senyum.png');

ws.close();
chrome.kill();

const pass = sample1.bubbles >= 2 && sample2.bubbles >= 2;
console.log('[CDP] TOP 2,000 SAMPLES BROWSER VERIFIED GREEN:', pass);
process.exit(pass ? 0 : 1);
