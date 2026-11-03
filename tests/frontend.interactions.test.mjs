import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { controller, rows, reply } from './controller-harness.mjs';

const entry = word => ({ id: 1, word, is_enriched: true, data_state: 'enriched', headword: { word, jawi: 'انق', status: 'official' },
  morphology: { root_word: 'anak', root_jawi: 'انق', formula: 'anak + ku → anakku' },
  senses: [1, 2].map(id => ({ id, pos: 'n', zh_definition: '孩子', en_definition: 'child', ms_definition: 'anak', ms_is_verbatim: id === 1, collocations: [{ ms: 'anak kecil', zh: '小孩', en: 'small child' }] })),
  dual_scenarios: [{ scenario: 'formal', ms: 'Anak saya', zh: '我的孩子', en: 'My child' }, { scenario: 'colloquial', messages: [{ speaker: 'A', ms_spoken: 'Hai', ms_standard: 'Hai', zh: '嗨', en: 'Hi' }] }],
  spoken_shortcuts: [], cultural_pragmatics: { register: 'neutral' }, etymology: { historical_story: 'story' },
});
const setup = options => controller({ loadShard: async () => ({ shard: Object.fromEntries(['word0', 'anakku', 'anak'].map(w => [w, entry(w)])) }), ...options });
const tick = async () => { for (let n = 0; n < 5; n++) await Promise.resolve(); };

