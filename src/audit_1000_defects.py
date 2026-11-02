"""
Exhaustive defect audit for all 1,000 enriched entries in Open-Melayu.
Scans for:
1. Missing or pending Jawi (null, empty, question marks, non-arabic chars)
2. Syllables null or empty
3. Senses missing ms_definition or zh_definition
4. Senses with fewer than 2 collocations
5. Missing or short historical_story / etymology
6. Missing cultural_pragmatics / sociolinguistic_register conflict
7. Control characters or malformed strings
8. Words like joe, me, oliver status
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

print(f"Total word files to audit: {len(word_files)}")

defects = {
    "question_mark_jawi": [],
    "null_jawi": [],
    "null_jawi_with_prpm_available": [],  # PRPM has Jawi, but enriched is null!
    "null_syllables": [],
    "null_syllables_with_prpm_available": [], # PRPM has syllables, but enriched is null!
    "senses_missing_ms_def": [],
    "senses_fewer_than_2_collocations": [],
    "missing_historical_story": [],
    "short_historical_story": [],
    "register_pragmatics_conflict": [],
    "control_characters": [],
    "specific_watch_words": {}
}

arabic_pattern = re.compile(r"[\u0600-\u06ff\u0750-\u077f\u08a0-\u08ff]")

for fpath in word_files:
    fname = os.path.basename(fpath)
    word = fname[:-5]
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            d = json.load(f)
    except Exception as e:
        print(f"Error loading {fname}: {e}")
        continue

    head = d.get("headword", {})
    jawi = head.get("jawi")
    syllables = head.get("syllables")
    senses = d.get("senses", [])
    prag = d.get("cultural_pragmatics")
    reg = d.get("sociolinguistic_register")
    etym = d.get("etymology", {})
    story = etym.get("historical_story") if etym else None

    # Check Jawi
    if jawi is not None:
        if isinstance(jawi, str):
            if "?" in jawi or "？" in jawi:
                defects["question_mark_jawi"].append((word, jawi))
    else:
        defects["null_jawi"].append(word)
        # Check if PRPM raw cache actually has Jawi for this word!
        prpm_path = os.path.join(PRPM_DIR, f"{word}.json")
        if os.path.exists(prpm_path):
            try:
                with open(prpm_path, "r", encoding="utf-8") as pf:
                    pdata = json.load(pf)
                pj = pdata.get("jawi") or (pdata.get("prpm") and pdata.get("prpm").get("jawi"))
                if pj and isinstance(pj, str) and arabic_pattern.search(pj) and "?" not in pj:
                    defects["null_jawi_with_prpm_available"].append((word, pj))
            except:
                pass

    # Check Syllables
    if not syllables:
        defects["null_syllables"].append(word)
        prpm_path = os.path.join(PRPM_DIR, f"{word}.json")
        if os.path.exists(prpm_path):
            try:
                with open(prpm_path, "r", encoding="utf-8") as pf:
                    pdata = json.load(pf)
                psy = pdata.get("syllables") or (pdata.get("prpm") and pdata.get("prpm").get("syllables"))
                if psy and isinstance(psy, str) and "." in psy:
                    defects["null_syllables_with_prpm_available"].append((word, psy))
            except:
                pass

    # Check Senses
    for s in senses:
        sid = s.get("id")
        ms_def = s.get("ms_definition")
        zh_def = s.get("zh_definition")
        collocs = s.get("collocations", [])

        if not ms_def or not ms_def.strip():
            defects["senses_missing_ms_def"].append((word, sid))
        if len(collocs) < 2:
            defects["senses_fewer_than_2_collocations"].append((word, sid, len(collocs)))

    # Check Historical Story
    if not story or not story.strip():
        defects["missing_historical_story"].append(word)
    elif len(story.strip()) < 30:
        defects["short_historical_story"].append((word, len(story.strip())))

    # Check Pragmatics & Register
    if prag and reg:
        if prag != reg:
            defects["register_pragmatics_conflict"].append(word)

    # Check Control Chars in raw json string
    with open(fpath, "r", encoding="utf-8") as f:
        raw_text = f.read()
    for ch in ["\x80", "\x81", "\x82", "\x83", "\x84", "\x85", "\x86", "\x87", "\x88", "\x89", "\x8a", "\x8b", "\x8c", "\x8d", "\x8e", "\x8f"]:
        if ch in raw_text:
            defects["control_characters"].append((word, hex(ord(ch))))

    # Watch words
    if word in ["joe", "me", "oliver", "okay", "tv", "tenaga"]:
        defects["specific_watch_words"][word] = {
            "jawi": jawi,
            "syllables": syllables,
            "senses_count": len(senses),
            "senses_missing_ms": [s.get("id") for s in senses if not s.get("ms_definition")],
            "has_story": bool(story)
        }

print("\n" + "="*50)
print("AUDIT SUMMARY REPORT")
print("="*50)
print(f"1. Question mark Jawi: {len(defects['question_mark_jawi'])}")
print(f"2. Null Jawi total: {len(defects['null_jawi'])}")
print(f"   -> PRPM actually HAS valid Jawi (Recoverable!): {len(defects['null_jawi_with_prpm_available'])}")
print(f"   -> Truly pending in PRPM: {len(defects['null_jawi']) - len(defects['null_jawi_with_prpm_available'])}")
print(f"3. Null Syllables total: {len(defects['null_syllables'])}")
print(f"   -> PRPM actually HAS syllables (Recoverable!): {len(defects['null_syllables_with_prpm_available'])}")
print(f"4. Senses missing ms_definition: {len(defects['senses_missing_ms_def'])}")
print(f"5. Senses with < 2 collocations: {len(defects['senses_fewer_than_2_collocations'])}")
print(f"6. Missing historical story: {len(defects['missing_historical_story'])}")
print(f"7. Short historical story (<30 chars): {len(defects['short_historical_story'])}")
print(f"8. Register/Pragmatics conflict: {len(defects['register_pragmatics_conflict'])}")
print(f"9. Hidden control characters: {len(defects['control_characters'])}")
print("10. Specific watch words:", json.dumps(defects["specific_watch_words"], ensure_ascii=False, indent=2))

out_file = r"C:\Users\d\Documents\open-melayu\data\audit\detailed_1000_defects.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(defects, f, ensure_ascii=False, indent=2)
print(f"\nSaved detailed findings to: {out_file}")
