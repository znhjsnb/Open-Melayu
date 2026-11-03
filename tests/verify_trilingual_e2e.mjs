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
await new Promise(r => setTimeout(r, 1500));
await send('Runtime.evaluate', {
  expression: `(async () => {
    if (window.indexedDB && window.indexedDB.databases) {
      const dbs = await window.indexedDB.databases();
      for (const db of dbs) {
        window.indexedDB.deleteDatabase(db.name);
      }
    }
    location.reload();
  })()`,
  awaitPromise: true
});
await new Promise(r => setTimeout(r, 2500));

async function testWord(word, screenshotName, expectedStatus = 'official') {
  console.log(`\n[*] Testing trilingual word rendering for: #${word} (expectedStatus=${expectedStatus})`);
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
  await new Promise(r => setTimeout(r, 1500));

  const evalResult = await send('Runtime.evaluate', {
    expression: `(() => {
      const title = document.querySelector('.word-title')?.textContent?.trim();
      const jawi = document.querySelector('.jawi-title')?.textContent?.trim();
      const senseEn = document.querySelector('.sense-en-sub')?.textContent?.trim();
      const collocEn = document.querySelector('.colloc-en')?.textContent?.trim();
      const bubbleEn = document.querySelector('.bubble-en')?.textContent?.trim();
      const quoteLabel = document.querySelector('.quote-label')?.textContent?.trim();
      const statusBadge = document.querySelector('.status-badge')?.textContent?.trim();
      const pendingNotice = document.querySelector('.pending-notice')?.textContent?.trim();
      const bubbles = document.querySelectorAll('.chat-bubble').length;
      const collocs = document.querySelectorAll('.collocation-item').length;
      return { title, jawi, senseEn, collocEn, bubbleEn, quoteLabel, statusBadge, pendingNotice, bubbles, collocs };
    })()`,
    returnByValue: true
  });

  const data = evalResult.result.value;
  console.log(`[+] Results for #${word}:`, JSON.stringify(data, null, 2));

  if (expectedStatus === 'missing_source') {
    if (!data.pendingNotice) {
      throw new Error(`Expected .pending-notice banner on missing_source word #${word}, got none`);
    }
  } else {
    if (!data.senseEn) throw new Error(`sense-en-sub missing on #${word}`);
    if (!data.collocEn) throw new Error(`colloc-en missing on #${word}`);
    if (!data.bubbleEn) throw new Error(`bubble-en missing on #${word}`);
    if (data.bubbles < 2) throw new Error(`Expected >= 2 chat bubbles on #${word}, got ${data.bubbles}`);
    if (data.collocs < 2) throw new Error(`Expected >= 2 collocations on #${word}, got ${data.collocs}`);

    if (expectedStatus === 'official' && data.quoteLabel !== 'DBP 原文:') {
      throw new Error(`Expected quoteLabel 'DBP 原文:' on official word #${word}, got '${data.quoteLabel}'`);
    }
    if (expectedStatus === 'root_derived' && data.quoteLabel !== '马来语释义 (基于 DBP 词根推导):') {
      throw new Error(`Expected quoteLabel '马来语释义 (基于 DBP 词根推导):' on root_derived word #${word}, got '${data.quoteLabel}'`);
    }
    if (expectedStatus === 'corpus_usage' && data.quoteLabel !== '马来语释义 (字幕高频语料用法):') {
      throw new Error(`Expected quoteLabel '马来语释义 (字幕高频语料用法):' on corpus_usage word #${word}, got '${data.quoteLabel}'`);
    }
  }

  const ss = await send('Page.captureScreenshot', { format: 'png' });
  const ssPath = path.join(SCREENSHOT_DIR, screenshotName);
  fs.writeFileSync(ssPath, Buffer.from(ss.data, 'base64'));
  console.log(`[+] Screenshot saved to ${ssPath} (${fs.statSync(ssPath).size} bytes)`);
}

let exitCode = 0;
try {
  await testWord('asli', '21_top3000_sample_asli.png', 'official');
  await testWord('memasak', '22_top3000_sample_memasak.png', 'official');
  await testWord('tajam', '23_top3000_sample_tajam.png', 'official');
  await testWord('anakku', '24_root_derived_anakku.png', 'root_derived');
  await testWord('water', '25_corpus_usage_water.png', 'corpus_usage');
  await testWord('milan', '26_corpus_usage_milan.png', 'corpus_usage');
  await testWord('head', '27_salvaged_head.png', 'corpus_usage');
  await testWord('jaikant', '28_missing_source_jaikant.png', 'missing_source');
  console.log('\n[★] ALL CDP TRILINGUAL SCREENSHOTS & PROVENANCE ASSERTIONS VERIFIED!');
} catch (err) {
  console.error('\n[!] CDP E2E Assertion Failed:', err);
  exitCode = 1;
} finally {
  ws.close();
  chrome.kill();
  process.exit(exitCode);
}
