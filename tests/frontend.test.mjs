import test from 'node:test';
import assert from 'node:assert/strict';
import { hydrateIndex, searchEntries, distance } from '../app/static/worker.js';
import { DATA_VERSION, SHELL_CACHE, SHARD_KEYS, shardKeyForWord, loadSearchIndex } from '../app/static/data.js';
import { readFile } from 'node:fs/promises';
import { formatEntryMarkdown, formatEntryAnkiTsv, quoteLabel } from '../app/static/entry-format.js';

const index = hydrateIndex([
  { id: 6, w: 'Anak', r: 'ANAK', j: 'انق', a: ' ', e: 1, s: ['孩子', '小孩'] },
  { id: 2, w: 'anakku', r: 'anak', st: 'e', s: ['我的孩子'] },
  { id: 4, w: 'ajar', r: 'ajar', st: 's', j: 'اجر', s: ['教'] },
  { id: 3, w: 'belajar', r: 'ajar', st: 'e', a: 'blajar', s: ['学习'] },
  { id: 1, w: 'tidak', r: '', st: 'e', a: 'tak', s: ['不'] },
  { id: 5, w: 'ann', r: null, st: 'm', j: ' ', s: [] },
]);
const words = options => searchEntries(index, options).results.map(e => e.w);

test('immutable data build and independent shell version / shard mapping', () => {
  assert.equal(DATA_VERSION, 'om-20261103-v9756');
  assert.equal(SHELL_CACHE, 'open-melayu-shell-v2');
  assert.equal(SHARD_KEYS.length, 27);
  assert.equal(shardKeyForWord(' Saya '), 's');
  assert.equal(shardKeyForWord('انق'), 'other');
});
test('multi-track exact, prefix, contains, Chinese, Jawi, root, alias and OSA transposition', () => {
  assert.equal(words({ query: 'anak' })[0], 'Anak');
  assert.deepEqual(words({ query: '孩子' }), ['anakku', 'Anak']);
  assert.deepEqual(words({ query: 'انق' }), ['Anak']);
  assert.deepEqual(words({ query: '#root:AJAR' }), ['belajar', 'ajar']);
  assert.equal(words({ query: 'tak' })[0], 'tidak');
  assert.ok(words({ query: 'nakk' }).includes('anakku'));
  assert.ok(words({ query: 'bealjar' }).includes('belajar'));
  assert.equal(distance('belajar', 'bealjar', 1), 1);
  assert.equal(words({ query: 'x'.repeat(500) }).length, 0);
});
test('all seven filters use explicit state, nonblank text and actual root equality', () => {
  assert.equal(words({ filter: 'all' }).length, 6);
  assert.deepEqual(words({ filter: 'enriched' }), ['tidak', 'anakku', 'belajar', 'Anak']);
  assert.deepEqual(words({ filter: 'root' }), ['ajar', 'Anak']);
  assert.deepEqual(words({ filter: 'colloquial' }), ['tidak', 'belajar']);
  assert.deepEqual(words({ filter: 'jawi' }), ['ajar', 'Anak']);
  assert.deepEqual(words({ filter: 'source' }), ['ajar']);
  assert.deepEqual(words({ filter: 'missing' }), ['ann']);
  assert.deepEqual(words({ bookmarks: ['anakku'], filter: 'enriched' }), ['anakku']);
  assert.deepEqual(words({ bookmarks: [] }), []);
});
test('four sorts and numeric ID tie breakers are deterministic', () => {
  assert.deepEqual(words({ sort: 'rank' }), ['tidak', 'anakku', 'belajar', 'ajar', 'ann', 'Anak']);
  assert.deepEqual(words({ sort: 'alpha' }), ['ajar', 'Anak', 'anakku', 'ann', 'belajar', 'tidak']);
  assert.deepEqual(words({ sort: 'alpha-desc' }), ['tidak', 'belajar', 'ann', 'anakku', 'Anak', 'ajar']);
  assert.deepEqual(words({ sort: 'senses' }), ['Anak', 'tidak', 'anakku', 'belajar', 'ajar', 'ann']);
  const ties = hydrateIndex([{ id: 3, w: 'a' }, { id: 1, w: 'a' }]);
  for (const sort of ['alpha', 'alpha-desc', 'senses', 'rank']) assert.deepEqual(searchEntries(ties, { sort }).results.map(e => e.id), [1, 3]);
});
test('sub-prefix counts precede narrowing, respect filters, cap at 18 and resolve ties', () => {
  const result = searchEntries(index, { letter: 'a', subPrefix: 'an' });
  assert.deepEqual(result.subPrefixCounts, [['an', 3], ['aj', 1]]);
  assert.equal(result.total, 3);
  assert.deepEqual(searchEntries(index, { letter: 'a', filter: 'enriched' }).subPrefixCounts, [['an', 2]]);
  assert.deepEqual(searchEntries(index, { letter: 'a', query: 'an' }).subPrefixCounts, []);
  const many = hydrateIndex([...'abcdefghijklmnopqrstuvwxyz'].map((c, id) => ({ id, w: `a${c}word` })));
  assert.equal(searchEntries(many, { letter: 'a' }).subPrefixCounts.length, 18);
  assert.deepEqual(searchEntries(many, { letter: 'a' }).subPrefixCounts[0], ['aa', 1]);
});
test('50-row pagination, explicit offsets, target coordinates and empty results', () => {
  const many = hydrateIndex(Array.from({ length: 123 }, (_, id) => ({ id: id + 1, w: `word${id}` })));
  assert.equal(searchEntries(many).results.length, 50);
  assert.equal(searchEntries(many, { page: 2 }).results[0].id, 51);
  assert.equal(searchEntries(many, { page: 3, offset: 7 }).results[0].id, 8);
  assert.equal(searchEntries(many, { offset: 120 }).results.length, 3);
  const target = searchEntries(many, { targetWord: 'WORD111' });
  assert.equal(target.offset, 100); assert.equal(target.targetIndex, 111);
  assert.equal(target.results.length, 23);
  assert.equal(searchEntries(many, { offset: -1 }).offset, 0);
  assert.equal(searchEntries(many, { page: 999 }).offset, 100);
  assert.equal(searchEntries([], { page: 999 }).total, 0);
});

