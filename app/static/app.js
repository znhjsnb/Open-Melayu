import { DATA_VERSION, normalizeWord, shardFor } from './data.js';
import { loadShard, cacheStatus } from './db.js';

// DOM Selectors
const $ = id => document.getElementById(id);
const searchInput = $('search');
const clearButton = $('clear');
const wordList = $('word-list');
const content = $('content');
const detail = $('detail');
const resultCount = $('result-count');
const searchTime = $('search-time');
const listStatus = $('list-status');
const sortOrder = $('sort-order');
const bookmarkFilter = $('bookmarks');
const bookmarkCount = $('bookmark-count');
const alphabetBar = $('alphabet-bar');
const filterButtons = document.querySelectorAll('.filter-pill');
const pagePrev = $('page-prev');
const pageNext = $('page-next');
const pageInput = $('page-input');
const pageTotal = $('page-total');
const themeToggle = $('theme');
const toastEl = $('toast');
const connectionEl = $('connection');
const pinnedWord = $('toolbar-pinned-word');
const breadcrumb = $('breadcrumb');
const saveBtn = $('save');
const copyBtn = $('copy');
const copyAnkiBtn = $('copy-anki');
const backBtn = $('back');
const langBilingualBtn = $('lang-bilingual');
const langMsBtn = $('lang-ms');
const studyDialog = $('study');
const dailyBtn = $('daily');
const practiceBtn = $('practice');
const closeStudyBtn = $('close-study');
const studyAgainBtn = $('study-again');
const studyKnownBtn = $('study-known');
const studyOpenBtn = $('study-open');
const flashcard = $('flashcard');
const typographyBtn = $('typography-btn');
const typographyPanel = $('typography-panel');
const typographyClose = $('typography-close');
const typographyIncrease = $('typography-increase');
const typographyDecrease = $('typography-decrease');
const typographyScale = $('typography-scale');
const typographyReset = $('typography-reset');

// Audio and Speech State
let activeSpeechButton = null;
let speechGeneration = 0;
let malayVoice = null;
let voiceInitialized = false;

// App State
const pageSize = 50;
const state = {
  query: '',
  filter: '',
  sort: 'rank',
  letter: '',
  offset: 0,
  page: 1,
  totalPages: 1,
  results: [],
  total: 0,
  selectedWord: null,
  selectedIndex: -1,
  requestId: 0,
  isSearching: false,
  studyWords: [],
  studyIndex: 0,
  studyKnown: 0,
  fontSize: 100
};

// Local Storage Helpers
function readStorage(key, fallback) {
  try {
    const val = localStorage.getItem(key);
    return val !== null ? JSON.parse(val) : fallback;
  } catch {
    return fallback;
  }
}

function writeStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

// Bookmarks & Progress
const BOOKMARKS_KEY = 'open_melayu_bookmarks';
const bookmarks = new Set(readStorage(BOOKMARKS_KEY, []));

function updateBookmarkCount() {
  bookmarkCount.textContent = bookmarks.size;
}
updateBookmarkCount();

// Toast Notification
let toastTimer = null;
function toast(message) {
  toastEl.textContent = message;
  toastEl.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toastEl.hidden = true; }, 3200);
}

// HTML Escaping
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[c]);
}

// Highlight helper
function highlighted(text, word) {
  const source = String(text ?? '');
  if (!word) return escapeHtml(source);
  const index = source.toLowerCase().indexOf(String(word).toLowerCase());
  if (index < 0) return escapeHtml(source);
  return `${escapeHtml(source.slice(0, index))}<mark>${escapeHtml(source.slice(index, index + word.length))}</mark>${escapeHtml(source.slice(index + word.length))}`;
}

// Web Speech API Voice Initialization
function initVoices() {
  if (!('speechSynthesis' in window)) return;
  const voices = window.speechSynthesis.getVoices();
  if (voices.length) {
    voiceInitialized = true;
    // Look for Malay (ms-MY), fallback to Indonesian (id-ID)
    malayVoice = voices.find(v => v.lang === 'ms-MY' || v.lang === 'ms_MY') ||
                 voices.find(v => v.lang.startsWith('ms')) ||
                 voices.find(v => v.lang === 'id-ID' || v.lang.startsWith('id')) ||
                 null;
  }
}
if ('speechSynthesis' in window) {
  initVoices();
  window.speechSynthesis.onvoiceschanged = initVoices;
}

// Entity Audio Pill Button Generator
const speakerIconSvg = '<svg class="speaker-icon" viewBox="0 0 24 24" width="14" height="14" fill="currentColor" aria-hidden="true"><path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z"/></svg>';

function audioButton(text, label = '发音', light = false) {
  return `<button class="audio-pill${light ? ' light' : ''}" data-speak="${escapeHtml(text)}" aria-label="${escapeHtml(label)}">${speakerIconSvg}<span>${escapeHtml(label)}</span><span class="wave" aria-hidden="true"><span></span><span></span><span></span></span></button>`;
}

