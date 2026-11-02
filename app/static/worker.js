import { normalizeWord, INDEX_CACHE } from './data.js';

let entries = [];
let loading = false;
const pageSize = 50;

// Bounded optimal-string-alignment distance for fuzzy matching
function distance(a, b, limit, rows) {
  if (Math.abs(a.length - b.length) > limit) return limit + 1;
  let [before, previous, row] = rows;
  const unreachable = limit + 1;
  previous.fill(unreachable);
  before.fill(unreachable);
  for (let j = 0; j <= Math.min(b.length, limit); j++) previous[j] = j;
  for (let i = 1; i <= a.length; i++) {
    row.fill(unreachable);
    row[0] = Math.min(i, unreachable);
    let minimum = unreachable;
    for (let j = Math.max(1, i - limit); j <= Math.min(b.length, i + limit); j++) {
      row[j] = Math.min(row[j - 1] + 1, previous[j] + 1, previous[j - 1] + (a[i - 1] !== b[j - 1]));
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        row[j] = Math.min(row[j], before[j - 2] + 1);
      }
      minimum = Math.min(minimum, row[j]);
    }
    if (minimum > limit) return limit + 1;
    [before, previous, row] = [previous, row, before];
  }
  return previous[b.length];
}

function search(message) {
  const started = performance.now();
  let rawQuery = String(message.query ?? '').trim().toLowerCase().slice(0, 120);
  
  let rootSearch = false;
  if (rawQuery.startsWith('#root:')) {
    rootSearch = true;
    rawQuery = rawQuery.replace('#root:', '').trim();
  }

  const isChinese = /[\u3400-\u9fff]/.test(rawQuery);
  const isArabic = /[\u0600-\u06ff]/.test(rawQuery);
  const limit = rawQuery.length >= 6 ? 2 : 1;
  const saved = message.bookmarks ? new Set(message.bookmarks) : null;

  const buckets = [[], [], [], []]; // 0: exact/direct, 1: prefix, 2: contains/slang, 3: fuzzy
  const candidates = [];

  for (const entry of entries) {
    // Letter filter
    if (message.letter && !entry.key.startsWith(message.letter)) continue;
    // Tag filter
    if (message.filter === 'enriched' && !entry.e) continue;
    if (message.filter === 'root' && !entry.is_root) continue;
    if (message.filter === 'colloquial' && !entry.a) continue;
    // Bookmark filter
    if (saved && !saved.has(entry.key)) continue;

    let rank = -1;

    if (!rawQuery) {
      rank = 0;
    } else if (rootSearch) {
      // Direct root match
      if (entry.r === rawQuery || entry.key === rawQuery) rank = 0;
    } else if (isChinese) {
      // Chinese meaning search (supports multi-senses, Condition C07)
      if (entry.zh && entry.zh.includes(rawQuery)) rank = 0;
    } else if (isArabic) {
      // Jawi script search
      if (entry.j && entry.j.includes(rawQuery)) rank = 0;
    } else {
      // Latin search
      if (entry.key === rawQuery) {
        rank = 0;
      } else if (entry.a && entry.a.toLowerCase() === rawQuery) {
        // Colloquial shortcut / alias exact match (e.g., tak -> tidak)
        rank = 0;
      } else if (entry.r && entry.r === rawQuery) {
        // Matching root word
        rank = 1;
      } else if (entry.key.startsWith(rawQuery)) {
        rank = 1;
      } else if (entry.key.includes(rawQuery)) {
        rank = 2;
      } else if (entry.a && entry.a.toLowerCase().includes(rawQuery)) {
        rank = 2;
      } else if (rawQuery.length >= 3 && rawQuery.length <= 35 && Math.abs(entry.key.length - rawQuery.length) <= limit) {
        candidates.push(entry);
      }
    }

    if (rank >= 0) buckets[rank].push(entry);
  }

  // Fuzzy matching if direct matches are scarce
  const directCount = buckets[0].length + buckets[1].length + buckets[2].length;
  if (directCount < 30 && !buckets[0].length && !isChinese && !isArabic && rawQuery.length >= 3) {
    const rows = [new Uint8Array(40), new Uint8Array(40), new Uint8Array(40)];
    for (const entry of candidates) {
      if (Math.abs(entry.key.length - rawQuery.length) > limit) continue;
      const edits = distance(rawQuery, entry.key, limit, rows);
      if (edits <= limit) buckets[3].push(entry);
    }
  }

  // Sort within buckets
  const byRank = (a, b) => a.id - b.id;
  const byAlpha = (a, b) => a.key.localeCompare(b.key, 'ms');
  const sortFn = message.sort === 'alpha' ? byAlpha : byRank;
  buckets.forEach(b => b.sort(sortFn));

  const matches = buckets.flat();
  const offset = Math.max(0, Number(message.offset) || 0);
  const page = matches.slice(offset, offset + pageSize);

  postMessage({
    type: 'results',
    requestId: message.requestId,
    results: page,
    total: matches.length,
    offset,
    elapsed: Math.round(performance.now() - started)
  });
}

async function initialize() {
  if (loading) return;
  loading = true;
  const started = performance.now();
  const url = new URL('./data/search_index.json', import.meta.url);

  try {
    let response;
    let cache;
    try {
      cache = await caches.open(INDEX_CACHE);
      response = await cache.match(url);
    } catch {
      // Memory only fallback
    }

    if (!response) {
      response = await fetch(url);
      if (response.ok && cache) {
        cache.put(url, response.clone()).catch(() => {});
      }
    }

    if (!response.ok) throw new Error(`索引载入失败（HTTP ${response.status}）`);
    const data = await response.json();
    if (!Array.isArray(data)) throw new Error('索引格式不合法');

    // Normalize entries
    entries = data.map(item => ({
      id: item.id,
      w: item.w,
      key: normalizeWord(item.w),
      j: item.j || '',
      p: item.p || '',
      r: item.r ? normalizeWord(item.r) : '',
      a: item.a || '',
      zh: item.s ? item.s.join(' ') : '',
      s: item.s || [],
      e: Boolean(item.e),
      st: item.st || 's',
      is_root: !item.r || item.r === item.w
    }));

    postMessage({
      type: 'ready',
      count: entries.length,
      elapsed: Math.round(performance.now() - started)
    });
  } catch (err) {
    postMessage({ type: 'error', message: err.message });
  } finally {
    loading = false;
  }
}

addEventListener('message', event => {
  const message = event.data;
  if (!message) return;
  if (message.type === 'init') {
    initialize();
  } else if (message.type === 'search') {
    search(message);
  }
});
