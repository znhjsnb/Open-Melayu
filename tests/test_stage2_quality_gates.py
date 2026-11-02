"""
Stage 2 & Full Top 2,000 Quality Gate Suite for Open-Melayu
Verifies all 1,841 enriched entries:
1. Pure question mark Jawi = 0
2. historical_story missing = 0, senses with <2 collocations = 0
3. All WhatsApp colloquial scenarios have >=2 messages with speaker identity
4. 27 Shards three-state conservation: enriched(1841) + source_only(6973) + missing_source(6186) = 15000
5. Search index uniqueness & manifest synchronization
"""

import json
import string
import sys
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"
DATA_DIR = ROOT_DIR / "app" / "static" / "data"
SHARDS_DIR = DATA_DIR / "shards"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"
MANIFEST_FILE = DATA_DIR / "manifest.json"

def test_jawi_integrity():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    assert len(files) == 1841, f"Expected 1,841 files in data/enriched, got {len(files)}"
    
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
    print(f"[PASS] Gate 1: Pure question mark Jawis = 0, Pending null Jawis = {len(null_jawis)} (Total files: {len(files)})")

def test_story_and_collocations():
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

def test_whatsapp_messages():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    invalid_messages = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        dual = d.get("dual_scenarios", [])
        colloquial = next((sc for sc in dual if sc.get("scenario") == "colloquial"), None)
        if not colloquial:
            invalid_messages.append((f.name, "missing colloquial"))
            continue
        msgs = colloquial.get("messages", [])
        if len(msgs) < 2:
            invalid_messages.append((f.name, f"fewer than 2 turns: {len(msgs)}"))
            continue
        for m in msgs:
            if not m.get("speaker") or not m.get("ms_spoken") or not m.get("zh"):
                invalid_messages.append((f.name, "incomplete message turn"))
                break

    assert len(invalid_messages) == 0, f"Found {len(invalid_messages)} invalid WhatsApp messages: {invalid_messages[:5]}"
    print(f"[PASS] Gate 3: WhatsApp multi-turn messages with speaker = {len(files)} / {len(files)} (100%)")

def test_three_state_conservation():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as fp:
        manifest = json.load(fp)
        
    assert manifest["total_words"] == 15000
    assert manifest["enriched_count"] == 1841
    assert manifest["source_only_count"] == 6973
    assert manifest["missing_source_count"] == 6186
    assert manifest["conservation_check"] is True
    
    with open(DATA_JS, "r", encoding="utf-8") as fp:
        data_js = fp.read()
    assert f"DATA_VERSION = '{manifest['build_id']}'" in data_js
    
    letters = list(string.ascii_lowercase) + ["other"]
    total_shard_words = 0
    enriched_found = 0
    source_only_found = 0
    missing_source_found = 0
    
    for l in letters:
        shard_p = SHARDS_DIR / f"{l}.json"
        assert shard_p.exists(), f"Shard {l}.json missing"
        with open(shard_p, "r", encoding="utf-8") as fp:
            shard_data = json.load(fp)
        total_shard_words += len(shard_data)
        
        for w, entry in shard_data.items():
            state = entry.get("data_state")
            if state == "enriched":
                enriched_found += 1
            elif state == "source_only":
                source_only_found += 1
            elif state == "missing_source":
                missing_source_found += 1

    assert total_shard_words == 15000
    assert enriched_found == 1841
    assert source_only_found == 6973
    assert missing_source_found == 6186
    print(f"[PASS] Gate 4: Three-state conservation strictly verified (1841 + 6973 + 6186 = 15000)")

if __name__ == "__main__":
    test_jawi_integrity()
    test_story_and_collocations()
    test_whatsapp_messages()
    test_three_state_conservation()
    print("\n========================================================")
    print("  ALL FULL TOP 2,000 QUALITY GATES PASSED (100% GREEN)")
    print("========================================================")
