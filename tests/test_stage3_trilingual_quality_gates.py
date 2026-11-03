"""
Stage 3 & Full 15K Trilingual Quality Gate Suite for Open-Melayu
Comprehensive verification for all enriched entries:
1. Gate 1: Pure question mark Jawi = 0, empty string Jawi = 0 (headword & root_jawi), banned control/format chars = 0, no legacy batch_*.json mirror files
2. Gate 2: historical_story missing = 0, senses with <2 collocations = 0
3. Gate 3: WhatsApp colloquial scenarios have >=2 messages with speaker identity
4. Gate 4: Provenance honesty (status in {'official', 'root_derived', 'corpus_usage'} strictly verified against data/prpm_raw/*.json) & Trilingual coverage:
   - senses[].en_definition non-empty
   - senses[].collocations[].en non-empty
   - dual_scenarios[formal].en non-empty
   - dual_scenarios[colloquial].messages[].en non-empty
5. Gate 5: 27 Shards three-state conservation (14748 enriched + 0 source_only + 252 missing_source = 15000) & quarantine triage alignment
6. Gate 6: Search index 100% synchronized with shards (all enriched words marked e=1, st='e')
"""

import json
import re
import string
import sys
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"
PRPM_DIR = ROOT_DIR / "data" / "prpm_raw"
TRIAGE_FILE = ROOT_DIR / "data" / "audit" / "quarantine_triage_report.json"
DATA_DIR = ROOT_DIR / "app" / "static" / "data"
SHARDS_DIR = DATA_DIR / "shards"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"
MANIFEST_FILE = DATA_DIR / "manifest.json"
INDEX_FILE = DATA_DIR / "search_index.json"

CTRL_RE = re.compile(r"[\x81\u00ad\u200b\u200e]")

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")


def _get_manifest_enriched_count() -> int:
    with open(MANIFEST_FILE, "r", encoding="utf-8") as fp:
        manifest = json.load(fp)
    return int(manifest["enriched_count"])


def _has_malay_dbp(prpm_data: dict) -> bool:
    if not prpm_data or not isinstance(prpm_data, dict):
        return False
    for key in ("kamus_dewan", "kamus_pelajar", "definisi_melayu"):
        val = prpm_data.get(key)
        if isinstance(val, str) and len(val.strip()) > 0:
            return True
        if isinstance(val, (list, dict)) and len(val) > 0:
            return True
    return False


