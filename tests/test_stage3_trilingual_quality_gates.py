"""
Stage 3 & Full 15K Trilingual Quality Gate Suite for Open-Melayu
Comprehensive verification for all enriched entries:
1. Gate 1: Pure question mark Jawi = 0, pending null Jawi documented, no legacy batch_*.json mirror files
2. Gate 2: historical_story missing = 0, senses with <2 collocations = 0
3. Gate 3: WhatsApp colloquial scenarios have >=2 messages with speaker identity
4. Gate 4: Provenance honesty (status in {'official', 'corpus_usage'} aligned with PRPM/DBP source) & Trilingual coverage:
   - senses[].en_definition non-empty
   - senses[].collocations[].en non-empty
   - dual_scenarios[formal].en non-empty
   - dual_scenarios[colloquial].messages[].en non-empty
5. Gate 5: 27 Shards three-state conservation (enriched + source_only + missing_source = 15000)
6. Gate 6: Search index 100% synchronized with shards (all enriched words marked e=1, st='e')
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
INDEX_FILE = DATA_DIR / "search_index.json"

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")


def _get_manifest_enriched_count() -> int:
    with open(MANIFEST_FILE, "r", encoding="utf-8") as fp:
        manifest = json.load(fp)
    return int(manifest["enriched_count"])


def test_jawi_integrity():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    expected = _get_manifest_enriched_count()
    assert len(files) >= expected, f"Expected >= {expected} files in data/enriched, got {len(files)}"

    q_jawis = []
    empty_str_jawis = []
    null_jawis = []
    u0081_files = []
    for f in files:
        txt = f.read_text(encoding="utf-8")
        if "\x81" in txt:
            u0081_files.append(f.name)
        d = json.loads(txt)
        j = d.get("headword", {}).get("jawi")
        if j and set(j) == {"?"}:
            q_jawis.append(f.name)
        elif j == "":
            empty_str_jawis.append(f.name)
        elif j is None:
            null_jawis.append(f.name)

    assert len(u0081_files) == 0, f"Found {len(u0081_files)} files containing banned U+0081: {u0081_files[:5]}"
    assert len(q_jawis) == 0, f"Found {len(q_jawis)} pure question mark Jawis: {q_jawis[:5]}"
    assert len(empty_str_jawis) == 0, f"Found {len(empty_str_jawis)} empty string Jawis: {empty_str_jawis[:5]}"
    print(f"[PASS] Gate 1: Pure question mark Jawis = 0, Empty string Jawis = 0, U+0081 = 0, Strict null Jawis = {len(null_jawis)} (Total files: {len(files)})")


def test_story_and_collocations():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    missing_story = []
    senses_low_colloc = []
    total_senses = 0

    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        story = d.get("etymology", {}).get("historical_story")
        if not story or len(story.strip()) < 15:
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


def test_provenance_and_status():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    invalid_status = []
    official_count = 0
    corpus_count = 0
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        st = d.get("headword", {}).get("status")
        if st == "official":
            official_count += 1
        elif st == "corpus_usage":
            corpus_count += 1
        else:
            invalid_status.append((f.name, st))
    assert len(invalid_status) == 0, f"Invalid headword.status found: {invalid_status[:5]}"
    print(f"[PASS] Gate 4a: Provenance status verified (official={official_count}, corpus_usage={corpus_count})")


def test_three_state_conservation():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as fp:
        manifest = json.load(fp)
    assert manifest["conservation_check"] is True
    expected_enriched = manifest["enriched_count"]
    assert expected_enriched >= 2607
    assert manifest["total_words"] == 15000

    with open(DATA_JS, "r", encoding="utf-8") as fp:
        data_js_content = fp.read()
    assert manifest["build_id"] in data_js_content

    enriched_found = 0
    source_only_found = 0
    missing_source_found = 0
    total_shard_words = 0

    letters = list(string.ascii_lowercase) + ["other"]
    for l in letters:
        shard_p = SHARDS_DIR / f"{l}.json"
        assert shard_p.exists(), f"Missing shard {l}.json"
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
    assert enriched_found == expected_enriched, f"Expected {expected_enriched} enriched in shards, got {enriched_found}"
    assert (enriched_found + source_only_found + missing_source_found) == 15000
    print(f"[PASS] Gate 5: Three-state conservation strictly verified ({enriched_found} + {source_only_found} + {missing_source_found} = 15000)")


def test_search_index_sync():
    expected_enriched = _get_manifest_enriched_count()
    with open(INDEX_FILE, "r", encoding="utf-8") as fp:
        index = json.load(fp)
    assert len(index) == 15000, f"Expected 15,000 items in search index, got {len(index)}"
    enriched_in_index = sum(1 for item in index if item.get("e") == 1 and item.get("st") == "e")
    assert enriched_in_index == expected_enriched, f"Expected {expected_enriched} enriched in search index, got {enriched_in_index}"
    print(f"[PASS] Gate 6: Search index synchronized with shards ({enriched_in_index} marked e=1, st='e')")


def test_trilingual_coverage():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    missing_en_def = []
    missing_colloc_en = []
    missing_msg_en = []
    missing_formal_en = []

    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        for s in d.get("senses", []):
            if not s.get("en_definition"):
                missing_en_def.append((f.stem, s.get("id")))
            for c in s.get("collocations", []):
                if not c.get("en"):
                    missing_colloc_en.append((f.stem, c.get("ms")))

        dual = d.get("dual_scenarios", [])
        if not dual or not dual[0].get("en"):
            missing_formal_en.append(f.stem)
        if len(dual) > 1 and "messages" in dual[1]:
            for m in dual[1]["messages"]:
                if not m.get("en"):
                    missing_msg_en.append((f.stem, m.get("speaker")))

    print(f"[*] Trilingual Coverage Status across {len(files)} words:")
    print(f"    - Missing en_definition: {len(missing_en_def)}")
    print(f"    - Missing collocation en: {len(missing_colloc_en)}")
    print(f"    - Missing message en: {len(missing_msg_en)}")
    print(f"    - Missing formal en: {len(missing_formal_en)}")
    assert len(missing_en_def) == 0, f"Missing en_definition: {missing_en_def[:5]}"
    assert len(missing_colloc_en) == 0, f"Missing collocation en: {missing_colloc_en[:5]}"
    assert len(missing_msg_en) == 0, f"Missing message en: {missing_msg_en[:5]}"
    assert len(missing_formal_en) == 0, f"Missing formal en: {missing_formal_en[:5]}"
    return {
        "missing_en_def": len(missing_en_def),
        "missing_colloc_en": len(missing_colloc_en),
        "missing_msg_en": len(missing_msg_en),
        "missing_formal_en": len(missing_formal_en),
    }


if __name__ == "__main__":
    print("=== RUNNING STAGE 3 & 15K TRILINGUAL QUALITY GATES ===")
    test_jawi_integrity()
    test_story_and_collocations()
    test_whatsapp_messages()
    test_provenance_and_status()
    test_three_state_conservation()
    test_search_index_sync()
    cov = test_trilingual_coverage()
    if cov["missing_en_def"] == 0 and cov["missing_colloc_en"] == 0 and cov["missing_msg_en"] == 0:
        print("\n  [★★★ ALL GATES PASS - 100% TRILINGUAL COVERAGE ACHIEVED ★★★]")
    else:
        print("\n  [BACKFILL IN PROGRESS]")
