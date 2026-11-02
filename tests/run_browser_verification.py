"""
Comprehensive Browser End-to-End Verification Suite for Open-Melayu (Port 8766)
Tests:
- Eight-dimension flat rendering (no accordions, no hidden tabs)
- Sample verification: saya, dengan, bangunan, belajar, kelihatan, okay, tv
- One source_only (anggap), one missing_source (ayahku)
- Search verification: headword, Chinese meaning, Jawi, root (#root:ajar), slang
- Visual comparison with Open-Lexicon 25K (Port 8765) in same dimensions (1280x800)
- Records evidence and screenshots
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Fix stdout encoding for Windows console
if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = ROOT_DIR / "data" / "audit" / "screenshots"
EVIDENCE_FILE = ROOT_DIR / "data" / "audit" / "browser_verification_evidence.json"
AGENT_BROWSER = r"C:\Users\d\AppData\Roaming\npm\agent-browser.cmd"

def run_ab(session, *args):
    cmd = [AGENT_BROWSER, "--session", session] + list(args)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res.stdout.strip(), res.stderr.strip(), res.returncode

def main():
    print("=== STARTING OPEN-MELAYU BROWSER E2E VERIFICATION ===")
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    evidence = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "build_id": "om-20261102-v1",
        "browser_engine": "agent-browser 0.39.2 (Chromium CDP)",
        "viewport": {"width": 1280, "height": 800},
        "tests": []
    }

    session = "melayu_e2e"

    # Step 1: Initialize 8766 workbench
    print("\n[Step 1] Opening Open-Melayu at http://127.0.0.1:8766...")
    run_ab(session, "open", "http://127.0.0.1:8766")
    run_ab(session, "set", "viewport", "1280", "800")
    run_ab(session, "wait", "2000")

    ss_home = SCREENSHOTS_DIR / "01_home_initial_8766.png"
    run_ab(session, "screenshot", str(ss_home))
    print(f"  Screenshot saved: {ss_home.name}")

    # Step 2: Test Sample 1: saya (Batch 1 upgraded, 8D flat)
    print("\n[Step 2] Testing Sample: saya...")
    run_ab(session, "fill", "#search", "saya")
    run_ab(session, "wait", "500")
    run_ab(session, "click", "#word-list .word-item")
    run_ab(session, "wait", "800")
    ss_saya = SCREENSHOTS_DIR / "02_sample_saya_8D.png"
    run_ab(session, "screenshot", str(ss_saya))
    
    # Eval saya
    eval_js = """
    (() => {
      const text = document.getElementById('detail').innerText;
      return JSON.stringify({
        hasTitle: text.includes('saya'),
        hasJawi: text.includes('ساي'),
        hasCollocations: text.includes('nama saya') && text.includes('rumah saya'),
        hasHistoricalStory: text.includes('sahāya') || text.includes('伴侣、随从'),
        hasWhatsAppDialogue: text.includes('Hafiz') && text.includes('Farah'),
        hasAudioPill: document.querySelectorAll('.audio-pill').length >= 3,
        dimensionCount: document.querySelectorAll('.dimension-section').length
      });
    })()
    """
    out, _, _ = run_ab(session, "eval", eval_js)
    try:
        saya_data = json.loads(out.strip('"').replace('\\"', '"'))
    except Exception:
        saya_data = {"raw": out}
    print("  Evaluation saya:", saya_data)
    evidence["tests"].append({"sample": "saya", "data": saya_data, "screenshot": str(ss_saya.name)})

    # Step 3: Test Sample 2: dengan (Batch 3 upgraded, 14 senses, collocations)
    print("\n[Step 3] Testing Sample: dengan...")
    run_ab(session, "fill", "#search", "dengan")
    run_ab(session, "wait", "500")
    run_ab(session, "click", "#word-list .word-item")
    run_ab(session, "wait", "800")
    ss_dengan = SCREENSHOTS_DIR / "03_sample_dengan_14senses.png"
    run_ab(session, "screenshot", str(ss_dengan))
    
    out, _, _ = run_ab(session, "eval", """
    (() => {
      const text = document.getElementById('detail').innerText;
      const senseCards = document.querySelectorAll('.sense-card').length;
      return JSON.stringify({
        hasTitle: text.includes('dengan'),
        senseCardsCount: senseCards,
        hasHistoricalStory: text.includes('共格') || text.includes('随从、奴仆'),
        hasCollocations: text.includes('pergi dengan kawan') && text.includes('menulis dengan pen'),
        hasWhatsApp: text.includes('Hanim') && text.includes('Najib')
      });
    })()
    """)
    try:
        dengan_data = json.loads(out.strip('"').replace('\\"', '"'))
    except Exception:
        dengan_data = {"raw": out}
    print("  Evaluation dengan:", dengan_data)
    evidence["tests"].append({"sample": "dengan", "data": dengan_data, "screenshot": str(ss_dengan.name)})

    # Step 4: Test Sample 3, 4, 5: Recovered Jawi words (bangunan, belajar, kelihatan)
    for w, expected_jawi in [("bangunan", "باڠونن"), ("belajar", "بلاجر"), ("kelihatan", "کليهتن")]:
        print(f"\n[Step 4] Testing Recovered Jawi Sample: {w} (Expected: {expected_jawi})...")
        run_ab(session, "fill", "#search", w)
        run_ab(session, "wait", "500")
        run_ab(session, "click", "#word-list .word-item")
        run_ab(session, "wait", "800")
        ss_w = SCREENSHOTS_DIR / f"04_recovered_jawi_{w}.png"
        run_ab(session, "screenshot", str(ss_w))
        
        out, _, _ = run_ab(session, "eval", f"""
        (() => {{
          const jawiEl = document.querySelector('.jawi-title');
          const jawiText = jawiEl ? jawiEl.innerText.trim() : '';
          const hasQmark = jawiText.includes('?');
          return JSON.stringify({{
            word: '{w}',
            jawi: jawiText,
            matchesExpected: jawiText === '{expected_jawi}',
            zeroQuestionMarks: !hasQmark && jawiText.length > 0
          }});
        }})()
        """)
        try:
            jawi_res = json.loads(out.strip('"').replace('\\"', '"'))
        except Exception:
            jawi_res = {"raw": out}
        print(f"  Evaluation {w}:", jawi_res)
        evidence["tests"].append({"sample": w, "data": jawi_res, "screenshot": str(ss_w.name)})

    # Step 5: Test Sample 6, 7: okay, tv (Unknown / pending Jawi)
    for w in ["okay", "tv"]:
        print(f"\n[Step 5] Testing Pending / Unknown Jawi Sample: {w}...")
        run_ab(session, "fill", "#search", w)
        run_ab(session, "wait", "500")
        run_ab(session, "click", "#word-list .word-item")
        run_ab(session, "wait", "800")
        ss_w = SCREENSHOTS_DIR / f"05_sample_pending_jawi_{w}.png"
        run_ab(session, "screenshot", str(ss_w))
        
        out, _, _ = run_ab(session, "eval", f"""
        (() => {{
          const text = document.getElementById('detail').innerText;
          const jawiPending = document.querySelector('.jawi-pending');
          return JSON.stringify({{
            word: '{w}',
            hasJawiPending: Boolean(jawiPending),
            noQuestionMarks: !text.includes('????')
          }});
        }})()
        """)
        try:
            pending_res = json.loads(out.strip('"').replace('\\"', '"'))
        except Exception:
            pending_res = {"raw": out}
        print(f"  Evaluation {w}:", pending_res)
        evidence["tests"].append({"sample": w, "data": pending_res, "screenshot": str(ss_w.name)})

    # Step 6: Test Sample 8: source_only (anggap)
    print("\n[Step 6] Testing source_only Sample: anggap...")
    run_ab(session, "fill", "#search", "anggap")
    run_ab(session, "wait", "500")
    run_ab(session, "click", "#word-list .word-item")
    run_ab(session, "wait", "800")
    ss_src = SCREENSHOTS_DIR / "06_sample_source_only_anggap.png"
    run_ab(session, "screenshot", str(ss_src))
    
    out, _, _ = run_ab(session, "eval", """
    (() => {
      const text = document.getElementById('detail').innerText;
      return JSON.stringify({
        hasWord: text.includes('anggap'),
        hasSourceBanner: text.includes('DBP 原始词典数据') || text.includes('DBP Kamus Dewan'),
        hasSenses: document.querySelectorAll('.sense-card').length >= 1,
        notMislabeledAs8D: !text.includes('★ 8维认知精编')
      });
    })()
    """)
    try:
        src_res = json.loads(out.strip('"').replace('\\"', '"'))
    except Exception:
        src_res = {"raw": out}
    print("  Evaluation source_only (anggap):", src_res)
    evidence["tests"].append({"sample": "anggap (source_only)", "data": src_res, "screenshot": str(ss_src.name)})

    # Step 7: Test Sample 9: missing_source (ayahku)
    print("\n[Step 7] Testing missing_source Sample: ayahku...")
    run_ab(session, "fill", "#search", "ayahku")
    run_ab(session, "wait", "500")
    run_ab(session, "click", "#word-list .word-item")
    run_ab(session, "wait", "800")
    ss_missing = SCREENSHOTS_DIR / "07_sample_missing_source_ayahku.png"
    run_ab(session, "screenshot", str(ss_missing))
    
    out, _, _ = run_ab(session, "eval", """
    (() => {
      const text = document.getElementById('detail').innerText;
      return JSON.stringify({
        hasWord: text.includes('ayahku'),
        hasPendingBanner: text.includes('官方词典收录说明') || text.includes('PRPM 尚未检索到 DBP'),
        zeroFakeDefinitions: !text.includes('马来语词汇（语料频次'),
        zeroFakeNuances: !text.includes('DBP 官方马来语词典定义'),
        sensesEmpty: document.querySelectorAll('.sense-card').length === 0
      });
    })()
    """)
    try:
        missing_res = json.loads(out.strip('"').replace('\\"', '"'))
    except Exception:
        missing_res = {"raw": out}
    print("  Evaluation missing_source (ayahku):", missing_res)
    evidence["tests"].append({"sample": "ayahku (missing_source)", "data": missing_res, "screenshot": str(ss_missing.name)})

    # Step 8: Multi-track Search Verification
    print("\n[Step 8] Testing Multi-track Search...")
    search_tests = {}
    
    # 8.1 Chinese search: 我
    run_ab(session, "fill", "#search", "我")
    run_ab(session, "wait", "500")
    out, _, _ = run_ab(session, "eval", """
    (() => {
      const items = Array.from(document.querySelectorAll('.word-head')).slice(0, 5).map(el => el.innerText);
      return JSON.stringify({ query: '我', topWords: items, containsSayaOrAku: items.includes('saya') || items.includes('aku') });
    })()
    """)
    try: search_tests["chinese_search"] = json.loads(out.strip('"').replace('\\"', '"'))
    except: search_tests["chinese_search"] = out
    print("  Chinese search (我):", search_tests["chinese_search"])

    # 8.2 Jawi search: ساي
    run_ab(session, "fill", "#search", "ساي")
    run_ab(session, "wait", "500")
    out, _, _ = run_ab(session, "eval", """
    (() => {
      const items = Array.from(document.querySelectorAll('.word-head')).slice(0, 3).map(el => el.innerText);
      return JSON.stringify({ query: 'ساي', topWords: items, containsSaya: items.includes('saya') });
    })()
    """)
    try: search_tests["jawi_search"] = json.loads(out.strip('"').replace('\\"', '"'))
    except: search_tests["jawi_search"] = out
    print("  Jawi search (ساي):", search_tests["jawi_search"])

    # 8.3 Root search: #root:ajar
    run_ab(session, "fill", "#search", "#root:ajar")
    run_ab(session, "wait", "500")
    out, _, _ = run_ab(session, "eval", """
    (() => {
      const items = Array.from(document.querySelectorAll('.word-head')).slice(0, 5).map(el => el.innerText);
      return JSON.stringify({ query: '#root:ajar', topWords: items, hasAjarFamily: items.includes('ajar') || items.includes('belajar') });
    })()
    """)
    try: search_tests["root_search"] = json.loads(out.strip('"').replace('\\"', '"'))
    except: search_tests["root_search"] = out
    print("  Root search (#root:ajar):", search_tests["root_search"])

    # 8.4 Colloquial slang search: tak
    run_ab(session, "fill", "#search", "tak")
    run_ab(session, "wait", "500")
    out, _, _ = run_ab(session, "eval", """
    (() => {
      const items = Array.from(document.querySelectorAll('.word-head')).slice(0, 5).map(el => el.innerText);
      return JSON.stringify({ query: 'tak', topWords: items, hasTakOrTidak: items.includes('tak') || items.includes('tidak') });
    })()
    """)
    try: search_tests["slang_search"] = json.loads(out.strip('"').replace('\\"', '"'))
    except: search_tests["slang_search"] = out
    print("  Slang search (tak):", search_tests["slang_search"])

    evidence["search_verification"] = search_tests

    # Step 9: Side-by-side Visual Comparison with Open-Lexicon (Port 8765)
    print("\n[Step 9] Taking Side-by-Side Visual Comparison Screenshots (8765 vs 8766)...")
    dict_session = "dict_ref"
    run_ab(dict_session, "open", "http://127.0.0.1:8765")
    run_ab(dict_session, "set", "viewport", "1280", "800")
    run_ab(dict_session, "wait", "2000")
    ss_8765 = SCREENSHOTS_DIR / "08_dict_reference_8765.png"
    run_ab(dict_session, "screenshot", str(ss_8765))
    print(f"  Reference 8765 Screenshot saved: {ss_8765.name}")

    # Return to 8766 home
    run_ab(session, "fill", "#search", "")
    run_ab(session, "wait", "500")
    run_ab(session, "click", "#word-list .word-item")
    run_ab(session, "wait", "800")
    ss_8766_compare = SCREENSHOTS_DIR / "09_open_melayu_compare_8766.png"
    run_ab(session, "screenshot", str(ss_8766_compare))
    print(f"  Melayu 8766 Screenshot saved: {ss_8766_compare.name}")

    # Save evidence JSON
    with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)
    print(f"\n[DONE] Full evidence recorded at: {EVIDENCE_FILE}")

if __name__ == "__main__":
    main()
