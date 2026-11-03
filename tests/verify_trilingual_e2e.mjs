import { openBrowser, until } from './browser-harness.mjs';
import fs from 'fs';
import path from 'path';

const ROOT_DIR = path.resolve('.');
const SCREENSHOT_DIR = path.join(ROOT_DIR, 'data', 'audit', 'screenshots');
const EVIDENCE_FILE = path.join(ROOT_DIR, 'data', 'audit', 'cdp_trilingual_e2e_evidence.json');
const MANIFEST_FILE = path.join(ROOT_DIR, 'app', 'static', 'data', 'manifest.json');

if (!fs.existsSync(SCREENSHOT_DIR)) {
  fs.mkdirSync(SCREENSHOT_DIR, { recursive: true });
}

const localManifest = JSON.parse(fs.readFileSync(MANIFEST_FILE, 'utf-8'));
const expectedBuildId = localManifest.build_id;

// Use a fresh project-local profile. Never clear the user's existing databases.
console.log('[*] Launching isolated headless Chrome for build', expectedBuildId);
const browser = await openBrowser();
const { send, evaluate } = browser;
await send('Page.navigate', { url: 'http://127.0.0.1:8766/' });
await until(() => evaluate(`document.querySelectorAll('.word-item').length === 50 && !!document.querySelector('.word-title')`));

// Verify build_id served by HTTP and data.js matches manifest.json
const buildCheck = await send('Runtime.evaluate', {
  expression: `(async () => {
    const mRes = await fetch('/data/manifest.json', { cache: 'no-store' });
    const mJson = await mRes.json();
    const mod = await import('/data.js');
    return { manifestBuildId: mJson.build_id, dataJsVersion: mod.DATA_VERSION };
  })()`,
  awaitPromise: true,
  returnByValue: true
});
const buildInfo = buildCheck.result.value;
console.log('[+] Live build verification:', JSON.stringify(buildInfo));
if (buildInfo.manifestBuildId !== expectedBuildId || buildInfo.dataJsVersion !== expectedBuildId) {
  throw new Error(`Build ID mismatch: expected ${expectedBuildId}, got ${JSON.stringify(buildInfo)}`);
}

const wordResults = [];

