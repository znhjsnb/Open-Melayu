import test from 'node:test';
import assert from 'node:assert/strict';
import { openBrowser, until, pause } from './browser-harness.mjs';

function fixtureEntry(word, id) {
  return { id, word, is_enriched: true, data_state: 'enriched',
    headword: { word, jawi: 'انق', status: 'official', ipa: '/a/' },
    morphology: { root_word: 'anak', root_jawi: 'انق', formula: 'anak + ku → anakku' },
    senses: Array.from({ length: 4 }, (_, n) => ({ id: n + 1, pos: 'n', zh_definition: `孩子 ${n}`, en_definition: `child ${n}`, ms_definition: `anak ${n}`, ms_is_verbatim: n === 0, nuance: '说明', collocations: [{ ms: 'anak kecil', zh: '小孩', en: 'small child' }, { ms: 'anak saya', zh: '我的孩子', en: 'my child' }] })),
    dual_scenarios: [{ scenario: 'formal', ms: 'Anak saya.', zh: '孩子', en: 'My child.' }, { scenario: 'colloquial', messages: [{ speaker: 'A', ms_spoken: 'Hai', ms_standard: 'Hai', zh: '嗨', en: 'Hi' }, { speaker: 'B', ms_spoken: 'Ya', ms_standard: 'Ya', zh: '是', en: 'Yes' }] }],
    spoken_shortcuts: [], cultural_pragmatics: { register: 'neutral', usage_etiquette: '说明' }, etymology: { historical_story: 'A story.', cognitive_memory_aid: 'Remember.' },
  };
}
const index = Array.from({ length: 220 }, (_, n) => ({ id: n + 1, w: `a${String(n).padStart(3, '0')}`, e: 1, st: 'e', s: ['孩子'], j: 'انق', r: 'anak' }));
index.push({ id: 221, w: 'bslow', e: 1, st: 'e', s: ['慢'] }, { id: 222, w: 'cfast', e: 1, st: 'e', s: ['快'] }, { id: 223, w: 'anak', e: 1, st: 'e', s: ['孩子'] }, { id: 224, w: 'anakku', e: 1, st: 'e', s: ['孩子'] });
const shards = {};
for (const row of index) (shards[row.w[0]] ||= {})[row.w] = fixtureEntry(row.w, row.id);

