import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, mkdtemp, rm, mkdir } from 'node:fs/promises';
import { resolve, extname, join } from 'node:path';

export const pause = ms => new Promise(r => setTimeout(r, ms));
export async function until(fn, timeout = 12000) {
  const start = Date.now();
  let last;
  while (Date.now() - start < timeout) {
    try { last = await fn(); if (last) return last; } catch (error) { last = error; }
    await pause(40);
  }
  throw new Error(`Browser condition timed out: ${last}`);
}

export async function openBrowser({ fixture = null } = {}) {
  const staticRoot = resolve('app/static');
  const server = createServer(async (req, res) => {
    try {
      const pathname = new URL(req.url, 'http://localhost').pathname;
      if (fixture && pathname.startsWith('/data/')) {
        const value = pathname.endsWith('search_index.json') ? fixture.index : fixture.shards[pathname.split('/').pop().replace('.json', '')] || {};
        if (pathname.endsWith('/b.json')) await pause(250);
        res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(value)); return;
      }
      const file = resolve(staticRoot, '.' + (pathname === '/' ? '/index.html' : pathname));
      if (!file.startsWith(staticRoot + '\\') && !file.startsWith(staticRoot + '/')) { res.writeHead(403).end(); return; }
      res.setHeader('Content-Type', ({ '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json' })[extname(file)] || 'application/octet-stream');
      res.end(await readFile(file));
    } catch { res.writeHead(404).end(); }
  });
  await new Promise(r => server.listen(0, '127.0.0.1', r));
  const origin = `http://127.0.0.1:${server.address().port}`;
  await mkdir(resolve('.tmp'), { recursive: true });
  const profile = await mkdtemp(resolve('.tmp/browser-'));
  const chromePath = process.env.CHROME_PATH || 'C:/Users/d/.agent-browser/browsers/chrome-156.0.8078.47/chrome.exe';
  const chrome = spawn(chromePath, ['--headless=new', '--remote-debugging-port=0', `--user-data-dir=${profile}`, '--disable-gpu', '--no-first-run', '--window-size=1440,900', 'about:blank'], { windowsHide: true, stdio: 'ignore' });
  let launchError;
  chrome.on('error', error => { launchError = error; });
  let ws;
  const pending = new Map();
  try {
    let port;
    const started = Date.now();
    while (!port) {
      if (launchError) throw launchError;
      if (chrome.exitCode !== null) throw Error(`Chrome exited before CDP startup (${chrome.exitCode})`);
      if (Date.now() - started > 12000) throw Error('Chrome CDP startup timed out');
      try { port = (await readFile(join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]; }
      catch (error) { if (error.code !== 'ENOENT') throw error; }
      if (!port) await pause(40);
    }
    const targets = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
    ws = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    let id = 0;
    const errors = [];
    ws.onmessage = event => {
      const message = JSON.parse(event.data);
      if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails);
      if (!pending.has(message.id)) return;
      const { resolve, reject } = pending.get(message.id); pending.delete(message.id);
      message.error ? reject(Error(JSON.stringify(message.error))) : resolve(message.result);
    };
    const send = (method, params = {}) => new Promise((resolve, reject) => {
      const requestId = ++id;
      const timer = setTimeout(() => { pending.delete(requestId); reject(Error(`CDP timeout: ${method}`)); }, 20000);
      pending.set(requestId, { resolve: v => { clearTimeout(timer); resolve(v); }, reject: e => { clearTimeout(timer); reject(e); } });
      ws.send(JSON.stringify({ id: requestId, method, params }));
    });
    const evaluate = async expression => {
      const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true, userGesture: true });
      if (result.exceptionDetails) throw Error(JSON.stringify(result.exceptionDetails));
      return result.result?.value;
    };
    await send('Page.enable'); await send('Runtime.enable');
    return { origin, send, evaluate, errors, async close() {
      ws.close(); chrome.kill();
      await new Promise(r => chrome.exitCode !== null ? r() : chrome.once('exit', r));
      await new Promise(r => server.close(r));
      // Remove only the temporary profile created by this helper, after Chrome exits.
      await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
    } };
  } catch (error) {
    ws?.close(); chrome.kill(); server.close(); throw error;
  }
}
