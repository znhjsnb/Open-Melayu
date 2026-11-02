"""
Apply fixes for the remaining defects in Open-Melayu 1,000 enriched entries:
1. Recover valid DBP Jawi for bimbang, ok, panggilan
2. Normalize empty strings to null for joe, me
3. Add transparent ms_definition editorial notice for foreign loanwords joe, me, oliver
"""

import json
import os
import sys

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ENRICHED_DIR = r"C:\Users\d\Documents\open-melayu\data\enriched"

fixes = [
    {
        "word": "bimbang",
        "action": "recover_jawi",
        "jawi": "\u0628\u064a\u0645\u0628\u06a0",  # بيمبڠ
        "source": "PRPM Kamus Dewan"
    },
    {
        "word": "ok",
        "action": "recover_jawi",
        "jawi": "\u0627\u0621\u0648\u0642",  # اءوق
        "source": "PRPM Kamus Dewan"
    },
    {
        "word": "panggilan",
        "action": "recover_jawi",
        "jawi": "\u06a4\u06a0\u06af\u064a\u0644\u0646",  # ڤڠݢيلن
        "source": "PRPM Kamus Dewan"
    },
    {
        "word": "joe",
        "action": "specify_ms_def",
        "ms_def": "DBP 官方词典未单独收录此人名/外来词条，保留字幕高频语料用法与音译。"
    },
    {
        "word": "me",
        "action": "specify_ms_def",
        "ms_def": "DBP 官方词典未单独收录此代词/外来词条，保留字幕高频语料用法与释义。"
    },
    {
        "word": "oliver",
        "action": "specify_ms_def",
        "ms_def": "DBP 官方词典未单独收录此人名/外来词条，保留字幕高频语料用法与音译。"
    }
]

audit_log = []

for item in fixes:
    word = item["word"]
    fpath = os.path.join(ENRICHED_DIR, f"{word}.json")
    if not os.path.exists(fpath):
        print(f"Error: {fpath} does not exist!")
        continue
    
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    old_state = json.loads(json.dumps(data))
    
    if item["action"] == "recover_jawi":
        data["headword"]["jawi"] = item["jawi"]
        audit_log.append({
            "word": word,
            "field": "headword.jawi",
            "old_value": old_state["headword"].get("jawi"),
            "new_value": item["jawi"],
            "source": item["source"]
        })
        print(f"[{word}] Recovered Jawi -> {item['jawi']}")

    elif item["action"] == "specify_ms_def":
        if "senses" in data and len(data["senses"]) > 0:
            data["senses"][0]["ms_definition"] = item["ms_def"]
        # Also ensure empty string jawi/syllables are normalized to null
        if data["headword"].get("jawi") == "":
            data["headword"]["jawi"] = None
        if data["headword"].get("syllables") == "":
            data["headword"]["syllables"] = None

        audit_log.append({
            "word": word,
            "field": "senses[0].ms_definition",
            "old_value": old_state["senses"][0].get("ms_definition"),
            "new_value": item["ms_def"],
            "normalization": "jawi/syllables normalized to null"
        })
        print(f"[{word}] Added transparent ms_definition and normalized empty strings.")

    # Write back with explicit UTF-8
    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

log_path = r"C:\Users\d\Documents\open-melayu\data\audit\remaining_defects_fix_evidence.json"
with open(log_path, "w", encoding="utf-8") as f:
    json.dump(audit_log, f, ensure_ascii=False, indent=2)

print(f"\nSaved fix evidence to: {log_path}")
