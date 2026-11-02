"""
Stage 1 Quality Gate Suite for Open-Melayu
Verifies all 10 criteria for data cleaning, quality gate, and export consistency.
"""

import json
import os
import re
import string
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"
DATA_DIR = ROOT_DIR / "app" / "static" / "data"
SHARDS_DIR = DATA_DIR / "shards"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"

def test_jawi_no_question_marks():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    assert len(files) == 1000, f"Expected 1,000 files, got {len(files)}"
    
    q_jawis = []
    null_jawis = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        j = d.get("headword", {}).get("jawi")
        if j and set(j) == {'?'}:
            q_jawis.append(f.name)
        elif not j:
            null_jawis.append(f.name)
            
    assert len(q_jawis) == 0, f"Found {len(q_jawis)} pure question mark Jawis: {q_jawis[:5]}"
    # Originally 176, minus 3 newly recovered from PRPM (bimbang, ok, panggilan) = 173
    assert len(null_jawis) == 173, f"Expected 173 pending null Jawis, got {len(null_jawis)}"
    print("[PASS] Gate 1: Pure question mark Jawis = 0, Pending null Jawis = 173 (3 newly recovered)")

def test_historical_story_and_collocations():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    missing_story = []
    senses_low_colloc = []
    total_senses = 0
    
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        story = d.get("etymology", {}).get("historical_story")
        if not story or not str(story).strip():
            missing_story.append(f.name)
            
        for s in d.get("senses", []):
            total_senses += 1
            collocs = s.get("collocations", [])
            if len(collocs) < 2:
                senses_low_colloc.append((f.stem, s.get("id"), len(collocs)))
                
    assert len(missing_story) == 0, f"Found {len(missing_story)} words missing historical_story: {missing_story[:5]}"
    assert len(senses_low_colloc) == 0, f"Found {len(senses_low_colloc)} senses with < 2 collocations: {senses_low_colloc[:5]}"
    print(f"[PASS] Gate 2: historical_story missing = 0, low-collocation senses = 0 (Total senses: {total_senses})")

def test_batch_1_to_3_mirror_consistency():
    batch_map = {
        1: ['saya', 'yang', 'aku', 'dia', 'awak', 'kau', 'ini', 'di', 'tak', 'dan'],
        2: ['akan', 'tidak', 'kita', 'apa', 'kamu', 'itu', 'untuk', 'ada', 'boleh', 'mereka'],
        3: ['dengan', 'anda', 'tahu', 'ke', 'kami', 'ya', 'dari', 'dalam', 'sini', 'semua']
    }
    for b_num, words in batch_map.items():
        batch_p = ENRICHED_DIR / f"batch_{b_num}.json"
        with open(batch_p, "r", encoding="utf-8") as fp:
            b_list = json.load(fp)
        assert len(b_list) == 10
        assert [e["headword"]["word"] for e in b_list] == words
        
        for e in b_list:
            w = e["headword"]["word"]
            ind_p = ENRICHED_DIR / f"{w}.json"
            with open(ind_p, "r", encoding="utf-8") as ifp:
                ind_e = json.load(ifp)
            assert e == ind_e, f"Batch {b_num} mismatch with individual file for {w}"
    print("[PASS] Gate 3: Batch 1-3 array mirrors exactly match individual files")

def test_export_three_states_and_clean_placeholders():
    manifest_p = DATA_DIR / "manifest.json"
    with open(manifest_p, "r", encoding="utf-8") as fp:
        manifest = json.load(fp)
        
    assert manifest["total_words"] == 15000
    assert manifest["enriched_count"] == 1000
    assert manifest["source_only_count"] == 7695
    assert manifest["missing_source_count"] == 6305
    assert manifest["conservation_check"] is True
    
    # Check data.js synchronization
    with open(DATA_JS, "r", encoding="utf-8") as fp:
        data_js = fp.read()
    assert f"DATA_VERSION = '{manifest['build_id']}'" in data_js
    
    # Inspect shards for clean missing_source
    letters = list(string.ascii_lowercase) + ["other"]
    total_shard_words = 0
    missing_found = 0
    fake_def_count = 0
    fake_nuance_count = 0
    
    for l in letters:
        shard_p = SHARDS_DIR / f"{l}.json"
        assert shard_p.exists(), f"Shard {l}.json missing"
        with open(shard_p, "r", encoding="utf-8") as fp:
            shard_data = json.load(fp)
        total_shard_words += len(shard_data)
        
        for w, entry in shard_data.items():
            state = entry.get("data_state")
            if state == "missing_source":
                missing_found += 1
                for s in entry.get("senses", []):
                    m_def = s.get("ms_definition", "")
                    if "语料频次" in m_def:
                        fake_def_count += 1
                    if "DBP 官方马来语词典定义" in s.get("nuances", ""):
                        fake_nuance_count += 1
                        
    assert total_shard_words == 15000, f"Expected 15,000 words in shards, got {total_shard_words}"
    assert missing_found == 6305, f"Expected 6305 missing_source, got {missing_found}"
    assert fake_def_count == 0, f"Found {fake_def_count} fake definitions in missing_source"
    assert fake_nuance_count == 0, f"Found {fake_nuance_count} fake DBP nuances in missing_source"
    print("[PASS] Gate 4: Shard three-state conservation verified, 0 fake placeholders/nuances in missing_source")

def test_search_index_consistency():
    idx_p = DATA_DIR / "search_index.json"
    with open(idx_p, "r", encoding="utf-8") as fp:
        idx = json.load(fp)
    assert len(idx) == 15000
    ids = {item["id"] for item in idx}
    words = {item["w"].lower() for item in idx}
    assert len(ids) == 15000, "Duplicate IDs in search index"
    assert len(words) == 15000, "Duplicate words in search index"
    print("[PASS] Gate 5: Search index has 15,000 unique IDs and words")

if __name__ == "__main__":
    test_jawi_no_question_marks()
    test_historical_story_and_collocations()
    test_batch_1_to_3_mirror_consistency()
    test_export_three_states_and_clean_placeholders()
    test_search_index_consistency()
    print("\nALL STAGE 1 QUALITY GATES PASSED 100%!")
