"""
Recover 64 pure question mark Jawis in data/enriched/*.json from data/prpm_raw/.
Adheres strictly to PROJECT_HANDOFF.md Section 4 A1.
"""

import json
import os
import sys
from pathlib import Path

# Safe encoding for Windows console
if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"
PRPM_RAW_DIR = ROOT_DIR / "data" / "prpm_raw"
AUDIT_LOG_PATH = ROOT_DIR / "data" / "audit" / "jawi_64_recovery_evidence.json"

WINDOWS_RESERVED = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2'}

def clean_jawi_string(raw_val: str) -> str:
    if not raw_val:
        return ""
    # Strip whitespace and unprintable control characters like \x81 or soft hyphens
    cleaned = raw_val.strip()
    cleaned = cleaned.replace('\x81', '').replace('\xad', '').strip()
    return cleaned

def main():
    print("Step 1: Identifying words with pure question mark Jawi...")
    all_files = sorted(ENRICHED_DIR.glob("*.json"))
    word_files = [f for f in all_files if not f.name.startswith("batch_")]
    print(f"Total individual enriched word files: {len(word_files)}")

    qmark_targets = []
    for f in word_files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        jawi = d.get("headword", {}).get("jawi")
        if jawi and set(jawi) == {'?'}:
            qmark_targets.append((f.stem, f, jawi))

    print(f"Found {len(qmark_targets)} words with pure question mark Jawi.")
    assert len(qmark_targets) == 64, f"Expected 64 words, found {len(qmark_targets)}"

    recovery_records = []
    recovered_count = 0

    for word, file_path, old_jawi in qmark_targets:
        # Determine raw file path
        raw_name = f"_reserved_{word}.json" if word.lower() in WINDOWS_RESERVED else f"{word}.json"
        raw_path = PRPM_RAW_DIR / raw_name

        if not raw_path.exists():
            print(f"ERROR: Raw PRPM file not found for {word}: {raw_path}")
            recovery_records.append({
                "word": word,
                "old_jawi": old_jawi,
                "new_jawi": None,
                "status": "failed_missing_raw",
                "raw_path": str(raw_path.relative_to(ROOT_DIR))
            })
            continue

        with open(raw_path, "r", encoding="utf-8") as rfp:
            raw_data = json.load(fp=rfp)

        raw_jawi = raw_data.get("jawi")
        if not raw_jawi:
            print(f"WARNING: Raw PRPM jawi is empty for {word}")
            recovery_records.append({
                "word": word,
                "old_jawi": old_jawi,
                "new_jawi": None,
                "status": "failed_empty_raw_jawi",
                "raw_path": str(raw_path.relative_to(ROOT_DIR))
            })
            continue

        cleaned_jawi = clean_jawi_string(raw_jawi)
        if not cleaned_jawi or set(cleaned_jawi) == {'?'}:
            print(f"WARNING: Cleaned jawi is invalid for {word}: {cleaned_jawi!r}")
            recovery_records.append({
                "word": word,
                "old_jawi": old_jawi,
                "new_jawi": cleaned_jawi,
                "status": "failed_cleaned_still_invalid",
                "raw_path": str(raw_path.relative_to(ROOT_DIR))
            })
            continue

        # Load enriched file, update jawi
        with open(file_path, "r", encoding="utf-8") as efp:
            enriched_content = json.load(efp)

        enriched_content["headword"]["jawi"] = cleaned_jawi

        # Atomic write
        temp_file = file_path.with_suffix(".json.tmp")
        with open(temp_file, "w", encoding="utf-8") as tfp:
            json.dump(enriched_content, tfp, ensure_ascii=False, indent=2)
            tfp.write("\n")

        # Verify temp file
        with open(temp_file, "r", encoding="utf-8") as vfp:
            verified = json.load(vfp)
            assert verified["headword"]["jawi"] == cleaned_jawi

        os.replace(temp_file, file_path)
        recovered_count += 1
        recovery_records.append({
            "word": word,
            "old_jawi": old_jawi,
            "new_jawi": cleaned_jawi,
            "status": "recovered",
            "raw_path": str(raw_path.relative_to(ROOT_DIR)),
            "prpm_headword": raw_data.get("headword") or raw_data.get("word")
        })

    print(f"Successfully recovered {recovered_count}/{len(qmark_targets)} Jawi entries.")

    # Write audit log
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG_PATH, "w", encoding="utf-8") as afp:
        json.dump({
            "total_targeted": len(qmark_targets),
            "recovered_count": recovered_count,
            "records": recovery_records
        }, afp, ensure_ascii=False, indent=2)
    print(f"Audit log written to: {AUDIT_LOG_PATH}")

    # Post-validation: ensure 0 pure question mark Jawis remaining
    remaining_qmark = 0
    remaining_null = 0
    for f in word_files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        j = d.get("headword", {}).get("jawi")
        if j and set(j) == {'?'}:
            remaining_qmark += 1
        elif j is None or j == "":
            remaining_null += 1

    print(f"Validation result across all 1,000 files:")
    print(f"  - Pure question mark Jawis remaining: {remaining_qmark}")
    print(f"  - Null/empty Jawis (pending): {remaining_null}")
    assert remaining_qmark == 0, f"Remaining question mark Jawis should be 0, found {remaining_qmark}"
    assert remaining_null == 176, f"Expected 176 null Jawis, found {remaining_null}"
    print("ALL 64 JAWI ENTRIES VERIFIED AND ZERO QUESTION MARKS REMAINING!")

if __name__ == "__main__":
    main()