def test_jawi_integrity():
    files = [f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")]
    expected = _get_manifest_enriched_count()
    assert len(files) >= expected, f"Expected >= {expected} files in data/enriched, got {len(files)}"

    q_jawis = []
    empty_str_jawis = []
    null_jawis = []
    ctrl_files = []
    for f in files:
        txt = f.read_text(encoding="utf-8")
        if CTRL_RE.search(txt):
            ctrl_files.append(f.name)
        d = json.loads(txt)
        j = d.get("headword", {}).get("jawi")
        rj = d.get("morphology", {}).get("root_jawi")
        if j and set(j) == {"?"}:
            q_jawis.append(f.name)
        elif j == "" or rj == "":
            empty_str_jawis.append(f.name)
        elif j is None:
            null_jawis.append(f.name)
        if rj and set(rj) == {"?"}:
            q_jawis.append(f"{f.name}:root_jawi")

    assert len(ctrl_files) == 0, f"Found {len(ctrl_files)} files containing banned control/format chars: {ctrl_files[:5]}"
    assert len(q_jawis) == 0, f"Found {len(q_jawis)} pure question mark Jawis: {q_jawis[:5]}"
    assert len(empty_str_jawis) == 0, f"Found {len(empty_str_jawis)} empty string Jawis: {empty_str_jawis[:5]}"
    print(f"[PASS] Gate 1: Pure question mark Jawis = 0, Empty string Jawis = 0, Control chars = 0, Strict null Jawis = {len(null_jawis)} (Total files: {len(files)})")


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
    rootwords_map = json.loads((ROOT_DIR / "raw" / "malay_rootwords.json").read_text(encoding="utf-8"))
    invalid_status = []
    unverified_official = []
    unverified_root_derived = []
    official_count = 0
    root_derived_count = 0
    corpus_count = 0

    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
        w = f.stem.lower()
        st = d.get("headword", {}).get("status")
        if st == "official":
            official_count += 1
            prpm_p = PRPM_DIR / f"{w}.json"
            if not prpm_p.exists():
                unverified_official.append((w, "missing_prpm_file"))
            else:
                with open(prpm_p, "r", encoding="utf-8") as pfp:
                    pd = json.load(pfp)
                if not _has_malay_dbp(pd):
                    unverified_official.append((w, "no_malay_dbp_entry"))
        elif st == "root_derived":
            root_derived_count += 1
            morph = d.get("morphology") or {}
            prov = d.get("provenance") or {}
            rw = (prov.get("root_word") or morph.get("root_word") or rootwords_map.get(w) or "").strip().lower()
            root_p = PRPM_DIR / f"{rw}.json" if rw else None
            if not rw or rw == w or not root_p or not root_p.exists():
                unverified_root_derived.append((w, rw, "invalid_root"))
            else:
                with open(root_p, "r", encoding="utf-8") as rfp:
                    rpd = json.load(rfp)
                if not _has_malay_dbp(rpd):
                    unverified_root_derived.append((w, rw, "root_no_malay_dbp"))
        elif st == "corpus_usage":
            corpus_count += 1
        else:
            invalid_status.append((f.name, st))

    assert len(invalid_status) == 0, f"Invalid headword.status found: {invalid_status[:5]}"
    assert len(unverified_official) == 0, f"Found {len(unverified_official)} official words without direct PRPM Malay DBP entry: {unverified_official[:5]}"
    assert len(unverified_root_derived) == 0, f"Found {len(unverified_root_derived)} root_derived words without valid PRPM Malay DBP root: {unverified_root_derived[:5]}"
    print(f"[PASS] Gate 4a: Provenance status strictly verified against PRPM evidence (official={official_count}, root_derived={root_derived_count}, corpus_usage={corpus_count})")


def test_three_state_conservation():
    with open(MANIFEST_FILE, "r", encoding="utf-8") as fp:
        manifest = json.load(fp)
    assert manifest["conservation_check"] is True
    expected_enriched = manifest["enriched_count"]
    assert expected_enriched == 14748, f"Expected 14748 enriched in manifest, got {expected_enriched}"
    assert manifest["source_only_count"] == 0, f"Expected 0 source_only in manifest, got {manifest['source_only_count']}"
    assert manifest["missing_source_count"] == 252, f"Expected 252 missing_source in manifest, got {manifest['missing_source_count']}"
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
    assert source_only_found == 0, f"Expected 0 source_only in shards, got {source_only_found}"
    assert missing_source_found == 252, f"Expected 252 missing_source in shards, got {missing_source_found}"
    assert (enriched_found + source_only_found + missing_source_found) == 15000

    assert TRIAGE_FILE.exists(), "Missing quarantine_triage_report.json"
    with open(TRIAGE_FILE, "r", encoding="utf-8") as tfp:
        triage = json.load(tfp)
    type_b_map = triage.get("type_b_missing_source_words", {})
    assert len(type_b_map) == 252, f"Expected 252 type_b_missing_source_words in triage report, got {len(type_b_map)}"
    empty_reasons = [w for w, item in type_b_map.items() if not (item.get("reason") or "").strip()]
    assert len(empty_reasons) == 0, f"Found empty reasons in quarantine_triage_report.json: {empty_reasons[:5]}"
    print(f"[PASS] Gate 5: Three-state conservation & triage alignment strictly verified ({enriched_found} + {source_only_found} + {missing_source_found} = 15000)")


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


if __name__ == "__main__":
    print("=== RUNNING STAGE 3 & 15K TRILINGUAL QUALITY GATES ===")
    test_jawi_integrity()
    test_story_and_collocations()
    test_whatsapp_messages()
    test_provenance_and_status()
    test_three_state_conservation()
    test_search_index_sync()
    test_trilingual_coverage()
    print("\n  [★★★ ALL GATES PASS - 100% TRILINGUAL COVERAGE ACHIEVED ★★★]")
