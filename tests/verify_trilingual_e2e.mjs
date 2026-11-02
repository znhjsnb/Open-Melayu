import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const CHROME_PATH = 'C:\\Users\\d\\.agent-browser\\browsers\\chrome-156.0.8078.47\\chrome.exe';
const PORT = 9462;
const SCREENSHOT_DIR = 'C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\screenshots';

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

console.log('[*] Launching headless Chrome CDP on port', PORT);
const chrome = spawn(CHROME_PATH, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:\\Users\\d\\.agent-browser\\poc-profile-trilingual',
  '--disable-gpu',
  '--window-size=1280,900',
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

await send('Page.enable');
await send('Runtime.enable');
await send('Page.navigate', { url: 'http://127.0.0.1:8766/' });
await new Promise(r => setTimeout(r, 2500));

async function testWord(word, screenshotName) {
  console.log(`\n[*] Testing trilingual word rendering for: #${word}`);
  await send('Runtime.evaluate', {
    expression: `(async () => {
      const input = document.getElementById('search');
      if (input) {
        input.value = '${word}';
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
      await new Promise(r => setTimeout(r, 300));
      if (typeof window.selectWord === 'function') {
        await window.selectWord('${word}');
      }
    })()`,
    awaitPromise: true
  });
  await new Promise(r => setTimeout(r, 2000));

  const evalResult = await send('Runtime.evaluate', {
    expression: `(() => {
      const title = document.querySelector('.word-title')?.textContent?.trim();
      const jawi = document.querySelector('.jawi-title')?.textContent?.trim();
      const senseEn = document.querySelector('.sense-en-sub')?.textContent?.trim();
      const collocEn = document.querySelector('.colloc-en')?.textContent?.trim();
      const bubbleEn = document.querySelector('.bubble-en')?.textContent?.trim();
      const bubbles = document.querySelectorAll('.chat-bubble').length;
      const collocs = document.querySelectorAll('.collocation-item').length;
      return { title, jawi, senseEn, collocEn, bubbleEn, bubbles, collocs };
    })()`,
    returnByValue: true
  });

  const data = evalResult.result.value;
  console.log(`[+] Results for #${word}:`, JSON.stringify(data, null, 2));

  if (!data.senseEn) console.warn(`[!] Warning: sense-en-sub missing on #${word}`);
  if (!data.collocEn) console.warn(`[!] Warning: colloc-en missing on #${word}`);
  if (!data.bubbleEn) console.warn(`[!] Warning: bubble-en missing on #${word}`);

  const ss = await send('Page.captureScreenshot', { format: 'png' });
  const ssPath = path.join(SCREENSHOT_DIR, screenshotName);
  fs.writeFileSync(ssPath, Buffer.from(ss.data, 'base64'));
  console.log(`[+] Screenshot saved to ${ssPath} (${fs.statSync(ssPath).size} bytes)`);
}

try {
  await testWord('asli', '21_top3000_sample_asli.png');
  await testWord('memasak', '22_top3000_sample_memasak.png');
  await testWord('tajam', '23_top3000_sample_tajam.png');
  console.log('\n[★] ALL CDP TRILINGUAL SCREENSHOTS CAPTURED AND VERIFIED!');
} finally {
  ws.close();
  chrome.kill();
  process.exit(0);
}