test('shipped 15K index keeps Stage 3 states and filter semantics', async () => {
  const real = hydrateIndex(JSON.parse(await readFile(new URL('../app/static/data/search_index.json', import.meta.url), 'utf8')));
  assert.equal(searchEntries(real, { filter: 'all' }).total, 15000);
  assert.equal(searchEntries(real, { filter: 'enriched' }).total, 14748);
  assert.equal(searchEntries(real, { filter: 'source' }).total, 0);
  assert.equal(searchEntries(real, { filter: 'missing' }).total, 252);
  for (const [filter, predicate] of [
    ['root', e => e._rLower && e._rLower === e._wLower],
    ['colloquial', e => Boolean(e.a && e.a.trim())], ['jawi', e => Boolean(e.j && e.j.trim())],
  ]) assert.equal(searchEntries(real, { filter }).total, real.filter(predicate).length);
});

// Minimal asynchronous IndexedDB contract with durable storage independent of module RAM.
function fakeStorage({ failWrite = false } = {}) {
  const stored = new Map();
  const db = {
    close() {}, createObjectStore() {},
    transaction() {
      const tx = { objectStore: () => ({
        get(key) { const request = {}; setTimeout(() => { request.result = stored.get(key); request.onsuccess?.(); }, 0); return request; },
        put(value, key) { setTimeout(() => { if (failWrite) tx.onabort?.(); else { stored.set(key, structuredClone(value)); tx.oncomplete?.(); } }, 0); },
      }) };
      return tx;
    },
  };
  globalThis.indexedDB = { open() { const request = {}; setTimeout(() => { request.result = db; request.onsuccess?.(); }, 0); return request; } };
  const cached = new Map();
  const cache = {
    match: async url => cached.get(String(url))?.clone(),
    put: async (url, response) => { cached.set(String(url), response.clone()); },
  };
  globalThis.caches = { open: async () => cache };
  return { stored, cached };
}
let moduleNumber = 0;
const freshDB = () => import(`../app/static/db.js?test=${++moduleNumber}`);
test('DB deduplicates callers, retries failed fetches, reads durable shards after LRU eviction', async () => {
  fakeStorage();
  let calls = 0; let fail = true;
  globalThis.fetch = async () => { calls++; await new Promise(r => setTimeout(r, 2)); if (fail) throw Error('offline'); return Response.json({ saya: { id: 1 } }); };
  const db = await freshDB();
  const failed = await Promise.allSettled([db.loadShard('s'), db.ensureShard('s')]);
  assert.ok(failed.every(r => r.status === 'rejected')); assert.equal(calls, 1);
  fail = false;
  await Promise.all([db.loadShard('s'), db.getWordDetail('Saya')]); assert.equal(calls, 2);
  for (const letter of 'abcdef') await db.loadShard(letter);
  assert.equal((await db.loadShard('s')).source, 'indexeddb');
  assert.equal(calls, 8);
  await assert.rejects(db.loadShard('../x'));
});
test('DB malformed/HTTP failures are retryable and unavailable IDB reports memory fallback', async () => {
  delete globalThis.indexedDB;
  let response = new Response('bad', { status: 503 });
  globalThis.fetch = async () => response.clone();
  const db = await freshDB();
  await assert.rejects(db.loadShard('a'));
  response = new Response('bad'); await assert.rejects(db.loadShard('a'));
  response = Response.json(null); await assert.rejects(db.loadShard('a'));
  response = Response.json({ a: {} }); await db.loadShard('a');
  assert.equal(db.cacheStatus.persistent, false);
  await assert.rejects(db.prepareOffline());
});
test('offline preparation persists all 27 shards and index, supports pause/resume without refetch', async () => {
  const { stored, cached } = fakeStorage();
  const calls = [];
  globalThis.fetch = async url => { calls.push(String(url)); return Response.json(String(url).includes('search_index') ? [{ w: 'a' }] : { a: { id: 1 } }); };
  const db = await freshDB();
  let done = 0;
  const paused = await db.prepareOffline(p => { done = p.completed; }, () => done >= 3);
  assert.equal(paused.paused, true); assert.equal(stored.size, 3);
  const result = await db.prepareOffline();
  assert.equal(result.completed, 27); assert.equal(stored.size, 27); assert.equal(cached.size, 1);
  assert.equal(calls.length, 28);
  const restarted = await freshDB();
  globalThis.fetch = async () => { throw Error('network disabled'); };
  for (const letter of SHARD_KEYS) assert.equal((await restarted.loadShard(letter)).source, 'indexeddb');
  assert.equal((await restarted.prepareOffline()).completed, 27);
});
test('quota failure cannot be reported as offline success', async () => {
  fakeStorage({ failWrite: true });
  globalThis.fetch = async url => Response.json(String(url).includes('search_index') ? [] : {});
  const db = await freshDB();
  await assert.rejects(db.prepareOffline(), /持久保存/);
  assert.equal(db.cacheStatus.persistent, false);
});
test('damaged index cache is repaired; unsuccessful cache writes cannot claim offline readiness', async () => {
  const { cached } = fakeStorage();
  const url = new URL('../app/static/data/search_index.json', import.meta.url);
  cached.set(String(url), new Response('broken'));
  let calls = 0;
  globalThis.fetch = async () => { calls++; return Response.json([{ w: 'a' }]); };
  assert.equal((await loadSearchIndex({ requireCache: true }))[0].w, 'a'); assert.equal(calls, 1);
  assert.equal((await loadSearchIndex({ requireCache: true }))[0].w, 'a'); assert.equal(calls, 1);
  globalThis.caches = { open: async () => ({ match: async () => undefined, put: async () => { throw Error('quota'); } }) };
  await assert.rejects(loadSearchIndex({ requireCache: true }), /quota/);
  assert.equal((await loadSearchIndex())[0].w, 'a');
});
test('structured Markdown / Anki keep all languages and escape embedded HTML, tabs and line breaks', () => {
  const entry = { id: 1, headword: { word: 'a\t<script>\r\nb', status: 'official', jawi: 'انق' }, morphology: { root_word: 'a', root_jawi: 'انق' }, senses: [{ id: 1, ms_is_verbatim: true, ms_definition: 'ms', zh_definition: '中文', en_definition: 'English', collocations: [{ ms: '<img src=x>', zh: '中', en: 'en' }] }], dual_scenarios: [{ messages: [{ speaker: 'A', ms_spoken: 'hi', zh: '嗨', en: 'hello' }] }], etymology: { historical_story: 'story' } };
  const md = formatEntryMarkdown(entry);
  assert.ok(md.includes('English') && md.includes('中文') && md.includes('hello') && md.includes('story'));
  assert.ok(md.includes('DBP 原文:')); assert.ok(!md.includes('<script>'));
  const tsv = formatEntryAnkiTsv(entry);
  assert.equal(tsv.split('\t').length, 2); assert.ok(!/[\r\n]/.test(tsv));
  assert.ok(!tsv.includes('<img')); assert.ok(tsv.includes('&lt;img'));
  assert.equal(quoteLabel({ status: 'official' }, {}), '马来语释义 (基于 DBP 官方词条):');
  assert.equal(quoteLabel({ status: 'root_derived' }, {}), '马来语释义 (基于 DBP 词根推导):');
  assert.equal(quoteLabel({ status: 'corpus_usage' }, {}), '马来语释义 (字幕高频语料用法):');
});
test('structured export uses the shipped Malay schema for nuance, scenarios, dialogue and etymology', async () => {
  const real = JSON.parse(await readFile(new URL('../data/enriched/saya.json', import.meta.url), 'utf8'));
  const markdown = formatEntryMarkdown(real);
  const escaped = text => String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/([\\`*_[\]#|])/g, '\\$1');
  assert.ok(markdown.includes(escaped(real.senses[0].nuances)));
  assert.ok(markdown.includes('formal') && markdown.includes('colloquial'));
  assert.ok(markdown.includes(escaped(real.dual_scenarios[1].messages[0].en)));
  assert.ok(markdown.includes(escaped(real.etymology.historical_story)));
});
