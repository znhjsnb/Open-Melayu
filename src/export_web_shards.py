"""
Open-Melayu Web Shards & Search Index Generator
Compiles 15,000 words into lightweight search index and 27 alphabetical detail shards.
Strictly adheres to:
- C01: Three-state accounting (enriched, source_only, missing_source = 15,000)
- C03: Manifest with immutable build_id versioning and atomic commit
- C05/B05: Windows reserved name protection (_reserved_con.json)
- C07: Multi-track search index (headword, jawi, syllables, root, slang aliases, Chinese senses)
- Project Handoff Section 4 A3 & A4:
  - Clean missing_source (no pseudo definitions, no fake DBP badges, frequency in metadata)
  - Distinguish source_only actual source (Kamus Dewan vs Kamus Pelajar vs PRPM raw)
  - Synchronize data.js DATA_VERSION with manifest BUILD_ID
  - Atomic release: validate all assets before switching manifest pointer
"""

import datetime
import json
import os
import re
import string
import sys
from pathlib import Path

# Safe encoding for Windows
if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
CANDIDATES_PATH = ROOT_DIR / "data" / "candidate_pool_15k.json"
PRPM_RAW_DIR = ROOT_DIR / "data" / "prpm_raw"
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"
OUTPUT_DIR = ROOT_DIR / "app" / "static" / "data"
SHARDS_DIR = OUTPUT_DIR / "shards"
DATA_JS_PATH = ROOT_DIR / "app" / "static" / "data.js"

WINDOWS_RESERVED = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2'}
BUILD_ID = "om-20261102-v1"

def clean_dbp_definition(raw_text):
    if not raw_text:
        return []
    clean = re.sub(r'<[^>]+>', ' ', raw_text)
    clean = clean.replace('\x81', '').replace('\xad', '')
    lines = [line.strip() for line in clean.split('\n') if line.strip()]
    cleaned_senses = []
    for line in lines:
        if line.startswith("Kamus Dewan") or line.startswith("Kamus Pelajar") or line.startswith("Definisi :"):
            continue
        if len(line) > 5:
            cleaned_senses.append(line)
    return cleaned_senses[:6]

def clean_jawi(jawi_str):
    if not jawi_str:
        return None
    cleaned = jawi_str.replace('\x81', '').replace('\xad', '').strip()
    if not cleaned or set(cleaned) == {'?'}:
        return None
    return cleaned

