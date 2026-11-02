import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';

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

await send('Page.enable');
await send('Runtime.enable');

console.log('Navigating to http://127.0.0.1:8766/ ...');
await send('Page.navigate', { url: 'http://127.0.0.1:8766/' });

// Wait 2.5s for page and web worker search index to load
await new Promise(r => setTimeout(r, 2500));

const evalTitle = await send('Runtime.evaluate', { expression: 'document.title' });
console.log('Page Title:', evalTitle.result.value);

const evalInput = await send('Runtime.evaluate', { expression: 'Boolean(document.getElementById("search"))' });
console.log('Search input exists:', evalInput.result.value);

const evalWords = await send('Runtime.evaluate', { expression: 'document.querySelectorAll(".word-item").length' });
console.log('Word items rendered on home:', evalWords.result.value);

const screenshot = await send('Page.captureScreenshot', { format: 'png' });
fs.writeFileSync('C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\screenshots\\test_home_navigated.png', Buffer.from(screenshot.data, 'base64'));
console.log('Screenshot saved to test_home_navigated.png');

ws.close();
process.exit(0);