function speakText(text, buttonEl = null) {
  if (!('speechSynthesis' in window)) {
    toast('当前浏览器不支持语音朗读');
    return;
  }
  speechGeneration++;
  const thisGen = speechGeneration;
  window.speechSynthesis.cancel();

  if (activeSpeechButton) {
    activeSpeechButton.classList.remove('speaking');
    activeSpeechButton = null;
  }

  const clean = String(text ?? '').trim();
  if (!clean) return;

  const utter = new SpeechSynthesisUtterance(clean);
  utter.rate = 0.95;
  utter.pitch = 1.0;
  if (malayVoice) {
    utter.voice = malayVoice;
    utter.lang = malayVoice.lang;
  } else {
    utter.lang = 'ms-MY';
  }

  if (buttonEl) {
    activeSpeechButton = buttonEl;
    buttonEl.classList.add('speaking');
  }

  utter.onend = utter.onerror = () => {
    if (thisGen === speechGeneration && buttonEl) {
      buttonEl.classList.remove('speaking');
      if (activeSpeechButton === buttonEl) activeSpeechButton = null;
    }
  };

  window.speechSynthesis.speak(utter);
}

// Worker Setup
const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });

worker.onmessage = event => {
  const msg = event.data;
  if (!msg) return;

  if (msg.type === 'ready') {
    connectionEl.innerHTML = `<i></i> 已就绪 · ${msg.count.toLocaleString()} 词`;
    listStatus.textContent = '';
    search();
  } else if (msg.type === 'results') {
    if (msg.requestId !== state.requestId) return;
    state.isSearching = false;
    state.results = msg.results;
    state.total = msg.total;
    state.totalPages = Math.max(1, Math.ceil(msg.total / pageSize));
    renderWordList();
    renderPagination();
    resultCount.textContent = `找到 ${msg.total.toLocaleString()} 个词条`;
    searchTime.textContent = `${msg.elapsed}ms`;
    listStatus.textContent = msg.total === 0 ? '未找到符合条件的词条' : '';
  } else if (msg.type === 'error') {
    connectionEl.innerHTML = `<i style="background:#ff3b30"></i> 载入错误`;
    listStatus.textContent = msg.message;
    toast(`词库加载失败: ${msg.message}`);
  }
};

worker.postMessage({ type: 'init' });

