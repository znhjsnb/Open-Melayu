import { spawn } from 'child_process';
import http from 'http';
import fs from 'fs';
import path from 'path';

const SCREENSHOT_DIR = 'C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\screenshots';
const EVIDENCE_FILE = 'C:\\Users\\d\\Documents\\open-melayu\\data\\audit\\browser_verification_evidence.json';
const CHROME_PATH = 'C:\\Users\\d\\.agent-browser\\browsers\\chrome-156.0.8078.47\\chrome.exe';
const PORT = 9455;

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

console.log('[E2E] Starting headless Chrome on port ' + PORT + '...');
const chrome = spawn(CHROME_PATH, [
  '--headless=new',
  `--remote-debugging-port=${PORT}`,
  '--user-data-dir=C:\\Users\\d\\.agent-browser\\poc-profile-full3',
  '--disable-gpu',
  '--window-size=1280,800',
  'about:blank'
]);

await new Promise(r => setTimeout(r, 1600));

// Get websocket debugger URL
const targets = await new Promise((resolve, reject) => {
  http.get(`http://127.0.0.1:${PORT}/json/list`, res => {
    let d = '';
    res.on('data', c => d += c);
    res.on('end', () => resolve(JSON.parse(d)));
  }).on('error', reject);
});

const pageTarget = targets.find(t => t.type === 'page');
if (!pageTarget) throw new Error('No page target found');

const ws = new WebSocket(pageTarget.webSocketDebuggerUrl);
let idCounter = 1;
const pending = new Map();
let loadFired = false;

