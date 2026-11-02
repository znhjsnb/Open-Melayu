"""
Deep scan of all 1,000 enriched entries in Open-Melayu to identify:
1. Missing `messages` in colloquial dual_scenarios (still legacy single-sentence dialog)
2. Words where headword.jawi is null, BUT its root word (Kata Dasar) actually has official DBP Jawi!
3. Historical stories that are generic or templated (<60 chars or matching boilerplate)
4. Overall list of entries that require Codex CLI targeted quality enhancement.
"""

import json
import glob
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ENRICHED_DIR = r"C:\Users\d\Documents\open-melayu\data\enriched"
PRPM_DIR = r"C:\Users\d\Documents\open-melayu\data\prpm_raw"

files = sorted(glob.glob(os.path.join(ENRICHED_DIR, "*.json")))
word_files = [f for f in files if not os.path.basename(f).startswith("batch_")]

report = {
    "legacy_single_sentence_dialogs": [],
    "dialogs_with_messages": [],
    "null_jawi_with_root_jawi_available": [],
    "generic_stories": [],
    "total_words_needing_upgrade": set()
}

arabic_pattern = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")

for fpath in word_files:
    fname = os.path.basename(fpath)
    word = fname[:-5]
    with open(fpath, "r", encoding="utf-8") as f:
        d = json.load(f)

    head = d.get("headword", {})
    morph = d.get("morphology", {})
    dual = d.get("dual_scenarios", [])
    etym = d.get("etymology", {})
    story = etym.get("historical_story", "") if etym else ""

    # 1. Check dual scenarios messages
    has_messages = False
    for sc in dual:
        if sc.get("scenario") == "colloquial":
            if sc.get("messages") and len(sc.get("messages")) >= 2:
                has_messages = True
            break
    
    if has_messages:
        report["dialogs_with_messages"].append(word)
    else:
        report["legacy_single_sentence_dialogs"].append(word)
        report["total_words_needing_upgrade"].add(word)

    # 2. Check null Jawi with root word Jawi
    jawi = head.get("jawi")
    if not jawi:
        root = morph.get("root_word")
        if root and root != word:
            # Check PRPM for root word!
            root_prpm = os.path.join(PRPM_DIR, f"{root}.json")
            if os.path.exists(root_prpm):
                try:
                    with open(root_prpm, "r", encoding="utf-8") as rf:
                        rdata = json.load(rf)
                    rj = rdata.get("jawi") or (rdata.get("prpm") and rdata.get("prpm").get("jawi"))
                    if rj and isinstance(rj, str) and arabic_pattern.search(rj) and "?" not in rj:
                        report["null_jawi_with_root_jawi_available"].append({
                            "word": word,
                            "root": root,
                            "root_jawi": rj,
                            "affix": morph.get("affix")
                        })
                except:
                    pass

    # 3. Check historical story length & quality
    if len(story) < 60 or "未明" in story or "暂无详细借词历史" in story:
        report["generic_stories"].append({
            "word": word,
            "story": story[:80]
        })

print(f"Total entries scanned: {len(word_files)}")
print(f"1. Modern multi-turn messages dialogs: {len(report['dialogs_with_messages'])}")
print(f"2. Legacy single-sentence dialogs (NEED CODEX UPGRADE): {len(report['legacy_single_sentence_dialogs'])}")
print(f"3. Null Jawi with valid ROOT Jawi available in PRPM: {len(report['null_jawi_with_root_jawi_available'])}")
print(f"4. Generic/short historical stories: {len(report['generic_stories'])}")
print(f"5. Total unique words needing upgrade: {len(report['total_words_needing_upgrade'])}")

out_path = r"C:\Users\d\Documents\open-melayu\data\audit\deep_scan_upgrade_needed.json"
# Convert set to sorted list for json
report["total_words_needing_upgrade"] = sorted(list(report["total_words_needing_upgrade"]))
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

print(f"Deep scan report saved to: {out_path}")
