import http from 'http';
import { spawn } from 'child_process';

const chromePath = 'C:\\Users\\d\\.agent-browser\\browsers\\chrome-156.0.8078.47\\chrome.exe';
const chrome = spawn(chromePath, [
  '--headless=new',
  '--remote-debugging-port=9452',
  '--user-data-dir=C:\\Users\\d\\.agent-browser\\poc-profile-debug3',
  '--disable-gpu',
  '--window-size=1280,800',
  'about:blank'
]);

await new Promise(r => setTimeout(r, 1500));

const targets = await new Promise((resolve, reject) => {
  http.get('http://127.0.0.1:9452/json/list', res => {
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
  if (msg.method === 'Console.messageAdded') {
    console.log('[BROWSER CONSOLE]', msg.params.message.text);
  }
  if (msg.method === 'Runtime.consoleAPICalled') {
    console.log('[BROWSER LOG]', ...msg.params.args.map(a => a.value || a.description));
  }
  if (msg.method === 'Runtime.exceptionThrown') {
    console.log('[BROWSER EXCEPTION]', msg.params.exceptionDetails);
  }
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
await send('Console.enable');

await send('Page.navigate', { url: 'http://127.0.0.1:8766/' });

await new Promise(r => setTimeout(r, 3500));

const title = await send('Runtime.evaluate', { expression: 'document.title' });
const items = await send('Runtime.evaluate', { expression: 'document.querySelectorAll(".word-item").length' });
const conn = await send('Runtime.evaluate', { expression: 'document.getElementById("connection")?.innerText' });

console.log('RESULT -> Title:', title.result.value, '| Items:', items.result.value, '| Conn:', conn.result.value);

ws.close();
chrome.kill();
process.exit(0);