def export_shards():
    print(f"=== OPEN-MELAYU EXPORT & GATE PROTOCOL ===")
    print(f"Target Build ID: {BUILD_ID}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SHARDS_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Loading candidate pool: {CANDIDATES_PATH}")
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        candidates = json.load(f)
    print(f"Total candidates in pool: {len(candidates)}")
    assert len(candidates) == 15000, f"Expected 15,000 candidates, got {len(candidates)}"

    # 1. Load all enriched individual files (skip batch_* arrays)
    enriched_map = {}
    if ENRICHED_DIR.exists():
        for p in sorted(ENRICHED_DIR.glob("*.json")):
            if p.name.startswith("batch_"):
                continue
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and "headword" in data:
                    w = data["headword"]["word"].strip().lower()
                    enriched_map[w] = data
            except Exception as e:
                print(f"Warning loading enriched {p.name}: {e}")

    print(f"Loaded 8-dimension enriched words: {len(enriched_map)}")
    assert len(enriched_map) == 1000, f"Expected 1,000 enriched words, got {len(enriched_map)}"

    # 2. Fast in-memory index of PRPM raw directory
    print("Indexing PRPM raw directory in memory...")
    prpm_files = {}
    if PRPM_RAW_DIR.exists():
        with os.scandir(PRPM_RAW_DIR) as it:
            for entry in it:
                if entry.name.endswith(".json") and entry.is_file():
                    prpm_files[entry.name] = entry.path
    print(f"Indexed {len(prpm_files)} raw PRPM files.")

    # 3. Iterate candidates and classify into three states with strict checks
    search_index = []
    shards = {letter: {} for letter in string.ascii_lowercase}
    shards["other"] = {}

    count_enriched = 0
    count_source_only = 0
    count_missing = 0

    pending_enriched_words = {"joe", "me", "oliver"}

    for item in candidates:
        wid = item["rank"]
        word = item["word"].strip()
        word_lower = word.lower()

        first_char = word_lower[0] if word_lower and word_lower[0] in string.ascii_lowercase else "other"

        if word_lower in enriched_map:
            count_enriched += 1
            enr_data = enriched_map[word_lower]
            head = enr_data.get("headword", {})
            morph = enr_data.get("morphology", {})
            senses = enr_data.get("senses", [])

            # Normalize pragmatics & sociolinguistic_register (must be equal)
            pragmatics = enr_data.get("cultural_pragmatics") or enr_data.get("sociolinguistic_register") or {}
            
            # Quality status
            quality_status = "pending" if word_lower in pending_enriched_words else "passed"

            senses_summary = [s.get("zh_definition", "") for s in senses if s.get("zh_definition")]
            if not senses_summary:
                senses_summary = [s.get("ms_definition", "") for s in senses if s.get("ms_definition")]

            # Ensure jawi is cleaned and not pure question marks
            jawi_val = clean_jawi(head.get("jawi"))
            head["jawi"] = jawi_val

            search_index.append({
                "id": wid,
                "w": word,
                "j": jawi_val or "",
                "p": head.get("ipa", "") or head.get("syllables", ""),
                "r": morph.get("root_word", ""),
                "a": item.get("colloquial_expansion") or "",
                "s": senses_summary[:3],
                "e": 1,
                "st": "e"
            })

            shards[first_char][word_lower] = {
                "id": wid,
                "word": word,
                "is_enriched": True,
                "data_state": "enriched",
                "headword": head,
                "morphology": morph,
                "senses": senses,
                "dual_scenarios": enr_data.get("dual_scenarios", []),
                "spoken_shortcuts": enr_data.get("spoken_shortcuts", []),
                "cultural_pragmatics": pragmatics,
                "sociolinguistic_register": pragmatics,
                "etymology": enr_data.get("etymology", {}),
                "tags": item.get("tags", []),
                "metadata": {
                    "schema_version": "om-8d-1",
                    "quality_status": quality_status,
                    "frequency_rank": wid,
                    "frequency_count": item.get("frequency_count", 0)
                }
            }

        else:
            prpm_file_name = f"_reserved_{word_lower}.json" if word_lower in WINDOWS_RESERVED else f"{word_lower}.json"
            prpm_file_path = prpm_files.get(prpm_file_name)
            prpm_data = None
            if prpm_file_path:
                try:
                    with open(prpm_file_path, "r", encoding="utf-8") as f:
                        prpm_data = json.load(f)
                except Exception:
                    pass

            has_kd = bool(prpm_data and prpm_data.get("kamus_dewan"))
            has_kp = bool(prpm_data and prpm_data.get("kamus_pelajar"))
            has_raw_def = bool(prpm_data and prpm_data.get("raw_definitions"))
            has_prpm_defs = prpm_data and (has_kd or has_kp or has_raw_def)

            if has_prpm_defs:
                count_source_only += 1
                state = "source_only"
                jawi = clean_jawi(prpm_data.get("jawi"))
                syllables = prpm_data.get("syllables") or None

                # Determine actual source
                if has_kd:
                    source_label = "DBP Kamus Dewan"
                    defs = clean_dbp_definition(prpm_data.get("kamus_dewan"))
                    nuance_text = "DBP Kamus Dewan 原始释义（未经人工精编）"
                elif has_kp:
                    source_label = "DBP Kamus Pelajar"
                    defs = clean_dbp_definition(prpm_data.get("kamus_pelajar"))
                    nuance_text = "DBP Kamus Pelajar 原始释义（未经人工精编）"
                else:
                    source_label = "PRPM 词典数据"
                    defs = prpm_data.get("raw_definitions", [])
                    nuance_text = "PRPM 原始词典数据（待核验来源）"

                if not defs:
                    defs = ["（未提取到分条释义文本）"]

                senses_list = [
                    {
                        "id": idx + 1,
                        "pos": item.get("pos_kaikki") or "kata",
                        "zh_definition": "",
                        "ms_definition": d,
                        "nuances": nuance_text,
                        "collocations": []
                    }
                    for idx, d in enumerate(defs[:5])
                ]

                search_index.append({
                    "id": wid,
                    "w": word,
                    "j": jawi or "",
                    "p": syllables or item.get("ipa", "") or "",
                    "r": item.get("root_word") or "",
                    "a": item.get("colloquial_expansion") or "",
                    "s": defs[:2],
                    "e": 0,
                    "st": "s"
                })

                shards[first_char][word_lower] = {
                    "id": wid,
                    "word": word,
                    "is_enriched": False,
                    "data_state": "source_only",
                    "headword": {
                        "word": word,
                        "jawi": jawi,
                        "syllables": syllables,
                        "ipa": item.get("ipa") or None,
                        "frequency_rank": wid
                    },
                    "morphology": {
                        "is_root": item.get("root_word") is None or item.get("root_word") == word,
                        "root_word": item.get("root_word") or word,
                        "formula": None
                    },
                    "senses": senses_list,
                    "dual_scenarios": [],
                    "spoken_shortcuts": [],
                    "cultural_pragmatics": {},
                    "sociolinguistic_register": {},
                    "etymology": {
                        "origin": None,
                        "source_language": None,
                        "root_origin": "",
                        "historical_story": "",
                        "cognitive_memory_aid": ""
                    },
                    "raw_prpm": {
                        "source": source_label,
                        "kamus_dewan": prpm_data.get("kamus_dewan") if prpm_data else None,
                        "kamus_pelajar": prpm_data.get("kamus_pelajar") if prpm_data else None,
                    } if prpm_data else None,
                    "tags": item.get("tags", []),
                    "metadata": {
                        "schema_version": "om-8d-1",
                        "quality_status": "source_only",
                        "source": source_label,
                        "frequency_rank": wid,
                        "frequency_count": item.get("frequency_count", 0)
                    }
                }

            else:
                count_missing += 1
                state = "missing_source"
                jawi = None
                syllables = None

                search_index.append({
                    "id": wid,
                    "w": word,
                    "j": "",
                    "p": item.get("ipa", "") or "",
                    "r": item.get("root_word") or "",
                    "a": item.get("colloquial_expansion") or "",
                    "s": ["（官方词典资料待补）"],
                    "e": 0,
                    "st": "m"
                })

                # Strict A3: No fake definitions, no fake DBP nuances, frequency in metadata
                shards[first_char][word_lower] = {
                    "id": wid,
                    "word": word,
                    "is_enriched": False,
                    "data_state": "missing_source",
                    "headword": {
                        "word": word,
                        "jawi": None,
                        "syllables": None,
                        "ipa": item.get("ipa") or None,
                        "frequency_rank": wid
                    },
                    "morphology": {
                        "is_root": item.get("root_word") is None or item.get("root_word") == word,
                        "root_word": item.get("root_word") or word,
                        "formula": None
                    },
                    "senses": [],
                    "dual_scenarios": [],
                    "spoken_shortcuts": [],
                    "cultural_pragmatics": {},
                    "sociolinguistic_register": {},
                    "etymology": {
                        "origin": None,
                        "source_language": None,
                        "root_origin": "",
                        "historical_story": "",
                        "cognitive_memory_aid": ""
                    },
                    "raw_prpm": None,
                    "tags": item.get("tags", []),
                    "metadata": {
                        "schema_version": "om-8d-1",
                        "quality_status": "pending",
                        "source": "missing_source",
                        "notes": "未取得 DBP 或权威词典公开释义",
                        "frequency_rank": wid,
                        "frequency_count": item.get("frequency_count", 0)
                    }
                }

    # 4. Atomic release verification before manifest switch (C01)
    print("\nVerifying three-state conservation (C01)...")
    total_classified = count_enriched + count_source_only + count_missing
    print(f"  - 8D Enriched:   {count_enriched}")
    print(f"  - Source-Only:   {count_source_only}")
    print(f"  - Missing Source:{count_missing}")
    print(f"  - Total:         {total_classified} / {len(candidates)}")
    assert total_classified == len(candidates), f"Conservation failed: {total_classified} != {len(candidates)}"
    assert count_enriched == 1000, f"Expected 1000 enriched words, got {count_enriched}"
    assert count_source_only == 7695, f"Expected 7695 source_only words, got {count_source_only}"
    assert count_missing == 6305, f"Expected 6305 missing words, got {count_missing}"

    # 5. Write Shards atomically
    print("\nWriting shards to disk...")
    total_shard_words = 0
    for letter, shard_data in shards.items():
        if not shard_data:
            continue
        shard_file = SHARDS_DIR / f"{letter}.json"
        tmp_shard = shard_file.with_suffix(".json.tmp")
        with open(tmp_shard, "w", encoding="utf-8") as f:
            json.dump(shard_data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp_shard, shard_file)
        total_shard_words += len(shard_data)

    print(f"Written 27 shards covering {total_shard_words} words.")
    assert total_shard_words == len(candidates), f"Shard word count mismatch: {total_shard_words} != {len(candidates)}"

    # 6. Write search_index.json atomically
    index_file = OUTPUT_DIR / "search_index.json"
    tmp_index = index_file.with_suffix(".json.tmp")
    print(f"Writing search index to {index_file}...")
    with open(tmp_index, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, separators=(",", ":"))
    os.replace(tmp_index, index_file)
    index_bytes = index_file.stat().st_size
    index_mb = index_bytes / (1024 * 1024)
    print(f"Search index size: {index_bytes} bytes ({index_mb:.2f} MiB)")
    assert len(search_index) == len(candidates), f"Search index count mismatch: {len(search_index)} != {len(candidates)}"

    # 7. Write manifest.json LAST (pointer switch)
    manifest = {
        "build_id": BUILD_ID,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_words": len(candidates),
        "enriched_count": count_enriched,
        "source_only_count": count_source_only,
        "missing_source_count": count_missing,
        "conservation_check": total_classified == len(candidates)
    }

    manifest_file = OUTPUT_DIR / "manifest.json"
    tmp_manifest = manifest_file.with_suffix(".json.tmp")
    with open(tmp_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    os.replace(tmp_manifest, manifest_file)
    print(f"Manifest written and switched to {BUILD_ID}.")

    # 8. Synchronize app/static/data.js
    data_js_content = f"""// Open-Melayu Data Specification & Cache Version
export const DATA_VERSION = '{BUILD_ID}';
export const INDEX_CACHE = `open-melayu-index-${{DATA_VERSION}}`;
export const SHELL_CACHE = `open-melayu-shell-${{DATA_VERSION}}`;

export function normalizeWord(word) {{
  return String(word ?? '').trim().toLowerCase();
}}

export function shardFor(word) {{
  const norm = normalizeWord(word);
  const first = norm.charAt(0);
  return /^[a-z]$/.test(first) ? first : 'other';
}}
"""
    with open(DATA_JS_PATH, "w", encoding="utf-8") as f:
        f.write(data_js_content)
    print(f"Synchronized {DATA_JS_PATH} with DATA_VERSION = {BUILD_ID}.")

    print("================ BUILD COMPLETE & VERIFIED ================")
    print(f"Build ID: {BUILD_ID}")
    print(f"Total Words: {len(candidates)} (Conserved: {manifest['conservation_check']})")
    print(f"  - 8D Enriched:    {count_enriched}")
    print(f"  - DBP Source-Only:{count_source_only}")
    print(f"  - Missing Source: {count_missing}")
    print(f"Shards written: {len(shards)} covering {total_shard_words} words.")
    print("============================================================")

if __name__ == "__main__":
    export_shards()
