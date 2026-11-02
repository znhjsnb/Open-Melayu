"""
Activate and link official DBP root Jawi for the 96 derived words.
Adds morphology.root_jawi and enriches morphology.pattern_note and headword.jawi_note.
"""

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = r"C:\Users\d\Documents\open-melayu"
DEEP_SCAN_PATH = os.path.join(ROOT_DIR, "data", "audit", "deep_scan_upgrade_needed.json")
ENRICHED_DIR = os.path.join(ROOT_DIR, "data", "enriched")

with open(DEEP_SCAN_PATH, "r", encoding="utf-8") as f:
    scan_data = json.load(f)

items = scan_data.get("null_jawi_with_root_jawi_available", [])
print(f"Total derived words to link with root Jawi: {len(items)}")

updated = []

for it in items:
    word = it["word"]
    root = it["root"]
    root_jawi = it["root_jawi"]
    affix = it.get("affix") or "派生词缀"

    fpath = os.path.join(ENRICHED_DIR, f"{word}.json")
    if not os.path.exists(fpath):
        continue

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Update morphology
    morph = data.setdefault("morphology", {})
    morph["root_jawi"] = root_jawi

    cur_note = morph.get("pattern_note", "")
    addition = f"核心词根（Kata Dasar）「{root}」官方爪夷文为「{root_jawi}」，派生附加 {affix}。"
    if addition not in cur_note:
        morph["pattern_note"] = f"{cur_note} {addition}".strip()

    # 2. Update headword note
    head = data.setdefault("headword", {})
    head["jawi_note"] = f"词根爪夷文: {root_jawi} ({root})"

    # Write back UTF-8
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    updated.append({
        "word": word,
        "root": root,
        "root_jawi": root_jawi,
        "affix": affix
    })

evidence_path = os.path.join(ROOT_DIR, "data", "audit", "root_jawi_96_evidence.json")
with open(evidence_path, "w", encoding="utf-8") as f:
    json.dump(updated, f, ensure_ascii=False, indent=2)

print(f"Successfully activated root Jawi for {len(updated)} words.")
print(f"Evidence saved to: {evidence_path}")