async function testWord(word, screenshotName, expectedStatus, expectedQuoteLabel = null) {
  console.log(`\n[*] Testing trilingual word rendering for: #${word} (expectedStatus=${expectedStatus}, expectedQuoteLabel=${expectedQuoteLabel})`);
  await send('Runtime.evaluate', {
    expression: `(async () => {
      const input = document.getElementById('search');
      if (input) {
        input.value = '${word}';
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
      await new Promise(r => setTimeout(r, 300));
      if (typeof window.selectWord === 'function') {
        await window.selectWord('${word}');
      }
    })()`,
    awaitPromise: true
  });
  await new Promise(r => setTimeout(r, 1500));

  const evalResult = await send('Runtime.evaluate', {
    expression: `(() => {
      const title = document.querySelector('.word-title')?.textContent?.trim();
      const jawi = document.querySelector('.jawi-title')?.textContent?.trim() || null;
      const senseEn = document.querySelector('.sense-en-sub')?.textContent?.trim();
      const collocEn = document.querySelector('.colloc-en')?.textContent?.trim();
      const bubbleEn = document.querySelector('.bubble-en')?.textContent?.trim();
      const formalEn = Array.from(document.querySelectorAll('.bubble-en'))[0]?.textContent?.trim() || null;
      const quoteLabels = Array.from(document.querySelectorAll('.quote-label')).map(el => el.textContent.trim());
      const quoteLabel = quoteLabels[0] || null;
      const statusBadge = document.querySelector('.status-badge')?.textContent?.trim() || null;
      const pendingNotice = document.querySelector('.pending-notice')?.textContent?.trim() || null;
      const bubbles = document.querySelectorAll('.chat-bubble').length;
      const collocs = document.querySelectorAll('.collocation-item').length;
      const senseCards = Array.from(document.querySelectorAll('.sense-card'));
      const minCollocsPerSense = senseCards.length ? Math.min(...senseCards.map(sc => sc.querySelectorAll('.collocation-item').length)) : 0;
      return { title, jawi, senseEn, collocEn, bubbleEn, formalEn, quoteLabel, quoteLabels, statusBadge, pendingNotice, bubbles, collocs, minCollocsPerSense };
    })()`,
    returnByValue: true
  });

  const data = evalResult.result.value;
  console.log(`[+] Results for #${word}:`, JSON.stringify(data, null, 2));

  if (data.title !== word) {
    throw new Error(`Expected .word-title '${word}', got '${data.title}'`);
  }

  if (expectedStatus === 'missing_source') {
    if (!data.pendingNotice) {
      throw new Error(`Expected .pending-notice banner on missing_source word #${word}, got none`);
    }
  } else {
    if (!data.senseEn) throw new Error(`sense-en-sub missing on #${word}`);
    if (!data.collocEn) throw new Error(`colloc-en missing on #${word}`);
    if (!data.bubbleEn) throw new Error(`bubble-en missing on #${word}`);
    if (!data.formalEn) throw new Error(`formalEn missing on #${word}`);
    if (data.bubbles < 2) throw new Error(`Expected >= 2 chat bubbles on #${word}, got ${data.bubbles}`);
    if (data.minCollocsPerSense < 2) throw new Error(`Expected >= 2 collocations per sense on #${word}, got min=${data.minCollocsPerSense}`);
    if (!data.quoteLabels || data.quoteLabels.length === 0) {
      throw new Error(`Expected non-empty quoteLabels on #${word}`);
    }
    if (expectedQuoteLabel) {
      for (const ql of data.quoteLabels) {
        if (ql !== expectedQuoteLabel) {
          throw new Error(`Expected all quoteLabels on #${word} to equal '${expectedQuoteLabel}', got ${JSON.stringify(data.quoteLabels)}`);
        }
      }
    }
  }

  const ss = await send('Page.captureScreenshot', { format: 'png' });
  const ssPath = path.join(SCREENSHOT_DIR, screenshotName);
  fs.writeFileSync(ssPath, Buffer.from(ss.data, 'base64'));
  const sizeBytes = fs.statSync(ssPath).size;
  console.log(`[+] Screenshot saved to ${ssPath} (${sizeBytes} bytes)`);
  wordResults.push({ word, expectedStatus, expectedQuoteLabel, screenshotName, sizeBytes, data });
}

let exitCode = 0;
try {
  await testWord('asli', '21_top3000_sample_asli.png', 'official', 'DBP 原文:');
  await testWord('memasak', '22_top3000_sample_memasak.png', 'official', '马来语释义 (基于 DBP 官方词条):');
  await testWord('tajam', '23_top3000_sample_tajam.png', 'official', '马来语释义 (基于 DBP 官方词条):');
  await testWord('anakku', '24_root_derived_anakku.png', 'root_derived', '马来语释义 (基于 DBP 词根推导):');
  await testWord('water', '25_corpus_usage_water.png', 'corpus_usage', '马来语释义 (字幕高频语料用法):');
  await testWord('milan', '26_corpus_usage_milan.png', 'corpus_usage', '马来语释义 (字幕高频语料用法):');
  await testWord('head', '27_salvaged_head.png', 'corpus_usage', '马来语释义 (字幕高频语料用法):');
  await testWord('jaikant', '28_missing_source_jaikant.png', 'missing_source', null);

  fs.writeFileSync(EVIDENCE_FILE, JSON.stringify({
    verified_at: new Date().toISOString(),
    build_id: expectedBuildId,
    live_build_check: buildInfo,
    sample_count: wordResults.length,
    returncode: 0,
    results: wordResults
  }, null, 2), 'utf-8');
  console.log('\n[★] ALL CDP TRILINGUAL SCREENSHOTS & EXACT PROVENANCE ASSERTIONS VERIFIED!');
} catch (err) {
  console.error('\n[!] CDP E2E Assertion Failed:', err);
  exitCode = 1;
} finally {
  await browser.close();
  process.exit(exitCode);
}