test('browser UI controllers with isolated data, real DOM/worker/IndexedDB/CSS', { timeout: 120000 }, async t => {
  const browser = await openBrowser({ fixture: { index, shards } });
  t.after(() => browser.close());
  const { evaluate: js, send } = browser;
  await send('Page.addScriptToEvaluateOnNewDocument', { source: `
    const NativeWorker = window.Worker;
    window.Worker = class extends NativeWorker {
      constructor(...args) { super(...args); window.testWorker = this; }
      postMessage(message) { if (message.type === 'search') window.lastSearch = message; super.postMessage(message); }
    };
    window.copiedTexts = [];
    Object.defineProperty(navigator, 'clipboard', { value: { writeText: async text => window.copiedTexts.push(text) } });
  ` });
  await send('Page.navigate', { url: browser.origin });
  const ready = () => until(() => js(`document.querySelectorAll('.word-item').length === 50 && !!document.querySelector('.word-title')`));
  const select = async word => {
    await js(`window.selectWord(${JSON.stringify(word)})`);
    await until(() => js(`document.querySelector('.word-title')?.textContent === ${JSON.stringify(word)}`));
  };
  await ready();

  await t.test('initial 50 rows stay fixed until scroll; append retains rows and page follows visible row', async () => {
    await pause(250);
    assert.equal(await js(`document.querySelectorAll('.word-item').length`), 50);
    await js(`document.getElementById('word-list').scrollTop = 99999`);
    await until(() => js(`document.querySelectorAll('.word-item').length === 100`));
    assert.equal(await js(`document.querySelector('.word-item').dataset.word`), 'a000');
    await js(`document.getElementById('word-list').scrollTop = document.querySelectorAll('.word-item')[55].offsetTop - document.querySelector('.word-item').offsetTop`);
    await until(() => js(`document.getElementById('page-input').value === '2'`));
  });
  await t.test('page jumper replaces stream; top prepend retains scroll anchor, prev/next and Enter work', async () => {
    await js(`document.getElementById('page-input').value = '4'; document.getElementById('page-go').click()`);
    await until(() => js(`document.querySelector('.word-item')?.dataset.word === 'a150'`));
    await js(`document.getElementById('word-list').dispatchEvent(new WheelEvent('wheel', {deltaY:-100}))`);
    await until(() => js(`document.querySelector('.word-item')?.dataset.word === 'a100'`));
    assert.equal(await js(`document.querySelectorAll('.word-item').length`), 100);
    assert.equal(await js(`(() => { const l=document.getElementById('word-list'), r=l.children[50]; return Math.abs(r.offsetTop - l.children[0].offsetTop - l.scrollTop) < 3; })()`), true);
    await js(`document.getElementById('page-prev').click()`);
    await until(() => js(`document.querySelector('.word-item')?.dataset.word === 'a100' && document.querySelectorAll('.word-item').length === 50`));
    await js(`document.getElementById('page-next').click()`);
    await until(() => js(`document.querySelector('.word-item')?.dataset.word === 'a150'`));
    await js(`document.getElementById('page-input').value = '1'; document.getElementById('page-input').dispatchEvent(new KeyboardEvent('keydown',{key:'Enter',bubbles:true}))`);
    await until(() => js(`document.querySelector('.word-item')?.dataset.word === 'a000'`));
  });
  await t.test('stale search messages are ignored and stale detail loads cannot overwrite later selection', async () => {
    await js(`window.testWorker.onmessage({ data: { type:'results', requestId:window.lastSearch.requestId-1, results:[], total:0, offset:0 } })`);
    assert.equal(await js(`document.querySelectorAll('.word-item').length`), 50);
    await js(`window.selectWord('bslow'); window.selectWord('cfast');`);
    await until(() => js(`document.querySelector('.word-title')?.textContent === 'cfast'`));
    await pause(350);
    assert.equal(await js(`document.querySelector('.word-title')?.textContent`), 'cfast');
  });
  await t.test('word selection, hash navigation and root chips preserve search text', async () => {
    await js(`document.getElementById('search').value = 'kept'; location.hash = '#anakku';`);
    await until(() => js(`document.querySelector('.word-title')?.textContent === 'anakku'`));
    assert.equal(await js(`document.getElementById('search').value`), 'kept');
    await js(`document.querySelector('.root-chip').click()`);
    await until(() => js(`document.querySelector('.word-title')?.textContent === 'anak'`));
    assert.equal(await js(`document.getElementById('search').value`), 'kept');
    assert.equal(await js(`location.hash`), '#anak');
    await js(`document.getElementById('search').value = ''`);
  });
  await t.test('language modes use CSS, retain translations, and synchronize panel and toolbar', async () => {
    assert.equal(await js(`document.getElementById('lang-trilingual').getAttribute('aria-pressed')`), 'true');
    await js(`document.getElementById('lang-bilingual').click()`);
    assert.equal(await js(`getComputedStyle(document.querySelector('.sense-en-sub')).display`), 'none');
    assert.equal(await js(`document.querySelector('[data-typo-lang="bilingual"]').getAttribute('aria-pressed')`), 'true');
    await js(`document.querySelector('[data-typo-lang="ms"]').click()`);
    assert.equal(await js(`getComputedStyle(document.querySelector('.sense-zh-title')).display`), 'none');
    assert.ok(await js(`document.querySelector('.sense-en-sub').textContent.includes('child')`));
    await js(`document.querySelector('[data-typo-lang="trilingual"]').click()`);
    assert.notEqual(await js(`getComputedStyle(document.querySelector('.sense-en-sub')).display`), 'none');
  });
  await t.test('font steps, font families, density and paper persist; theme sync works in both directions', async () => {
    const before = await js(`getComputedStyle(document.querySelector('.sense-zh-title')).fontSize`);
    await js(`document.getElementById('font-increase').click(); document.querySelector('[data-font-family="legible"]').click(); document.querySelector('[data-density="spacious"]').click(); document.querySelector('[data-paper="night"]').click()`);
    assert.equal(await js(`document.documentElement.dataset.theme`), 'dark');
    assert.notEqual(await js(`getComputedStyle(document.querySelector('.sense-zh-title')).fontSize`), before);
    assert.deepEqual(await js(`JSON.parse(localStorage.getItem('open_melayu_typography_v2'))`), { langMode: 'trilingual', fontSize: 115, fontFamily: 'legible', density: 'spacious', paper: 'night' });
    await js(`document.getElementById('theme-toggle').click()`);
    assert.equal(await js(`document.querySelector('[data-paper="white"]').getAttribute('aria-pressed')`), 'true');
    await js(`document.querySelector('[data-font-size="85"]').click()`);
    assert.equal(await js(`document.getElementById('font-decrease').disabled`), true);
    await js(`document.querySelector('[data-font-size="130"]').click()`);
    assert.equal(await js(`document.getElementById('font-increase').disabled`), true);
    await js(`document.querySelector('[data-paper="sepia"]').click(); document.querySelector('[data-font-family="serif"]').click()`);
  });
  await t.test('saved preferences survive reload; reset restores every field', async () => {
    await send('Page.reload'); await ready();
    assert.equal(await js(`document.documentElement.dataset.readingPaper`), 'sepia');
    assert.equal(await js(`document.documentElement.dataset.readingFont`), 'serif');
    await js(`document.getElementById('typo-reset').click()`);
    assert.deepEqual(await js(`JSON.parse(localStorage.getItem('open_melayu_typography_v2'))`), { langMode: 'trilingual', fontSize: 100, fontFamily: 'sans', density: 'normal', paper: 'white' });
  });
  await t.test('Jawi title/root use protected RTL font and spacing; sense chips scroll and pulse; no collapsed content', async () => {
    await select('anakku');
    await js(`document.querySelector('[data-font-family="legible"]').click()`);
    for (const selector of ['.jawi-title', '.jawi-pill', '.root-jawi-inline']) {
      const style = await js(`(() => {const s=getComputedStyle(document.querySelector('${selector}')); return {direction:s.direction, spacing:s.letterSpacing, words:s.wordSpacing, font:s.fontFamily};})()`);
      assert.equal(style.direction, 'rtl'); assert.ok(['0px', 'normal'].includes(style.spacing));
      assert.ok(['0px', 'normal'].includes(style.words)); assert.ok(style.font.includes('Amiri'));
    }
    assert.equal(await js(`document.querySelector('.root-jawi-inline').textContent`), 'انق');
    assert.equal(await js(`document.querySelectorAll('details,.accordion').length`), 0);
    assert.equal(await js(`document.querySelectorAll('.sense-chip').length`), 4);
    await js(`document.querySelectorAll('.sense-chip')[3].click()`);
    assert.equal(await js(`document.getElementById('sense-4').classList.contains('pulse')`), true);
    await until(() => js(`document.getElementById('content').scrollTop > 0`));
    await js(`document.getElementById('typo-reset').click()`);
  });
  await t.test('sticky pinned header appears below headword and contains Jawi/audio; focus and Escape work from inputs', async () => {
    await js(`document.getElementById('content').scrollTop=0`); await pause(70);
    assert.equal(await js(`document.getElementById('toolbar-pinned-word').hidden`), true);
    await js(`document.getElementById('content').scrollTop=800`);
    await until(() => js(`!document.getElementById('toolbar-pinned-word').hidden`));
    assert.ok(await js(`!!document.querySelector('#toolbar-pinned-word .jawi-text') && !!document.querySelector('#toolbar-pinned-word [data-speak]')`));
    assert.equal(await js(`getComputedStyle(document.querySelector('.content-toolbar')).position`), 'sticky');
    await js(`document.getElementById('focus').click()`);
    assert.equal(await js(`document.body.classList.contains('focus-mode')`), true);
    await js(`document.getElementById('search').dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
    assert.equal(await js(`document.getElementById('focus').getAttribute('aria-pressed')`), 'false');
    await js(`document.getElementById('typography-btn').click(); document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape',bubbles:true}))`);
    assert.equal(await js(`document.getElementById('typography-panel').open`), false);
  });
  await t.test('copy exports model content despite hidden language; 3D flashcards reopen after completion and support swipe', async () => {
    await js(`document.getElementById('lang-ms').click(); document.getElementById('copy').click(); document.getElementById('copy-anki').click()`);
    assert.equal(await js(`window.copiedTexts.length`), 2);
    assert.ok(await js(`window.copiedTexts[0].includes('child') && window.copiedTexts[0].includes('孩子')`));
    assert.equal(await js(`window.copiedTexts[1].split('\t').length`), 2);
    await js(`document.getElementById('daily').click(); document.getElementById('flashcard').click()`);
    assert.equal(await js(`document.getElementById('flashcard').classList.contains('is-flipped')`), true);
    assert.equal(await js(`getComputedStyle(document.querySelector('.flashcard-inner')).transformStyle`), 'preserve-3d');
    assert.equal(await js(`getComputedStyle(document.querySelector('.flashcard-back')).backfaceVisibility`), 'hidden');
    await js(`document.getElementById('study-known').click(); document.getElementById('close-study').click(); document.getElementById('practice').click()`);
    assert.notEqual(await js(`document.getElementById('card-word').textContent`), '完成！');
    assert.equal(await js(`JSON.parse(localStorage.getItem('open_melayu_streak')).count`), 1);
    const grab = await js(`(() => { const r = document.getElementById('study-grabber').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()`);
    await send('Input.dispatchMouseEvent', { type: 'mousePressed', x: grab.x, y: grab.y, button: 'left', clickCount: 1 });
    await send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: grab.x, y: grab.y + 120, button: 'left', clickCount: 1 });
    assert.equal(await js(`document.getElementById('study').open`), false);
  });
  await t.test('two-letter selection clears on letter change; offline button durably prepares every shard and module SW', async () => {
    await js(`document.querySelector('[data-letter="a"]').click()`);
    await until(() => js(`!!document.querySelector('[data-prefix="an"]')`));
    await js(`document.querySelector('[data-prefix="an"]').click()`);
    await until(() => js(`document.querySelectorAll('.word-item').length === 2`));
    await js(`document.querySelector('[data-letter="c"]').click()`);
    await until(() => js(`document.querySelector('.word-item')?.dataset.word === 'cfast'`));
    assert.equal(await js(`window.lastSearch.subPrefix`), '');
    await js(`document.getElementById('offline').click()`);
    await until(() => js(`document.getElementById('offline').textContent === '离线词库已就绪'`));
    assert.equal(await js(`(async()=>{const db=await new Promise(r=>{const q=indexedDB.open('open-melayu-shards');q.onsuccess=()=>r(q.result)});return await new Promise(r=>{const q=db.transaction('shards').objectStore('shards').count();q.onsuccess=()=>{r(q.result);db.close()}})})()`), 27);
    await until(() => js(`(async()=>!!(await navigator.serviceWorker.getRegistration()))()`));
  });
  assert.deepEqual(browser.errors, []);
});