ws.onmessage = event => {
  const msg = JSON.parse(event.data);
  if (msg.method === 'Page.loadEventFired') {
    loadFired = true;
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

async function navigate(url) {
  loadFired = false;
  await send('Page.navigate', { url });
  const start = Date.now();
  while (!loadFired && Date.now() - start < 10000) {
    await new Promise(r => setTimeout(r, 100));
  }
  await new Promise(r => setTimeout(r, 800));
}

async function evalJs(expr) {
  const res = await send('Runtime.evaluate', { expression: expr, returnByValue: true });
  if (res.exceptionDetails) {
    throw new Error(`Eval error: ${res.exceptionDetails.text} (${JSON.stringify(res.exceptionDetails)})`);
  }
  return res.result?.value;
}

async function screenshot(filename) {
  const outPath = path.join(SCREENSHOT_DIR, filename);
  const res = await send('Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(outPath, Buffer.from(res.data, 'base64'));
  console.log(`[E2E] Screenshot saved: ${filename}`);
  return outPath;
}

async function waitForCondition(checkFn, timeoutMs = 12000, intervalMs = 200) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    try {
      const ok = await checkFn();
      if (ok) return true;
    } catch {}
    await new Promise(r => setTimeout(r, intervalMs));
  }
  return false;
}

const auditEvidence = {
  timestamp: new Date().toISOString(),
  environment: {
    browser: 'Chrome 156.0.8078.47 (Headless CDP)',
    viewport: { width: 1280, height: 800 },
    endpoints: {
      open_melayu: 'http://127.0.0.1:8766',
      dict_reference: 'http://127.0.0.1:8765'
    }
  },
  tests: {},
  screenshots: {}
};

try {
  await send('Page.enable');
  await send('Runtime.enable');

  // =========================================================================
  // Test 1: Home page initial render and index loading
  // =========================================================================
  console.log('\n--- Test 1: Home page initial load ---');
  await navigate('http://127.0.0.1:8766/');
  
  // Wait for index to load and connection text to show "已就绪"
  const readyOk = await waitForCondition(async () => {
    const text = await evalJs(`document.getElementById('connection')?.innerText || ''`);
    return text.includes('已就绪') || text.includes('15,000');
  }, 15000);

  // Wait for 50 items to render
  const itemsOk = await waitForCondition(async () => {
    const count = await evalJs(`document.querySelectorAll('.word-item').length`);
    return count === 50;
  }, 10000);

  const pageTitle = await evalJs(`document.title`);
  const wordCount = await evalJs(`document.querySelectorAll('.word-item').length`);
  const firstWord = await evalJs(`document.querySelector('.word-item strong')?.textContent`);
  const connectionText = await evalJs(`document.getElementById('connection')?.innerText`);

  console.log(`Title: ${pageTitle}`);
  console.log(`Items rendered: ${wordCount}`);
  console.log(`First word: ${firstWord}`);
  console.log(`Connection: ${connectionText}`);

  auditEvidence.tests.test1_home = {
    title: pageTitle,
    itemsRendered: wordCount,
    firstWord,
    connectionText,
    passed: readyOk && itemsOk && wordCount === 50
  };
  auditEvidence.screenshots.home = await screenshot('01_home_screen.png');

  // Helper function to search and select a word
  async function searchAndSelect(targetWord) {
    await evalJs(`(() => {
      const input = document.getElementById('search');
      input.value = ${JSON.stringify(targetWord)};
      input.dispatchEvent(new Event('input', { bubbles: true }));
    })()`);

    // Wait for the word to appear in the list
    await waitForCondition(async () => {
      const hasItem = await evalJs(`Boolean(document.querySelector('.word-item[data-word="${targetWord}"]'))`);
      return hasItem;
    }, 6000);

    // Click the item
    await evalJs(`(() => {
      const item = document.querySelector('.word-item[data-word="${targetWord}"]');
      if (item) item.click();
    })()`);

    // Wait for detail card to render with word-title matching targetWord
    await waitForCondition(async () => {
      const head = await evalJs(`document.querySelector('.word-title')?.textContent`);
      return head === targetWord;
    }, 6000);
  }

  // =========================================================================
  // Test 2: Sample 'saya' (8-Dimension Full Flat Render, 4 Collocations, Story)
  // =========================================================================
  console.log('\n--- Test 2: Sample "saya" (8-Dimension Flat Render) ---');
  await searchAndSelect('saya');

  const sayaData = await evalJs(`(() => {
    const head = document.querySelector('.word-title')?.textContent || '';
    const jawi = document.querySelector('.jawi-title')?.textContent || '';
    const ipa = document.querySelector('.ipa-pill')?.textContent || '';
    const audioPills = document.querySelectorAll('.audio-pill').length;
    const senses = document.querySelectorAll('.sense-card').length;
    const collocations = document.querySelectorAll('.collocation-item').length;
    const story = document.querySelector('.story-text')?.textContent || '';
    const memory = document.querySelector('.aid-text')?.textContent || '';
    const chatBubbles = document.querySelectorAll('.chat-bubble').length;
    const hasAccordion = document.querySelectorAll('details, .accordion').length > 0;
    const badge = document.querySelector('.badge-gold')?.textContent || '';
    const formulaCard = document.querySelector('.morph-formula-box')?.textContent || '';

    return {
      head,
      jawi,
      ipa,
      audioPills,
      senses,
      collocations,
      storyLength: story.length,
      memoryLength: memory.length,
      chatBubbles,
      hasAccordion,
      badge,
      hasFormula: formulaCard.length > 0
    };
  })()`);

  console.log('saya evaluation:', sayaData);
  auditEvidence.tests.test2_saya = {
    ...sayaData,
    passed: sayaData.head === 'saya' &&
            sayaData.jawi === 'ساي' &&
            sayaData.senses === 2 &&
            sayaData.collocations >= 4 &&
            sayaData.storyLength > 50 &&
            sayaData.chatBubbles >= 2 &&
            !sayaData.hasAccordion &&
            sayaData.audioPills >= 5
  };
  auditEvidence.screenshots.saya = await screenshot('02_sample_saya_8D.png');

  // =========================================================================
  // Test 3: Sample 'dengan' (14 Senses, 28 Collocations, Historical Story)
  // =========================================================================
  console.log('\n--- Test 3: Sample "dengan" (14 Senses & 28 Collocations) ---');
  await searchAndSelect('dengan');

  const denganData = await evalJs(`(() => {
    const head = document.querySelector('.word-title')?.textContent || '';
    const senses = document.querySelectorAll('.sense-card').length;
    const collocations = document.querySelectorAll('.collocation-item').length;
    const story = document.querySelector('.story-text')?.textContent || '';
    const chatBubbles = document.querySelectorAll('.chat-bubble').length;
    return { head, senses, collocations, storyLength: story.length, chatBubbles };
  })()`);

  console.log('dengan evaluation:', denganData);
  auditEvidence.tests.test3_dengan = {
    ...denganData,
    passed: denganData.head === 'dengan' &&
            denganData.senses === 14 &&
            denganData.collocations === 28 &&
            denganData.storyLength > 50
  };
  auditEvidence.screenshots.dengan = await screenshot('03_sample_dengan_14senses.png');

  // =========================================================================
  // Test 4: Recovered Jawi ('bangunan', 'belajar', 'kelihatan')
  // =========================================================================
  console.log('\n--- Test 4: Recovered Jawi (0 question marks) ---');
  const jawiResults = {};
  for (const word of ['bangunan', 'belajar', 'kelihatan']) {
    await searchAndSelect(word);
    const jawi = await evalJs(`document.querySelector('.jawi-title')?.textContent || ''`);
    jawiResults[word] = jawi;
    console.log(`Word: ${word} -> Jawi: ${jawi}`);
  }

  auditEvidence.tests.test4_recovered_jawi = {
    jawiResults,
    passed: jawiResults['bangunan'] === 'باڠونن' &&
            jawiResults['belajar'] === 'بلاجر' &&
            jawiResults['kelihatan'] === 'کليهتن'
  };
  auditEvidence.screenshots.recovered_jawi = await screenshot('04_sample_bangunan_jawi.png');

  // =========================================================================
  // Test 5: Pending Jawi ('okay', 'tv')
  // =========================================================================
  console.log('\n--- Test 5: Pending Jawi ("okay", "tv") ---');
  const pendingJawiResults = {};
  for (const word of ['okay', 'tv']) {
    await searchAndSelect(word);
    const jawiHtml = await evalJs(`document.querySelector('.jawi-pending')?.outerHTML || ''`);
    const isPending = jawiHtml.includes('待补') || jawiHtml.includes('pending');
    pendingJawiResults[word] = { jawiHtml, isPending };
    console.log(`Word: ${word} -> isPending: ${isPending}`);
  }

  auditEvidence.tests.test5_pending_jawi = {
    pendingJawiResults,
    passed: pendingJawiResults['okay'].isPending && pendingJawiResults['tv'].isPending
  };
  auditEvidence.screenshots.pending_jawi = await screenshot('05_sample_okay_pending_jawi.png');

  // =========================================================================
  // Test 6: Source_only sample ('anggap')
  // =========================================================================
  console.log('\n--- Test 6: Source_only sample ("anggap") ---');
  await searchAndSelect('anggap');

  const anggapData = await evalJs(`(() => {
    const badge = document.querySelector('.badge-source')?.textContent || '';
    const defOfficial = document.querySelector('.sense-ms-quote')?.textContent || '';
    const notice = document.querySelector('.source-notice')?.textContent || '';
    return { badge, defOfficial: defOfficial.slice(0, 60), notice: notice.slice(0, 60) };
  })()`);
  console.log('anggap evaluation:', anggapData);

  auditEvidence.tests.test6_source_only = {
    ...anggapData,
    passed: anggapData.badge.includes('官方原义') && Boolean(anggapData.defOfficial)
  };
  auditEvidence.screenshots.source_only = await screenshot('06_sample_anggap_source_only.png');

  // =========================================================================
  // Test 7: Missing_source sample ('ayahku')
  // =========================================================================
  console.log('\n--- Test 7: Missing_source sample ("ayahku") ---');
  await searchAndSelect('ayahku');

  const ayahkuData = await evalJs(`(() => {
    const badge = document.querySelector('.badge-pending')?.textContent || '';
    const hasFakeDef = document.body.innerText.includes('语料频次');
    const fakeOfficialBadge = Boolean(document.querySelector('.badge-source'));
    const notice = document.querySelector('.pending-notice')?.textContent || '';
    return { badge, hasFakeDef, fakeOfficialBadge, notice: notice.slice(0, 60) };
  })()`);
  console.log('ayahku evaluation:', ayahkuData);

  auditEvidence.tests.test7_missing_source = {
    ...ayahkuData,
    passed: ayahkuData.badge.includes('待补') && !ayahkuData.hasFakeDef && !ayahkuData.fakeOfficialBadge
  };
  auditEvidence.screenshots.missing_source = await screenshot('07_sample_ayahku_missing_source.png');

  // =========================================================================
  // Test 8: Multi-track Search (Chinese, Jawi, #root, Slang)
  // =========================================================================
  console.log('\n--- Test 8: Multi-track Search ---');
  const searchTracks = {};

  // Track A: Chinese '我'
  await evalJs(`(() => {
    const input = document.getElementById('search');
    input.value = '我';
    input.dispatchEvent(new Event('input', { bubbles: true }));
  })()`);
  await new Promise(r => setTimeout(r, 600));
  const chineseTopWords = await evalJs(`Array.from(document.querySelectorAll('.word-item strong')).slice(0, 5).map(e => e.textContent)`);
  searchTracks.chinese = { query: '我', topWords: chineseTopWords, matched: chineseTopWords.includes('saya') || chineseTopWords.includes('aku') };

  // Track B: Jawi 'ساي'
  await evalJs(`(() => {
    const input = document.getElementById('search');
    input.value = 'ساي';
    input.dispatchEvent(new Event('input', { bubbles: true }));
  })()`);
  await new Promise(r => setTimeout(r, 600));
  const jawiTopWords = await evalJs(`Array.from(document.querySelectorAll('.word-item strong')).slice(0, 5).map(e => e.textContent)`);
  searchTracks.jawi = { query: 'ساي', topWords: jawiTopWords, matched: jawiTopWords[0] === 'saya' };

  // Track C: Root '#root:ajar'
  await evalJs(`(() => {
    const input = document.getElementById('search');
    input.value = '#root:ajar';
    input.dispatchEvent(new Event('input', { bubbles: true }));
  })()`);
  await new Promise(r => setTimeout(r, 600));
  const rootTopWords = await evalJs(`Array.from(document.querySelectorAll('.word-item strong')).slice(0, 5).map(e => e.textContent)`);
  searchTracks.root = { query: '#root:ajar', topWords: rootTopWords, matched: rootTopWords.includes('belajar') || rootTopWords.includes('pelajar') };

  // Track D: Slang shortcut 'tak'
  await evalJs(`(() => {
    const input = document.getElementById('search');
    input.value = 'tak';
    input.dispatchEvent(new Event('input', { bubbles: true }));
  })()`);
  await new Promise(r => setTimeout(r, 600));
  const slangTopWords = await evalJs(`Array.from(document.querySelectorAll('.word-item strong')).slice(0, 5).map(e => e.textContent)`);
  searchTracks.slang = { query: 'tak', topWords: slangTopWords, matched: slangTopWords.includes('tidak') || slangTopWords.includes('tak') };

  console.log('Search tracks:', searchTracks);
  auditEvidence.tests.test8_search_tracks = {
    ...searchTracks,
    passed: searchTracks.chinese.matched && searchTracks.jawi.matched && searchTracks.root.matched && searchTracks.slang.matched
  };

  // =========================================================================
  // Test 9: Visual Comparison between Reference (8765) and Open-Melayu (8766)
  // =========================================================================
  console.log('\n--- Test 9: Visual Comparison 8765 vs 8766 ---');
  // 1. Reference 8765 (Open-Lexicon 25K)
  await navigate('http://127.0.0.1:8765/');
  await new Promise(r => setTimeout(r, 2000));
  auditEvidence.screenshots.reference_8765 = await screenshot('08_dict_reference_8765.png');

  // 2. Open-Melayu 8766
  await navigate('http://127.0.0.1:8766/');
  await waitForCondition(async () => {
    const count = await evalJs(`document.querySelectorAll('.word-item').length`);
    return count >= 50;
  });
  await searchAndSelect('saya');
  await new Promise(r => setTimeout(r, 1000));
  auditEvidence.screenshots.open_melayu_8766 = await screenshot('09_open_melayu_compare_8766.png');

  // All tests passed?
  const allPassed = Object.values(auditEvidence.tests).every(t => t.passed);
  auditEvidence.overall_passed = allPassed;
  console.log(`\n======================================================`);
  console.log(`ALL TESTS PASSED: ${allPassed ? 'YES (100% GREEN)' : 'NO'}`);
  console.log(`======================================================`);

} catch (err) {
  console.error('[E2E ERROR]:', err);
  auditEvidence.error = err.message;
} finally {
  fs.writeFileSync(EVIDENCE_FILE, JSON.stringify(auditEvidence, null, 2), 'utf-8');
  console.log(`[E2E] Evidence recorded to: ${EVIDENCE_FILE}`);
  ws.close();
  chrome.kill();
  process.exit(auditEvidence.overall_passed ? 0 : 1);
}