test('controller starts with exactly 50 rows, no automatic fill, and registers module service worker', async () => {
  const f = setup(); f.worker.reply({ type: 'ready', count: 15000 }); reply(f); await tick();
  assert.equal(f.element('word-list').children.length, 50);
  assert.equal(f.worker.messages.filter(m => m.type === 'search').length, 1);
  assert.deepEqual(f.registrations.map(args => [args[0], args[1].type]), [['/sw.js', 'module']]);
  assert.equal(typeof f.window.selectWord, 'function');
});
test('bottom scroll appends 50, visible page updates, and duplicate scroll does not duplicate requests', () => {
  const f = setup(); reply(f);
  const list = f.element('word-list'); list.scrollTop = 2800; list.dispatch('scroll');
  assert.equal(f.worker.messages.at(-1).offset, 50);
  const count = f.worker.messages.length; list.dispatch('scroll'); assert.equal(f.worker.messages.length, count);
  reply(f, rows(50)); assert.equal(list.children.length, 100);
  assert.equal(list.children[0].dataset.word, 'word0');
  list.scrollTop = 55 * 60; list.dispatch('scroll'); assert.equal(Number(f.element('page-input').value), 2);
});
test('page jumper/Enter/prev/next replace stream; prepend preserves visible anchor and row indices', () => {
  const f = setup(); reply(f);
  f.element('page-input').value = '4'; f.element('page-go').click(); reply(f, rows(150));
  assert.equal(f.element('word-list').children[0].dataset.word, 'word150');
  f.element('word-list').dispatch('wheel', { deltaY: -100 }); reply(f, rows(100));
  const list = f.element('word-list'); assert.equal(list.children.length, 100); assert.equal(list.scrollTop, 3000);
  assert.equal(list.children[50].dataset.word, 'word150'); assert.equal(list.children[50].dataset.index, 50);
  f.element('page-prev').click(); assert.equal(f.worker.messages.at(-1).offset, 100); reply(f, rows(100));
  f.element('page-next').click(); assert.equal(f.worker.messages.at(-1).offset, 150); reply(f, rows(150));
  f.element('page-input').value = '1'; f.element('page-input').dispatch('keydown', { key: 'Enter' });
  assert.equal(f.worker.messages.at(-1).offset, 0);
  f.ui.jumpPage(999); assert.equal(f.worker.messages.at(-1).offset, 200);
});
test('stale worker responses and slow detail success/error never overwrite newer results/selection', async () => {
  let resolveOld, rejectOld;
  const f = setup({ loadShard: letter => letter === 'b' ? new Promise((resolve, reject) => { resolveOld = resolve; rejectOld = reject; }) : Promise.resolve({ shard: { anak: entry('anak') } }) });
  reply(f); f.ui.search(); reply(f, [], 0, { requestId: f.ui.state.requestId - 1 });
  assert.equal(f.element('word-list').children.length, 50);
  const old = f.ui.selectWord('bslow'); await f.ui.selectWord('anak'); resolveOld({ shard: { bslow: entry('bslow') } }); await old;
  assert.equal(f.element('detail').querySelector('.word-title').textContent, 'anak');
  const failing = f.ui.selectWord('bslow'); await f.ui.selectWord('anak'); rejectOld(Error('stale')); await failing;
  assert.equal(f.element('detail').querySelector('.word-title').textContent, 'anak');
});
test('initial deep link survives worker readiness while its detail request is still in flight', async () => {
  let finish;
  const f = setup({ hash: '#anakku', loadShard: () => new Promise(resolve => { finish = resolve; }) });
  f.worker.reply({ type: 'ready', count: 15000 }); reply(f);
  assert.equal(f.ui.state.selectedWord, 'anakku');
  finish({ shard: { anakku: entry('anakku') } }); await tick();
  assert.equal(f.element('detail').querySelector('.word-title').textContent, 'anakku');
  assert.equal(f.element('search').value, '');
});
test('debounce and IME immediately reject old replies; composed search dispatches once after completion', () => {
  const f = setup(); reply(f);
  const oldId = f.ui.state.requestId;
  f.element('search').value = 'new'; f.element('search').dispatch('input');
  reply(f, [], 0, { requestId: oldId }); assert.equal(f.element('word-list').children.length, 50);
  f.element('search').dispatch('compositionstart'); f.element('search').value = '孩子';
  const messages = f.worker.messages.length;
  f.element('search').dispatch('input', { isComposing: true }); f.flushTimers();
  assert.equal(f.worker.messages.length, messages);
  f.element('search').dispatch('compositionend'); f.flushTimers();
  assert.equal(f.worker.messages.length, messages + 1); assert.equal(f.worker.messages.at(-1).query, '孩子');
});
test('hash selection and root-chip navigation update selection/hash without changing search text', async () => {
  const f = setup(); f.element('search').value = 'retained';
  await f.ui.selectWord('anakku');
  assert.equal(f.location.hash, 'anakku'); assert.equal(f.element('search').value, 'retained');
  f.element('detail').querySelector('.root-chip').click(); await tick();
  assert.equal(f.ui.state.selectedWord, 'anak'); assert.equal(f.element('search').value, 'retained');
  f.location.hash = '#anakku'; f.window.dispatch('hashchange'); await tick();
  assert.equal(f.element('detail').querySelector('.word-title').textContent, 'anakku');
});
test('letter changes clear sub-prefix; rendered prefix controls update worker request', () => {
  const f = setup(); reply(f, rows(), 250, { subPrefixCounts: [['an', 20]] });
  const prefix = f.element('sub-prefix-bar').querySelector('[data-prefix="an"]');
  assert.equal(prefix.textContent, 'an');
  assert.equal(prefix.getAttribute('title'), '20 词');
  f.element('sub-prefix-bar').querySelector('[data-prefix="an"]').click();
  assert.equal(f.worker.messages.at(-1).subPrefix, 'an');
  f.element('alphabet-bar').querySelector('[data-letter="b"]').click();
  assert.equal(f.worker.messages.at(-1).subPrefix, ''); assert.equal(f.worker.messages.at(-1).letter, 'b');
});
test('shell controls use compact rows, pressed states, search hint and sidebar footer', () => {
  const f = setup(); reply(f);
  assert.equal(f.element('alphabet-bar').querySelectorAll('.alphabet-button').length, 27);
  assert.deepEqual(f.element('filters').querySelectorAll('[data-filter]').map(b => b.textContent), ['全部', '8维精编', '词根', '口语', 'Jawi', '原义', '待补']);
  assert.equal(f.element('alphabet-bar').querySelector('[data-letter=""]').getAttribute('aria-pressed'), 'true');
  const letter = f.element('alphabet-bar').querySelector('[data-letter="a"]'); letter.click();
  assert.equal(letter.getAttribute('aria-pressed'), 'true');
  const filter = f.element('filters').querySelector('[data-filter="enriched"]'); filter.click();
  assert.equal(filter.getAttribute('aria-pressed'), 'true');
  assert.equal(f.element('filters').querySelector('[data-filter="all"]').getAttribute('aria-pressed'), 'false');
  f.element('search').value = 'anak'; f.element('search').dispatch('input');
  assert.equal(f.element('search-key').hidden, true);
  f.element('clear').click(); assert.equal(f.element('search-key').hidden, false);
  reply(f);
  assert.match(f.element('list-status').textContent, /50 \/ 250/);
  assert.equal(f.element('offline').parent.classList.contains('sidebar-footer'), true);
  assert.equal(f.element('sub-prefix-bar').parent.classList.contains('search-area'), true);
  const row = f.element('word-list').children[0];
  assert.equal(row.tagName, 'button'); assert.equal(row.classList.contains('word-row'), true);
  assert.ok(row.querySelector('.row-pos')); assert.equal(row.querySelector('.status-badge'), null);
  assert.equal(f.element('typography-fonts').querySelectorAll('button').length, 4);
  assert.equal(f.element('typography-papers').querySelectorAll('.paper-swatch').length, 4);
  assert.equal(f.element('typography-panel').querySelector('[data-font-size]'), null);
});
test('sidebar width clamps, persists, resets and supports pointer and keyboard controls', () => {
  const f = setup(), resizer = f.element('resizer');
  assert.equal(resizer.getAttribute('aria-valuenow'), '340');
  resizer.dispatch('pointerdown', { clientX: 340, pointerId: 1, button: 0 });
  resizer.dispatch('pointermove', { clientX: 1200, pointerId: 1 });
  resizer.dispatch('pointerup', { pointerId: 1 });
  assert.equal(resizer.getAttribute('aria-valuenow'), '640');
  const restored = setup({ stored: [...f.storage] });
  assert.equal(restored.element('resizer').getAttribute('aria-valuenow'), '640');
  resizer.dispatch('pointerdown', { clientX: 640, pointerId: 2, button: 0 });
  resizer.dispatch('pointermove', { clientX: 0, pointerId: 2 });
  resizer.dispatch('pointercancel', { pointerId: 2 });
  assert.equal(resizer.getAttribute('aria-valuenow'), '240');
  assert.equal(f.document.body.classList.contains('resizing'), false);
  resizer.dispatch('dblclick'); assert.equal(resizer.getAttribute('aria-valuenow'), '340');
  resizer.dispatch('keydown', { key: 'ArrowRight', shiftKey: true });
  assert.equal(JSON.parse(f.storage.get('open_melayu_sidebar_width')), 380);
  resizer.dispatch('keydown', { key: 'Home' }); assert.equal(resizer.getAttribute('aria-valuenow'), '240');
  resizer.dispatch('keydown', { key: 'End' }); assert.equal(resizer.getAttribute('aria-valuenow'), '640');
  resizer.dispatch('keydown', { key: 'Enter' }); assert.equal(resizer.getAttribute('aria-valuenow'), '340');
});
test('mobile detail uses the same 900px breakpoint as the stylesheet', async () => {
  const f = setup(); f.window.innerWidth = 900;
  await f.ui.selectWord('anakku'); assert.equal(f.document.body.classList.contains('reading'), true);
  f.element('back').click(); assert.equal(f.document.body.classList.contains('reading'), false);
  f.window.innerWidth = 901; await f.ui.selectWord('anakku');
  assert.equal(f.document.body.classList.contains('reading'), false);
});
test('three toolbar language modes synchronize preferences and keep all translations in rendered DOM', async () => {
  const f = setup(); await f.ui.selectWord('anakku');
  assert.equal(f.element('lang-trilingual').getAttribute('aria-pressed'), 'true');
  f.element('lang-bilingual').click();
  assert.equal(f.document.body.classList.contains('lang-mode-bilingual'), true);
  assert.equal(f.element('lang-bilingual').getAttribute('aria-pressed'), 'true');
  assert.equal(f.element('typography-panel').querySelector('[data-typo-lang]'), null);
  f.element('lang-ms').click();
  assert.equal(f.element('lang-ms').getAttribute('aria-pressed'), 'true');
  assert.ok(f.element('detail').querySelector('.sense-en-sub').textContent.includes('child'));
  assert.equal(JSON.parse(f.storage.get('open_melayu_typography_v2')).langMode, 'ms');
});
test('all typography fields, exact size steps, bidirectional theme sync, persistence and reset', () => {
  const f = setup(), panel = f.element('typography-panel');
  f.element('font-decrease').click(); assert.equal(f.element('font-size-value').textContent, '95% · 小字');
  f.element('font-decrease').click(); assert.equal(f.element('font-size-value').textContent, '85% · 紧凑'); assert.equal(f.element('font-decrease').disabled, true);
  for (let n = 0; n < 4; n++) f.element('font-increase').click(); assert.equal(f.element('font-increase').disabled, true);
  panel.querySelector('[data-font-family="legible"]').click(); panel.querySelector('[data-density="spacious"]').click(); panel.querySelector('[data-paper="night"]').click();
  assert.equal(f.document.documentElement.style['--reading-line-height'], '1.85');
  assert.equal(f.document.documentElement.style['--reading-padding-scale'], '1.25');
  assert.equal(f.document.documentElement.dataset.theme, 'dark'); assert.equal(f.document.documentElement.style['--font-scale'], '1.3');
  f.element('theme-toggle').click(); assert.equal(panel.querySelector('[data-paper="white"]').getAttribute('aria-pressed'), 'true');
  const restored = setup({ stored: [...f.storage] }); assert.equal(restored.document.documentElement.dataset.readingFont, 'legible');
  restored.element('typo-reset').click();
  assert.deepEqual(JSON.parse(restored.storage.get('open_melayu_typography_v2')), { langMode: 'trilingual', fontSize: 100, fontFamily: 'sans', density: 'normal', paper: 'white' });
  const invalid = setup({ stored: [['open_melayu_typography_v2', '{"fontSize":999,"paper":"bad"}']] });
  assert.equal(invalid.element('font-size-value').textContent, '100% · 标准');
});
test('root Jawi, status badges, four-tier provenance, quick chips and pulse bind to flat cards', async () => {
  const f = setup(); await f.ui.selectWord('anakku');
  const detail = f.element('detail');
  assert.equal(detail.querySelector('.root-jawi-inline').textContent, 'انق');
  assert.equal(detail.querySelector('.root-jawi-inline').getAttribute('dir'), 'rtl');
  assert.ok(detail.querySelector('.status-badge').classList.contains('badge-gold'));
  assert.equal(detail.querySelectorAll('.quote-label')[0].textContent, 'DBP 原文:');
  assert.equal(detail.querySelectorAll('.quote-label')[1].textContent, '马来语释义 (基于 DBP 官方词条):');
  assert.equal(detail.querySelectorAll('details,.accordion').length, 0);
  const chip = detail.querySelectorAll('.sense-chip')[1]; chip.click();
  const sense = f.element('sense-2'); assert.equal(sense.scrollOptions.behavior, 'smooth'); assert.equal(sense.classList.contains('pulse'), true);
  sense.dispatch('animationend'); assert.equal(sense.classList.contains('pulse'), false);
});
test('pinned word follows content scroll and includes mini audio; focus/Escape and typography close stay synchronized', async () => {
  const f = setup(); await f.ui.selectWord('anakku');
  assert.equal(f.element('toolbar-pinned-word').hidden, true);
  f.element('content').scrollTop = 400; f.element('content').dispatch('scroll');
  assert.equal(f.element('toolbar-pinned-word').hidden, false);
  assert.ok(f.element('toolbar-pinned-word').querySelector('[data-speak]'));
  assert.ok(f.element('toolbar-pinned-word').querySelector('.jawi-text'));
  assert.equal(f.element('breadcrumb').hidden, true);
  assert.equal(f.element('content').classList.contains('is-scrolled'), true);
  f.element('content').scrollTop = 0; f.element('content').dispatch('scroll');
  assert.equal(f.element('breadcrumb').hidden, false);
  f.element('focus').click(); assert.equal(f.document.body.classList.contains('immersive'), true);
  f.element('typography-btn').click(); assert.equal(f.element('typography-panel').open, true);
  f.element('search').dispatch('keydown', { key: 'Escape' });
  assert.equal(f.element('focus').getAttribute('aria-pressed'), 'false');
  assert.equal(f.element('typography-panel').open, false); assert.equal(f.element('typography-btn').getAttribute('aria-expanded'), 'false');
  f.element('typography-btn').click(); f.element('typography-handle').dispatch('dblclick');
  assert.equal(f.element('typography-panel').open, false);
  assert.equal(f.document.activeElement, f.element('typography-btn'));
});
test('copy actions serialize current model despite hidden translations', async () => {
  const f = setup(); await f.ui.selectWord('anakku'); f.element('lang-ms').click();
  f.element('copy').click(); f.element('copy-anki').click(); await tick();
  assert.equal(f.copied.length, 2); assert.ok(f.copied[0].includes('child') && f.copied[0].includes('孩子'));
  assert.equal(f.copied[1].split('\t').length, 2); assert.ok(!/[\r\n]/.test(f.copied[1]));
});
test('3D flip controller, completion/reopen, daily streak idempotence, swipe and cancel', () => {
  const f = setup(); reply(f);
  f.element('daily').click(); f.element('flashcard').click();
  assert.equal(f.element('flashcard').classList.contains('is-flipped'), true);
  f.element('study-known').click(); assert.equal(f.element('card-word').textContent, '完成！');
  f.element('close-study').click(); f.element('practice').click();
  assert.notEqual(f.element('card-word').textContent, '完成！'); assert.ok(f.element('flashcard').querySelector('.flashcard-inner'));
  assert.equal(JSON.parse(f.storage.get('open_melayu_streak')).count, 1);
  f.element('study-grabber').dispatch('pointerdown', { clientY: 0, pointerId: 1 });
  f.element('study-grabber').dispatch('pointercancel'); f.element('study-grabber').dispatch('pointerup', { clientY: 100 });
  assert.equal(f.element('study').open, true);
  f.element('study-grabber').dispatch('pointerdown', { clientY: 0, pointerId: 1 }); f.element('study-grabber').dispatch('pointerup', { clientY: 100 });
  assert.equal(f.element('study').open, false);
});
test('offline button passes progress and pause callback, handles success/error without false readiness', async () => {
  let finish, shouldPause;
  const f = setup({ prepareOffline: async (onProgress, pause) => { shouldPause = pause; onProgress({ completed: 3, total: 27 }); return new Promise(r => { finish = r; }); } });
  f.element('offline').click(); assert.equal(f.element('offline').textContent, '3/27 · 暂停');
  f.element('offline').click(); assert.equal(shouldPause(), true);
  finish({ paused: true }); await tick(); assert.equal(f.element('offline').textContent, '继续离线准备');
  const failed = setup({ prepareOffline: async () => { throw Error('quota'); } }); failed.element('offline').click(); await tick();
  assert.equal(failed.element('offline').textContent, '重试离线准备');
});
test('CSS contracts protect Jawi spacing, hide exact language groups, and retain 3D/sticky/reduced-motion rules', async () => {
  const css = await readFile(new URL('../app/static/styles.css', import.meta.url), 'utf8');
  assert.match(css, /\.jawi-title, \.jawi-pill, \.jawi-text, \.root-jawi-inline\s*\{[^}]*font-family: var\(--font-jawi\) !important;[^}]*direction: rtl;[^}]*letter-spacing: 0 !important;[^}]*word-spacing: normal !important;/);
  assert.ok(css.includes('body.lang-mode-bilingual :is(.sense-en-sub, .colloc-en, .bubble-en)'));
  assert.ok(css.includes('body.lang-mode-ms :is(.sense-zh-title, .sense-en-sub, .sense-nuance-box, .colloc-zh, .colloc-en, .bubble-zh, .bubble-en, .preview-def)'));
  assert.match(css, /\.content-toolbar\s*\{[^}]*position: sticky;/);
  assert.ok(css.includes('transform-style: preserve-3d')); assert.ok(css.includes('backface-visibility: hidden'));
  assert.ok(css.includes('prefers-reduced-motion: reduce'));
});
