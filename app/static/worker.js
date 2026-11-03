import { normalizeWord, loadSearchIndex } from './data.js';

let entries = [];
let loading = false;
const pageSize = 50;

// Bounded optimal-string-alignment distance for fuzzy matching
export function distance(a, b, limit, rows = Array.from({ length: 3 }, () => new Uint16Array(b.length + 1))) {
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

export function hydrateIndex(data) {
  return data.map(item => ({
    ...item,
    key: normalizeWord(item.w),
    _wLower: normalizeWord(item.w),
    _rLower: normalizeWord(item.r),
    j: item.j || '', a: item.a || '', s: item.s || [],
    zh: (item.s || []).join(' '),
  }));
}

export function searchEntries(entries, message = {}) {

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
  const prefixes = new Map();
  const countPrefixes = /^[a-z]$/.test(message.letter || '') && !rawQuery;

  for (const entry of entries) {
    // Letter filter
    if (message.letter && !entry.key.startsWith(message.letter)) continue;
    // Tag filter
    if (message.filter === 'enriched' && !(entry.st === 'e' || entry.e === 1)) continue;
    if (message.filter === 'root' && !(entry._rLower && entry._rLower === entry._wLower)) continue;
    if (message.filter === 'colloquial' && !Boolean(entry.a && entry.a.trim())) continue;
    if (message.filter === 'jawi' && !Boolean(entry.j && entry.j.trim())) continue;
    if (message.filter === 'source' && entry.st !== 's') continue;
    if (message.filter === 'missing' && entry.st !== 'm') continue;
    // Bookmark filter
    if (saved && !saved.has(entry.key)) continue;

    if (countPrefixes) {
      const prefix = entry.key.slice(0, 2);
      if (/^[a-z]{2}$/.test(prefix)) prefixes.set(prefix, (prefixes.get(prefix) || 0) + 1);
      if (message.subPrefix && !entry.key.startsWith(message.subPrefix)) continue;
    }
    let rank = -1;

    if (!rawQuery) {
      rank = 0;
    } else if (rootSearch) {
      // Direct root match
      if (entry._rLower === rawQuery || entry.key === rawQuery) rank = 0;
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
      } else if (entry.r && entry._rLower === rawQuery) {
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

  const byRank = (a, b) => a.id - b.id;
  const byAlpha = (a, b) => a.key.localeCompare(b.key, 'ms') || byRank(a, b);
  const comparators = {
    rank: byRank,
    alpha: byAlpha,
    'alpha-desc': (a, b) => b.key.localeCompare(a.key, 'ms') || byRank(a, b),
    senses: (a, b) => (b.s?.length || 0) - (a.s?.length || 0) || byRank(a, b),
  };
  // Relevance tracks apply to rank; explicit sorts order the entire matching pool.
  buckets.forEach(bucket => bucket.sort(byRank));
  const matches = buckets.flat();
  if (message.sort && message.sort !== 'rank') matches.sort(comparators[message.sort] || byRank);
  const targetIndex = message.targetWord ? matches.findIndex(e => e.key === normalizeWord(message.targetWord)) : -1;
  const requested = message.offset != null ? Number(message.offset) : (Math.max(1, Number(message.page) || 1) - 1) * pageSize;
  const requestedOffset = Math.max(0, Math.floor(Number.isFinite(requested) ? requested : 0));
  const lastPageOffset = Math.max(0, Math.floor((matches.length - 1) / pageSize) * pageSize);
  const offset = targetIndex >= 0 ? Math.floor(targetIndex / pageSize) * pageSize :
    requestedOffset >= matches.length ? lastPageOffset : requestedOffset;
  return {
    type: 'results', requestId: message.requestId,
    results: matches.slice(offset, offset + pageSize),
    total: matches.length, offset, page: Math.floor(offset / pageSize) + 1,
    targetIndex,
    subPrefixCounts: [...prefixes].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).slice(0, 18),
    elapsed: Math.round(performance.now() - started),
  };
}

async function initialize() {
  if (loading) return;
  loading = true;
  const started = performance.now();
  try {
    const data = await loadSearchIndex();

    entries = hydrateIndex(data);

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

if (typeof self !== 'undefined' && typeof document === 'undefined') self.addEventListener('message', event => {
  const message = event.data;
  if (!message) return;
  if (message.type === 'init') {
    initialize();
  } else if (message.type === 'search') {
    postMessage(searchEntries(entries, message));
  }
});