test('live 8766 Stage 3 workbench: 15K, initial 50, original manifest and full translations', { timeout: 60000 }, async t => {
  const browser = await openBrowser();
  t.after(() => browser.close());
  const { send, evaluate: js } = browser;
  await send('Page.navigate', { url: 'http://127.0.0.1:8766/' });
  await until(() => js(`document.querySelectorAll('.word-item').length === 50 && !!document.querySelector('.word-title')`));
  assert.ok(await js(`document.getElementById('connection').textContent.includes('15,000')`));
  assert.equal(await js(`(async()=> (await import('/data.js')).DATA_VERSION)()`), 'om-20261103-v9756');
  assert.equal(await js(`(async()=> (await (await fetch('/data/manifest.json')).json()).build_id)()`), 'om-20261103-v9756');
  for (const word of ['saya', 'anakku', 'anggap', 'jaikant']) {
    await js(`window.selectWord('${word}')`);
    await until(() => js(`document.querySelector('.word-title')?.textContent === '${word}'`));
    assert.equal(await js(`document.getElementById('search').value`), '');
    assert.equal(await js(`document.querySelectorAll('details,.accordion').length`), 0);
  }
  await js(`window.selectWord('anakku')`);
  await until(() => js(`document.querySelector('.word-title')?.textContent === 'anakku'`));
  assert.ok(await js(`!!document.querySelector('.root-jawi-inline')`));
  await js(`document.getElementById('lang-ms').click()`);
  assert.equal(await js(`getComputedStyle(document.querySelector('.sense-en-sub')).display`), 'none');
  assert.ok(await js(`document.querySelector('.sense-en-sub').textContent.length > 0`));
  assert.deepEqual(browser.errors, []);
});
