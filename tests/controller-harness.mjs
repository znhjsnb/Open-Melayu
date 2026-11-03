// Isolated controller contract doubles, adapted from the Open-Lexicon tests.
// Layout values are synthetic. Native rendering is covered by verify_workbench_e2e.mjs.
import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import { normalizeWord, shardFor, DATA_VERSION } from '../app/static/data.js';
import { formatEntryMarkdown, formatEntryAnkiTsv } from '../app/static/entry-format.js';
const source = await readFile(new URL('../app/static/app.js', import.meta.url), 'utf8');
const html = await readFile(new URL('../app/static/index.html', import.meta.url), 'utf8');

const decode = s => String(s).replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
export function controller({ stored = [], hash = '', loadShard = async () => ({ shard: {} }), prepareOffline = async () => ({ completed: 27 }) } = {}) {
  const storage = new Map(stored), timers = new Map(), workers = [], copied = [], registrations = [];
  let document, window, timerId = 0;
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag; this.attributes = new Map(); this.dataset = {}; this.events = new Map(); this.children = [];
      this.style = { setProperty(name, value) { this[name] = String(value); } };
      this.value = ''; this.hidden = false; this.disabled = false; this.scrollTop = 0; this.clientHeight = 300; this.text = '';
      const classes = new Set();
      this.classList = {
        contains: n => classes.has(n), add: (...ns) => ns.forEach(n => classes.add(n)), remove: (...ns) => ns.forEach(n => classes.delete(n)),
        toggle(n, force = !classes.has(n)) { if (force) classes.add(n); else classes.delete(n); return force; },
        values: () => [...classes],
      };
    }
    setAttribute(name, value) {
      this.attributes.set(name, String(value));
      if (name === 'class') { this.classList.remove(...this.classList.values()); this.classList.add(...String(value).split(/\s+/)); }
      if (name === 'id') this.id = value;
      if (name.startsWith('data-')) this.dataset[name.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(value);
      if (name === 'hidden') this.hidden = true;
      if (name === 'disabled') this.disabled = true;
      if (name === 'value') this.value = value;
    }
    getAttribute(name) { return this.attributes.get(name) ?? null; }
    removeAttribute(name) { this.attributes.delete(name); }
    get innerHTML() { return this.html || ''; }
    set innerHTML(value) { this.html = String(value); this.children = []; parse(this.html, this); }
    get textContent() { return this.text + this.children.map(c => c.textContent).join(''); }
    set textContent(value) { this.text = String(value); this.children = []; this.html = this.text; }
    insertAdjacentHTML(where, value) {
      const fragment = new Element(); parse(value, fragment);
      fragment.children.forEach(c => { c.parent = this; });
      if (where === 'afterbegin') { this.children.unshift(...fragment.children); this.html = value + this.html; }
      else { this.children.push(...fragment.children); this.html += value; }
    }
    get scrollHeight() { return this.children.length * 60; }
    get offsetTop() { return this.parent ? this.parent.children.indexOf(this) * 60 : 0; }
    get offsetWidth() { return 300; }
    matches(selector) {
      return selector.split(',').some(s => {
        s = s.trim();
        const attr = s.match(/\[([\w-]+)(?:="([^"]*)")?\]/);
        if (attr && (this.getAttribute(attr[1]) === null || (attr[2] !== undefined && this.getAttribute(attr[1]) !== attr[2]))) return false;
        const id = s.match(/#([\w-]+)/); if (id && this.id !== id[1]) return false;
        const classes = [...s.matchAll(/\.([\w-]+)/g)]; if (!classes.every(c => this.classList.contains(c[1]))) return false;
        const tag = s.match(/^[a-z][\w-]*/i); return !tag || this.tagName === tag[0];
      });
    }
    closest(selector) { return this.matches(selector) ? this : this.parent?.closest(selector) || null; }
    querySelectorAll(selector) {
      const result = [];
      for (const child of this.children) { if (child.matches(selector)) result.push(child); result.push(...child.querySelectorAll(selector)); }
      return result;
    }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    addEventListener(name, fn, options) {
      if (!this.events.has(name)) this.events.set(name, []);
      this.events.get(name).push({ fn, once: options?.once });
    }
    dispatch(name, extra = {}) {
      const event = { type: name, target: this, preventDefault() {}, stopPropagation() { this.stopped = true; }, ...extra };
      this.emit(name, event); return event;
    }
    emit(name, event) {
      this['on' + name]?.(event);
      const handlers = this.events.get(name) || [];
      this.events.set(name, handlers.filter(h => !h.once)); handlers.forEach(h => h.fn(event));
      if (!event.stopped && ['click', 'keydown'].includes(name)) this.parent?.emit(name, event);
    }
    click() { if (!this.disabled) this.dispatch('click'); }
    focus() { document.activeElement = this; }
    blur() { document.activeElement = null; }
    select() {}
    showModal() { this.open = true; }
    close() { this.open = false; this.dispatch('close'); }
    setPointerCapture() {}
    getBoundingClientRect() { return this.rect || { bottom: this.classList.contains('headword-header') ? 200 - document.getElementById('content').scrollTop : 44, width: 340 }; }
    scrollIntoView(options) { this.scrollOptions = options; }
  }
  function parse(markup, root) {
    const stack = [root];
    for (const token of markup.matchAll(/<!--[\s\S]*?-->|<![^>]*>|<\/([\w-]+)\s*>|<([\w-]+)\b([^>]*)>|([^<]+)/g)) {
      if (token[1]) { if (stack.length > 1) stack.pop(); }
      else if (token[2]) {
        const element = new Element(token[2]);
        for (const attr of token[3].matchAll(/([\w-]+)(?:="([^"]*)")?/g)) element.setAttribute(attr[1], decode(attr[2] ?? ''));
        element.parent = stack.at(-1); element.parent.children.push(element);
        if (!['input', 'meta', 'link', 'br', 'hr', 'img', 'path', 'circle'].includes(element.tagName) && !token[3].endsWith('/')) stack.push(element);
      } else if (token[4]) stack.at(-1).text += decode(token[4]);
    }
  }
  document = new Element('document');
  document.innerHTML = html.replace(/<script\b[^>]*>[\s\S]*?<\/script>/g, '');
  document.getElementById = id => document.querySelector('#' + id);
  document.body = document.querySelector('body'); document.documentElement = document.querySelector('html');
  window = new Element('window'); window.innerWidth = 1280; document.parent = window;
  const location = { hash };
  const context = vm.createContext({
    window, document, location, URL, console: { log() {} }, DATA_VERSION, normalizeWord, shardFor, loadShard, prepareOffline,
    formatEntryMarkdown, formatEntryAnkiTsv, cacheStatus: { persistent: true },
    localStorage: { getItem: k => storage.get(k) ?? null, setItem: (k, v) => storage.set(k, v) },
    navigator: { clipboard: { writeText: async text => { copied.push(text); } }, serviceWorker: { register: async (...args) => { registrations.push(args); } } },
    Worker: class { constructor() { this.messages = []; workers.push(this); } postMessage(m) { this.messages.push(m); } reply(data) { this.onmessage({ data }); } },
    setTimeout: fn => { timers.set(++timerId, fn); return timerId; }, clearTimeout: id => timers.delete(id),
  });
  const executable = source.replace(/^import .*;\r?\n/gm, '').replace(/^export \{.*;\r?\n/gm, '').replace('export const PAGE_SIZE', 'const PAGE_SIZE').replaceAll('import.meta.url', "'https://melayu.test/app.js'");
  vm.runInContext(`${executable}\nglobalThis.ui = { state, selectWord, search, loadMore, loadPrevious, jumpPage, renderStudyCard, applyTypography, updatePinnedWord };`, context);
  return { ui: context.ui, element: id => document.getElementById(id), document, window, location, storage, copied, registrations, worker: workers[0],
    flushTimers() { const pending = [...timers.values()]; timers.clear(); pending.forEach(fn => fn()); },
  };
}

export const rows = (start = 0, count = 50) => Array.from({ length: count }, (_, n) => ({ id: start + n + 1, w: `word${start + n}`, s: ['中文'], e: 1, st: 'e', j: 'انق' }));
export function reply(f, result = rows(), total = 250, overrides = {}) {
  f.worker.reply({ type: 'results', requestId: f.ui.state.requestId, results: result, total, offset: f.ui.state.offset, elapsed: 1, subPrefixCounts: [], ...overrides });
}
