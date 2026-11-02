import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';

const chromePath = 'C:\\Users\\d\\.agent-browser\\browsers\\chrome-156.0.8078.47\\chrome.exe';
const chrome = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9444',
  '--user-data-dir=C:\\Users\\d\\.agent-browser\\poc-profile',
  '--disable-gpu',
  '--window-size=1280,800',
  'http://127.0.0.1:8766'
]);

await new Promise(r => setTimeout(r, 2000));

const versionData = await new Promise((resolve, reject) => {
  http.get('http://127.0.0.1:9444/json/version', res => {
    let d = '';
    res.on('data', c => d += c);
    res.on('end', () => resolve(JSON.parse(d)));
  }).on('error', reject);
});

const targets = await new Promise((resolve, reject) => {
  http.get('http://127.0.0.1:9444/json/list', res => {
    let d = '';
    res.on('data', c => d += c);
    res.on('end', () => resolve(JSON.parse(d)));
  }).on('error', reject);
});

const pageTarget = targets.find(t => t.type === 'page');
const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);

let idCounter = 1;
const pending = new Map();

ws.onmessage = event => {
  const msg = JSON.parse(event.data);
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

// Enable Page and Runtime
await send('Page.enable');
await send('Runtime.enable');

// Wait for page to load & worker to initialize
await new Promise(r => setTimeout(r, 2000));

// Evaluate page title and search input
const evalTitle = await send('Runtime.evaluate', { expression: 'document.title' });
console.log('Page Title:', evalTitle.result.value);

// Check search input exists
const evalInput = await send('Runtime.evaluate', { expression: 'Boolean(document.getElementById("search"))' });
console.log('Search input exists:', evalInput.result.value);

// Check total word count rendered
const evalWords = await send('Runtime.evaluate', { expression: 'document.querySelectorAll(".word-item").length' });
console.log('Word items rendered on home:', evalWords.result.value);

// Capture screenshot
const screenshot = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync('C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\screenshots\\poc_screenshot.png', Buffer.from(screenshot.data, 'base64'));
console.log('Screenshot saved to poc_screenshot.png');

ws.close();
chrome.kill();
process.exit(0);