// Alphabet Bar Generation
function initAlphabetBar() {
  const letters = 'abcdefghijklmnopqrstuvwxyz'.split('');
  alphabetBar.innerHTML = `<button class="alphabet-pill active" data-letter="">全</button>` +
    letters.map(l => `<button class="alphabet-pill" data-letter="${l}">${l.toUpperCase()}</button>`).join('');

  alphabetBar.addEventListener('click', e => {
    const btn = e.target.closest('.alphabet-pill');
    if (!btn) return;
    alphabetBar.querySelectorAll('.alphabet-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.letter = btn.dataset.letter || '';
    state.offset = 0;
    state.page = 1;
    search();
  });
}
initAlphabetBar();

// Search dispatcher
function search() {
  state.requestId++;
  state.isSearching = true;
  listStatus.textContent = '检索中…';
  worker.postMessage({
    type: 'search',
    requestId: state.requestId,
    query: state.query,
    filter: state.filter,
    sort: state.sort,
    letter: state.letter,
    offset: state.offset,
    bookmarks: bookmarkFilter.getAttribute('aria-pressed') === 'true' ? Array.from(bookmarks) : null
  });
}

// Render Word List
function renderWordList() {
  if (!state.results.length) {
    wordList.innerHTML = '';
    wordList.setAttribute('aria-busy', 'false');
    return;
  }

  const selectedNorm = state.selectedWord ? normalizeWord(state.selectedWord) : '';

  wordList.innerHTML = state.results.map((item, idx) => {
    const norm = normalizeWord(item.w);
    const isSelected = norm === selectedNorm;
    const isEnriched = item.e === 1 || item.e === true;
    const stateBadge = isEnriched ? '<span class="badge-gold">★ 8维精编</span>' :
                       (item.st === 's' ? '<span class="badge-source">官方原义</span>' : '<span class="badge-pending">待补</span>');
    const sensesZh = (item.s && item.s.length) ? item.s.join('；') : '释义资料待补';

    return `
      <div class="word-item${isSelected ? ' selected' : ''}" role="option" aria-selected="${isSelected}" data-word="${escapeHtml(item.w)}" data-index="${idx}">
        <div class="word-item-top">
          <strong class="word-head">${escapeHtml(item.w)}</strong>
          ${item.j ? `<span class="jawi-pill" dir="rtl">${escapeHtml(item.j)}</span>` : ''}
          ${stateBadge}
          <span class="rank-badge">#${item.id}</span>
        </div>
        <div class="word-item-bottom">
          <span class="phonetic-text">${escapeHtml(item.p || '')}</span>
          <span class="preview-def">${escapeHtml(sensesZh)}</span>
        </div>
      </div>
    `;
  }).join('');

  wordList.setAttribute('aria-busy', 'false');

  // If nothing is selected, select the first word automatically on desktop
  if (!state.selectedWord && state.results.length > 0 && window.innerWidth > 860) {
    selectWord(state.results[0].w, 0);
  }
}

// Pagination Controls
function renderPagination() {
  pageInput.value = state.page;
  pageInput.max = state.totalPages;
  pageInput.disabled = state.totalPages <= 1;
  pagePrev.disabled = state.page <= 1;
  pageNext.disabled = state.page >= state.totalPages;
  pageTotal.textContent = `/ ${state.totalPages} 页`;
}

pagePrev.onclick = () => {
  if (state.page > 1) {
    state.page--;
    state.offset = (state.page - 1) * pageSize;
    search();
  }
};

pageNext.onclick = () => {
  if (state.page < state.totalPages) {
    state.page++;
    state.offset = (state.page - 1) * pageSize;
    search();
  }
};

pageInput.onchange = () => {
  let p = parseInt(pageInput.value, 10);
  if (isNaN(p) || p < 1) p = 1;
  if (p > state.totalPages) p = state.totalPages;
  state.page = p;
  state.offset = (state.page - 1) * pageSize;
  search();
};

// Select and Load Word Detail
async function selectWord(word, index = -1) {
  window.selectWord = selectWord;
  const norm = normalizeWord(word);
  state.selectedWord = norm;
  state.selectedIndex = index;

  // Highlight list item
  document.querySelectorAll('.word-item').forEach(el => {
    const isCur = normalizeWord(el.dataset.word) === norm;
    el.classList.toggle('selected', isCur);
    el.setAttribute('aria-selected', String(isCur));
  });

  // Mobile drawer support
  if (window.innerWidth <= 860) {
    document.body.classList.add('mobile-detail-open');
  }

  breadcrumb.textContent = `词典 / ${word}`;
  pinnedWord.textContent = word;
  pinnedWord.hidden = false;
  saveBtn.disabled = false;
  copyBtn.disabled = false;
  copyAnkiBtn.disabled = false;
  saveBtn.setAttribute('aria-pressed', String(bookmarks.has(norm)));

  // Load shard from IDB or network
  const letter = shardFor(norm);
  detail.innerHTML = `<div class="loading-detail"><div class="spinner"></div><span>正在调取「${escapeHtml(word)}」八维认知数据…</span></div>`;

  try {
    const res = await loadShard(letter);
    if (!res || !res.shard || !res.shard[norm]) {
      detail.innerHTML = `
        <div class="welcome">
          <h2>词条数据暂缺</h2>
          <p>未能从分片 ${letter}.json 中检索到「${escapeHtml(word)}」的数据。</p>
        </div>
      `;
      return;
    }
    const entryData = res.shard[norm];
    renderDetailCard(entryData);
  } catch (err) {
    detail.innerHTML = `<div class="welcome"><h2>加载出错</h2><p>${escapeHtml(err.message)}</p></div>`;
  }
}

// Word list click delegation
wordList.onclick = event => {
  const item = event.target.closest('.word-item');
  if (!item) return;
  const word = item.dataset.word;
  const idx = parseInt(item.dataset.index, 10);
  selectWord(word, idx);
};

// ============================================================================
// EIGHT-DIMENSION FLAT RENDERER (Section 3.1 & RULES.md)
// 1. Headword, 2. Morphology, 3. Senses, 4. Collocations (in Senses),
// 5. Dual Scenarios, 6. Spoken Shortcuts, 7. Cultural Pragmatics, 8. Deep Etymology
// ZERO accordions, ZERO default-collapsed panels, ZERO hidden tabs!
// ============================================================================
function renderDetailCard(d) {
  const head = d.headword || {};
  const isEnriched = Boolean(d.is_enriched);
  const dataState = d.data_state || (isEnriched ? 'enriched' : 'missing_source');
  const morph = d.morphology || {};
  const senses = d.senses || [];
  const dual = d.dual_scenarios || [];
  const shortcuts = d.spoken_shortcuts || [];
  const prag = d.cultural_pragmatics || d.sociolinguistic_register || {};
  const etym = d.etymology || {};
  const metadata = d.metadata || {};

  // Status Badge
  let statusBadgeHtml = '';
  if (dataState === 'enriched') {
    statusBadgeHtml = `<span class="badge-gold">★ 8维认知精编</span>`;
    if (head.status === 'corpus_usage') {
      statusBadgeHtml += ` <span class="badge-source" title="官方词典未单独收录，保留字幕高频语料用法">官方词典未单独收录 · 保留字幕高频语料用法</span>`;
    } else if (head.status === 'root_derived') {
      statusBadgeHtml += ` <span class="badge-source" title="派生自 DBP 官方词根，本词形释义由构词与语料推导">派生自 DBP 词根 · 构词推导释义</span>`;
    }
  } else if (dataState === 'source_only') {
    const srcName = (d.raw_prpm && d.raw_prpm.source) || 'DBP 官方词典';
    statusBadgeHtml = `<span class="badge-source">${escapeHtml(srcName)} 官方原义</span>`;
  } else {
    statusBadgeHtml = `<span class="badge-pending">词典资料待补</span>`;
  }

  let html = `
    <!-- DIMENSION 1: HEADWORD & PRONUNCIATION -->
    <header class="headword-header">
      <div class="headword-top">
        <h1 class="word-title" lang="ms">${escapeHtml(head.word || d.word)}</h1>
        ${head.jawi ? `<span class="jawi-title" dir="rtl" title="爪夷文拼写">${escapeHtml(head.jawi)}</span>` : '<span class="jawi-pending" title="未取得官方爪夷文资料">Jawi 待补</span>'}
        <div class="headword-actions">
          ${audioButton(head.word || d.word, '朗读单词')}
        </div>
      </div>
      <div class="headword-meta">
        ${head.syllables ? `<span class="meta-pill syllables-pill" title="DBP 正字法音节划分">音节: ${escapeHtml(head.syllables)}</span>` : ''}
        ${head.ipa ? `<span class="meta-pill ipa-pill" title="国际音标 IPA">${escapeHtml(head.ipa)}</span>` : ''}
        ${statusBadgeHtml}
        <span class="meta-pill rank-pill" title="字幕语料词频位序">词频位序: #${d.id}</span>
        ${head.frequency_count ? `<span class="meta-pill count-pill">出现: ${Number(head.frequency_count).toLocaleString()}次</span>` : ''}
      </div>
    </header>
  `;

  // Missing Source Banner
  if (dataState === 'missing_source') {
    html += `
      <div class="notice-banner pending-notice">
        <strong>📌 官方词典收录说明:</strong>
        <p>本词来自马来语高频语料池（位序 #${d.id}），PRPM 尚未检索到 DBP 《Kamus Dewan》或《Kamus Pelajar》的独立词头原文。为保证词库严肃性，本词典不强造伪定义，保留待补状态。</p>
      </div>
    `;
  }

  // Source Only Banner
  if (dataState === 'source_only') {
    html += `
      <div class="notice-banner source-notice">
        <strong>📖 DBP 原始词典数据:</strong>
        <p>本词包含 DBP 官方词典原始条目。构词代数公式、双境对抗、街头缩写及词源深度辨析等认知维度正在排期精编。</p>
      </div>
    `;
  }

  // DIMENSION 2: MORPHOLOGY
  if (morph.formula || morph.root_word || (morph.word_family && morph.word_family.length)) {
    html += `
      <section class="dimension-section morphology-section" aria-label="构词母体">
        <div class="dimension-header">
          <span class="dim-num">02</span>
          <h2>构词母体 · Morphology</h2>
          <span class="dim-badge">代数公式 · 词族芯片</span>
        </div>
        ${morph.formula ? `<div class="morph-formula-box">${escapeHtml(morph.formula)}</div>` : ''}
        ${morph.pattern_note ? `<p class="morph-note">${escapeHtml(morph.pattern_note)}</p>` : ''}
        ${morph.root_word ? `
          <div class="root-container">
            <span class="sub-label">核心词根 (Kata Dasar):</span>
            <button class="family-chip root-chip" data-jump="${escapeHtml(morph.root_word)}">
              <strong>${escapeHtml(morph.root_word)}</strong> ➔
            </button>
          </div>
        ` : ''}
        ${morph.word_family && morph.word_family.length ? `
          <div class="family-container">
            <span class="sub-label">同族派生词芯片 (点击秒切):</span>
            <div class="word-family-grid">
              ${morph.word_family.map(f => `
                <button class="family-chip" data-jump="${escapeHtml(f.word)}">
                  <strong>${escapeHtml(f.word)}</strong>
                  ${f.affix ? `<span class="affix-tag">${escapeHtml(f.affix)}</span>` : ''}
                  ${f.gloss ? `<small>${escapeHtml(f.gloss.split(';')[0])}</small>` : ''}
                </button>
              `).join('')}
            </div>
          </div>
        ` : ''}
      </section>
    `;
  }

  // DIMENSION 3 & 4: SENSES & COLLOCATIONS (Collocations embedded per sense)
  if (senses.length) {
    html += `
      <section class="dimension-section senses-section" aria-label="权威释义与地道搭配">
        <div class="dimension-header">
          <span class="dim-num">03 & 04</span>
          <h2>权威释义与地道搭配 · Senses & Collocations</h2>
          <span class="dim-badge">每义逐条 · 双语搭配</span>
        </div>
        <div class="senses-list">
          ${senses.map(s => {
            const collocs = s.collocations || [];
            return `
              <div class="sense-card" id="sense-${s.id}">
                <div class="sense-header">
                  <span class="sense-index">${String(s.id).padStart(2, '0')}</span>
                  <span class="pos-badge ${escapeHtml(s.pos)}">${escapeHtml(s.pos)}</span>
                  <h3 class="sense-zh-title">${escapeHtml(s.zh_definition || '')}</h3>
                </div>
                ${s.en_definition ? `<p class="sense-en-sub">${escapeHtml(s.en_definition)}</p>` : ''}
                ${s.ms_definition ? `<div class="sense-ms-quote"><span class="quote-label">${head.status === 'corpus_usage' ? '马来语释义 (字幕高频语料用法):' : (head.status === 'root_derived' ? '马来语释义 (基于 DBP 词根推导):' : 'DBP 原文:')}</span> ${escapeHtml(s.ms_definition)}</div>` : ''}
                ${s.nuances ? `<div class="sense-nuance-box">💡 <strong>使用边界:</strong> ${escapeHtml(s.nuances)}</div>` : ''}
                
                <!-- DIMENSION 4: COLLOCATIONS UNDER THIS SENSE -->
                ${collocs.length ? `
                  <div class="collocations-box">
                    <span class="colloc-label">地道搭配 (Collocations):</span>
                    <div class="collocations-grid">
                      ${collocs.map(c => `
                        <div class="collocation-item">
                          <div class="colloc-ms-line">
                            <strong class="colloc-ms">${highlighted(c.ms, head.word || d.word)}</strong>
                            ${audioButton(c.ms, '朗读', true)}
                          </div>
                          <div class="colloc-translations">
                            <span class="colloc-zh">${escapeHtml(c.zh)}</span>
                            ${c.en ? `<span class="colloc-en">${escapeHtml(c.en)}</span>` : ''}
                          </div>
                        </div>
                      `).join('')}
                    </div>
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      </section>
    `;
  }

  // DIMENSION 5: DUAL SCENARIOS (FORMAL VS WHATSAPP)
  if (dual.length) {
    html += `
      <section class="dimension-section scenarios-section" aria-label="双境对抗">
        <div class="dimension-header">
          <span class="dim-num">05</span>
          <h2>双境对抗 · Dual Scenarios</h2>
          <span class="dim-badge">官方正式 ⇄ 街头口语</span>
        </div>
        <div class="scenarios-grid">
          ${dual.map(sc => {
            const isColloquial = sc.scenario === 'colloquial';
            const malayText = isColloquial ? (sc.ms_spoken || sc.ms || '') : (sc.ms || '');
            const messages = isColloquial && sc.messages && sc.messages.length ? sc.messages : null;

            return `
              <div class="scenario-card ${isColloquial ? 'colloquial-card' : 'formal-card'}">
                <div class="scenario-card-header">
                  <span class="scenario-pill">${isColloquial ? '💬 WhatsApp 街头口语' : '📰 Berita 官方书面'}</span>
                  ${sc.context ? `<span class="scenario-context">${escapeHtml(sc.context)}</span>` : ''}
                </div>

                <!-- Messages dialogue turns if present -->
                ${messages ? `
                  <div class="dialogue-messages-stream">
                    ${messages.map(m => `
                      <div class="chat-message-row">
                        <span class="chat-speaker">${escapeHtml(m.speaker)}:</span>
                        <div class="chat-bubble">
                          <p class="bubble-spoken">${escapeHtml(m.ms_spoken)}</p>
                          <p class="bubble-standard"><strong>标准还原:</strong> ${escapeHtml(m.ms_standard)}</p>
                          <p class="bubble-zh">${escapeHtml(m.zh)}</p>
                          ${m.en ? `<p class="bubble-en">${escapeHtml(m.en)}</p>` : ''}
                          <div class="bubble-audio">${audioButton(m.ms_spoken, '听对话', true)}</div>
                        </div>
                      </div>
                    `).join('')}
                  </div>
                ` : `
                  <div class="dialogue-bubble">
                    <p class="bubble-ms">${escapeHtml(malayText)}</p>
                    ${sc.zh ? `<p class="bubble-zh">${escapeHtml(sc.zh)}</p>` : ''}
                    ${sc.en ? `<p class="bubble-en">${escapeHtml(sc.en)}</p>` : ''}
                    ${isColloquial && sc.ms_standard ? `<p class="bubble-standard"><strong>标准还原:</strong> ${escapeHtml(sc.ms_standard)}</p>` : ''}
                    <div class="bubble-audio">${audioButton(malayText, '听例句', true)}</div>
                  </div>
                `}

                ${isColloquial && sc.spoken_features && sc.spoken_features.length ? `
                  <div class="spoken-features-wrap">
                    <span class="feature-label">口语变音特征:</span>
                    <div class="feature-tags">
                      ${sc.spoken_features.map(f => `<span class="feature-tag">${escapeHtml(f)}</span>`).join('')}
                    </div>
                  </div>
                ` : ''}
              </div>
            `;
          }).join('')}
        </div>
      </section>
    `;
  }

  // DIMENSION 6: SPOKEN SHORTCUTS
  if (shortcuts.length || isEnriched) {
    html += `
      <section class="dimension-section shortcuts-section" aria-label="口语速查">
        <div class="dimension-header">
          <span class="dim-num">06</span>
          <h2>口语速查 · Spoken Shortcuts</h2>
          <span class="dim-badge">Bahasa Pasar 吞音缩写</span>
        </div>
        ${shortcuts.length ? `
          <div class="shortcuts-grid">
            ${shortcuts.map(sc => `
              <div class="shortcut-card">
                <div class="shortcut-header">
                  <strong class="shortcut-abbr">${escapeHtml(sc.abbr)}</strong>
                  <span class="shortcut-arrow">➔</span>
                  <span class="shortcut-full">${escapeHtml(sc.full_form)}</span>
                </div>
                ${sc.note ? `<p class="shortcut-note">${escapeHtml(sc.note)}</p>` : ''}
              </div>
            `).join('')}
          </div>
        ` : '<p class="empty-note">暂无常用缩写或变音形式（保留标准书面拼写）</p>'}
      </section>
    `;
  }

  // DIMENSION 7: CULTURAL PRAGMATICS & REGISTER
  const regLevel = prag.register || prag.level || '';
  const politenessNote = prag.politeness_note || prag.usage_notes || '';
  const etiquette = prag.usage_etiquette || (prag.warnings && prag.warnings.length ? prag.warnings.join('；') : '');

  if (regLevel || politenessNote || etiquette) {
    html += `
      <section class="dimension-section pragmatics-section" aria-label="社交礼仪">
        <div class="dimension-header">
          <span class="dim-num">07</span>
          <h2>社交礼仪与称谓避坑 · Cultural Pragmatics</h2>
          <span class="dim-badge">语域礼貌 · 代词防雷</span>
        </div>
        <div class="pragmatics-card">
          ${regLevel ? `<div class="pragmatic-level"><strong>语体归属:</strong> <span class="register-pill">${escapeHtml(regLevel)}</span></div>` : ''}
          ${politenessNote ? `<div class="politeness-box">🤝 <strong>社交距离:</strong> ${escapeHtml(politenessNote)}</div>` : ''}
          ${etiquette ? `
            <div class="etiquette-alert">
              ⚠️ <strong>称谓避坑与礼节禁忌:</strong>
              <p>${escapeHtml(etiquette)}</p>
            </div>
          ` : ''}
        </div>
      </section>
    `;
  }

  // DIMENSION 8: DEEP ETYMOLOGY & COGNITIVE MEMORY ANCHORS
  const etymStory = etym.historical_story || '';
  const etymOrigin = etym.origin || '';
  const etymSource = etym.source_language || '';
  const etymRoot = etym.root_origin || '';
  const etymAid = etym.cognitive_memory_aid || '';

  if (etymStory || etymOrigin || etymSource || etymRoot || etymAid) {
    html += `
      <section class="dimension-section etymology-section" aria-label="深度认知词源">
        <div class="dimension-header">
          <span class="dim-num">08</span>
          <h2>深度认知词源 · Deep Etymology</h2>
          <span class="dim-badge">历史叙事 · 脑图口诀</span>
        </div>
        <div class="etymology-card">
          ${etymStory ? `
            <div class="historical-story-box">
              <h3>📜 词源演变历史叙事</h3>
              <p class="story-text">${escapeHtml(etymStory)}</p>
            </div>
          ` : ''}
          <div class="etymology-meta-row">
            ${etymOrigin ? `<div class="etym-meta-item"><strong>语系溯源:</strong> <span class="origin-pill">${escapeHtml(etymOrigin)}</span></div>` : ''}
            ${etymSource ? `<div class="etym-meta-item"><strong>来源语言:</strong> ${escapeHtml(etymSource)}</div>` : ''}
          </div>
          ${etymRoot ? `<div class="root-origin-box"><strong>考据注记:</strong> ${escapeHtml(etymRoot)}</div>` : ''}
          ${etymAid ? `
            <div class="cognitive-aid-box">
              <h3>🧠 脑图记忆口诀 (区分于史实)</h3>
              <p class="aid-text">${escapeHtml(etymAid)}</p>
            </div>
          ` : ''}
        </div>
      </section>
    `;
  }

  detail.innerHTML = html;
  detail.scrollTop = 0;
  content.scrollTop = 0;
}

// Global Event Delegation for Audio & Jump Chips
document.addEventListener('click', e => {
  // Speech button
  const speakBtn = e.target.closest('[data-speak]');
  if (speakBtn) {
    e.preventDefault();
    e.stopPropagation();
    const text = speakBtn.dataset.speak;
    speakText(text, speakBtn);
    return;
  }

  // Word Jump Chip (e.g., morphology root or word family)
  const jumpChip = e.target.closest('[data-jump]');
  if (jumpChip) {
    e.preventDefault();
    const targetWord = jumpChip.dataset.jump;
    if (targetWord) {
      searchInput.value = targetWord;
      state.query = targetWord;
      state.offset = 0;
      state.page = 1;
      search();
      selectWord(targetWord);
    }
    return;
  }
});

// Search input handlers
let searchDebounce = null;
searchInput.oninput = () => {
  clearButton.hidden = !searchInput.value;
  clearTimeout(searchDebounce);
  searchDebounce = setTimeout(() => {
    state.query = searchInput.value.trim();
    state.offset = 0;
    state.page = 1;
    search();
  }, 120);
};

clearButton.onclick = () => {
  searchInput.value = '';
  clearButton.hidden = true;
  state.query = '';
  state.offset = 0;
  state.page = 1;
  search();
  searchInput.focus();
};

// Filter Buttons
filterButtons.forEach(btn => {
  btn.onclick = () => {
    filterButtons.forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.filter = btn.dataset.filter || '';
    state.offset = 0;
    state.page = 1;
    search();
  };
});

// Sort Order
sortOrder.onchange = () => {
  state.sort = sortOrder.value;
  state.offset = 0;
  state.page = 1;
  search();
};

// Bookmark Filter
bookmarkFilter.onclick = () => {
  const current = bookmarkFilter.getAttribute('aria-pressed') === 'true';
  bookmarkFilter.setAttribute('aria-pressed', String(!current));
  bookmarkFilter.classList.toggle('active', !current);
  state.offset = 0;
  state.page = 1;
  search();
};

// Save Bookmark Action
saveBtn.onclick = () => {
  if (!state.selectedWord) return;
  const w = state.selectedWord;
  if (bookmarks.has(w)) {
    bookmarks.delete(w);
    saveBtn.setAttribute('aria-pressed', 'false');
    toast(`已取消收藏「${w}」`);
  } else {
    bookmarks.add(w);
    saveBtn.setAttribute('aria-pressed', 'true');
    toast(`已收藏「${w}」`);
  }
  writeStorage(BOOKMARKS_KEY, Array.from(bookmarks));
  updateBookmarkCount();
};

// Copy Markdown Action
copyBtn.onclick = () => {
  if (!state.selectedWord) return;
  const entryText = detail.innerText;
  navigator.clipboard.writeText(`# ${state.selectedWord}\n\n${entryText}`).then(() => {
    toast(`已复制「${state.selectedWord}」Markdown 文本`);
  }).catch(() => {
    toast('复制失败，请手动选择');
  });
};

// Copy Anki TSV Action
copyAnkiBtn.onclick = () => {
  if (!state.selectedWord) return;
  const front = state.selectedWord;
  const back = detail.innerText.replace(/\t/g, ' ').replace(/\n/g, '<br>');
  const tsv = `${front}\t${back}`;
  navigator.clipboard.writeText(tsv).then(() => {
    toast(`已复制「${state.selectedWord}」Anki 制表符数据`);
  }).catch(() => {
    toast('复制失败');
  });
};

// Mobile Back Button
backBtn.onclick = () => {
  document.body.classList.remove('mobile-detail-open');
};

// Theme Toggle
function initTheme() {
  const savedTheme = readStorage('open_melayu_theme', 'light');
  document.documentElement.dataset.theme = savedTheme;
}
initTheme();

themeToggle.onclick = () => {
  const isDark = document.documentElement.dataset.theme === 'dark';
  const newTheme = isDark ? 'light' : 'dark';
  document.documentElement.dataset.theme = newTheme;
  writeStorage('open_melayu_theme', newTheme);
  toast(`已切换为${newTheme === 'dark' ? '深色' : '浅色'}主题`);
};

// Keyboard Flow (/ to search, ArrowUp/ArrowDown to select words)
window.addEventListener('keydown', event => {
  // Do NOT hijack input boxes or IME composition
  if (event.isComposing || event.target.matches('input, textarea, [contenteditable]')) {
    if (event.key === 'Escape' && event.target === searchInput) {
      searchInput.blur();
    }
    return;
  }

  // `/` hotkey to focus search
  if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey) {
    event.preventDefault();
    searchInput.focus();
    searchInput.select();
    return;
  }

  // ArrowDown to select next word
  if (event.key === 'ArrowDown') {
    event.preventDefault();
    if (!state.results.length) return;
    let nextIdx = state.selectedIndex + 1;
    if (nextIdx >= state.results.length) nextIdx = state.results.length - 1;
    if (nextIdx !== state.selectedIndex) {
      selectWord(state.results[nextIdx].w, nextIdx);
      const el = wordList.children[nextIdx];
      if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
    return;
  }

  // ArrowUp to select previous word
  if (event.key === 'ArrowUp') {
    event.preventDefault();
    if (!state.results.length) return;
    let prevIdx = state.selectedIndex - 1;
    if (prevIdx < 0) prevIdx = 0;
    if (prevIdx !== state.selectedIndex) {
      selectWord(state.results[prevIdx].w, prevIdx);
      const el = wordList.children[prevIdx];
      if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
    return;
  }

  // Escape to close open dialogs
  if (event.key === 'Escape') {
    if (studyDialog.open) studyDialog.close();
    if (typographyPanel.open) typographyPanel.close();
  }
});

// Flashcard Practice Dialog
dailyBtn.onclick = () => openStudy(true);
practiceBtn.onclick = () => openStudy(false);
closeStudyBtn.onclick = () => studyDialog.close();

function openStudy(dailyOnly = false) {
  if (!state.results.length) {
    toast('词库尚未就绪');
    return;
  }
  state.studyWords = state.results.slice(0, 20);
  state.studyIndex = 0;
  state.studyKnown = 0;
  $('study-total-count').textContent = state.studyWords.length;
  $('study-known-count').textContent = '0';
  renderStudyCard();
  studyDialog.showModal();
}

function renderStudyCard() {
  if (state.studyIndex >= state.studyWords.length) {
    $('study-progress').textContent = '🎉 本轮练习已完成！';
    flashcard.innerHTML = `<div class="card-front"><strong>完成！</strong><p>掌握了 ${state.studyKnown}/${state.studyWords.length} 个词条</p></div>`;
    studyAgainBtn.disabled = true;
    studyKnownBtn.disabled = true;
    return;
  }

  const cur = state.studyWords[state.studyIndex];
  $('study-progress').textContent = `卡片 ${state.studyIndex + 1} / ${state.studyWords.length}`;
  $('card-word').textContent = cur.w;
  $('card-jawi').textContent = cur.j || '';
  $('card-phonetic').textContent = cur.p ? `[${cur.p}]` : '';
  $('card-meaning').innerHTML = `
    <p><strong>释义:</strong> ${(cur.s && cur.s.length) ? cur.s.join('；') : '释义待补'}</p>
    ${cur.r ? `<p style="margin-top:6px;"><strong>词根:</strong> ${cur.r}</p>` : ''}
  `;

  flashcard.querySelector('.card-front').hidden = false;
  flashcard.querySelector('.card-back').hidden = true;
  studyAgainBtn.disabled = false;
  studyKnownBtn.disabled = false;
}

flashcard.onclick = () => {
  const front = flashcard.querySelector('.card-front');
  const back = flashcard.querySelector('.card-back');
  if (front.hidden) {
    front.hidden = false;
    back.hidden = true;
  } else {
    front.hidden = true;
    back.hidden = false;
  }
};

studyAgainBtn.onclick = () => {
  state.studyIndex++;
  renderStudyCard();
};

studyKnownBtn.onclick = () => {
  state.studyKnown++;
  $('study-known-count').textContent = state.studyKnown;
  state.studyIndex++;
  renderStudyCard();
};

studyOpenBtn.onclick = () => {
  const cur = state.studyWords[state.studyIndex];
  if (cur) {
    studyDialog.close();
    selectWord(cur.w);
  }
};

// Typography Settings Dialog
typographyBtn.onclick = () => typographyPanel.showModal();
typographyClose.onclick = () => typographyPanel.close();

typographyIncrease.onclick = () => {
  if (state.fontSize < 140) {
    state.fontSize += 10;
    detail.style.fontSize = `${state.fontSize}%`;
    typographyScale.textContent = `${state.fontSize}%`;
  }
};

typographyDecrease.onclick = () => {
  if (state.fontSize > 80) {
    state.fontSize -= 10;
    detail.style.fontSize = `${state.fontSize}%`;
    typographyScale.textContent = `${state.fontSize}%`;
  }
};

typographyReset.onclick = () => {
  state.fontSize = 100;
  detail.style.fontSize = '100%';
  typographyScale.textContent = '100% · 标准';
};

// Resizer for desktop sidebar width
const resizer = $('resizer');
let isResizing = false;
let startX = 0;
let startWidth = 340;

if (resizer) {
  resizer.addEventListener('pointerdown', e => {
    isResizing = true;
    startX = e.clientX;
    const sidebar = $('word-sidebar');
    startWidth = sidebar ? sidebar.getBoundingClientRect().width : 340;
    resizer.setPointerCapture(e.pointerId);
    document.body.classList.add('resizing');
  });

  resizer.addEventListener('pointermove', e => {
    if (!isResizing) return;
    const dx = e.clientX - startX;
    const newWidth = Math.max(260, Math.min(600, startWidth + dx));
    document.documentElement.style.setProperty('--sidebar-width', `${newWidth}px`);
  });

  function stopResizing() {
    if (isResizing) {
      isResizing = false;
      document.body.classList.remove('resizing');
    }
  }

  resizer.addEventListener('pointerup', stopResizing);
  resizer.addEventListener('pointercancel', stopResizing);
}

console.log(`[Open-Melayu] App Engine v1.0 (${DATA_VERSION}) initialized.`);
