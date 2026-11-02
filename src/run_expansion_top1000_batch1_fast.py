"""
Open-Melayu Top 1,001 - 2,000 Expansion Pipeline (Fast 25-30 RPM Edition)
- 25 parallel worker threads (4 words per micro-batch = 100 words).
- Generates 8-dimension entries via Codex CLI (gpt-6.1-sol / high).
- Compact context packets & clear token budgeting for fast completion (<3 mins).
- Zero file write collisions, full gate verification, atomic commits to data/enriched/.
- Shards synchronization and manifest update.
"""

import concurrent.futures
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
RAW_DIR = ROOT_DIR / "raw"
DATA_DIR = ROOT_DIR / "data"
PRPM_RAW_DIR = DATA_DIR / "prpm_raw"
ENRICHED_DIR = DATA_DIR / "enriched"
AUDIT_DIR = DATA_DIR / "audit"
APP_STATIC_DATA = ROOT_DIR / "app" / "static" / "data"
SHARDS_DIR = APP_STATIC_DATA / "shards"
MANIFEST_FILE = APP_STATIC_DATA / "manifest.json"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"
CODEX_EXE = r"C:\Users\d\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe"

ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

WINDOWS_RESERVED = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2'}

class LinguisticKnowledgeBase:
    def __init__(self):
        print("[*] Initializing offline linguistic resources...")
        t0 = time.time()
        
        with open(RAW_DIR / "malaya_colloquial_rules.json", "r", encoding="utf-8") as f:
            self.colloquial_rules = json.load(f)
        self.reverse_shortcuts = {}
        for short, full in self.colloquial_rules.items():
            full_w = full.lower().strip()
            if full_w not in self.reverse_shortcuts:
                self.reverse_shortcuts[full_w] = []
            self.reverse_shortcuts[full_w].append(short)

        with open(RAW_DIR / "malay_rootwords.json", "r", encoding="utf-8") as f:
            self.roots = json.load(f)

        self.kaikki = {}
        with open(RAW_DIR / "kaikki_malay.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                w = item.get("word", "").lower()
                if w not in self.kaikki:
                    self.kaikki[w] = []
                self.kaikki[w].append(item)

        print(f"[+] Knowledge base ready in {time.time()-t0:.2f}s.")

    def get_prpm_data(self, word: str) -> dict:
        w = word.lower().strip()
        raw_fname = f"_reserved_{w}.json" if w in WINDOWS_RESERVED else f"{w}.json"
        raw_path = PRPM_RAW_DIR / raw_fname
        if raw_path.exists():
            try:
                with open(raw_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def resolve_root(self, word: str) -> tuple[str, str | None]:
        w = word.lower().strip()
        r = self.roots.get(w)
        if not r or r == w:
            for suffix in ["kan", "i", "an", "nya", "ku", "mu"]:
                if w.endswith(suffix) and len(w) > len(suffix) + 3:
                    cand = w[:-len(suffix)]
                    if (PRPM_RAW_DIR / f"{cand}.json").exists():
                        r = cand
                        break
            if not r or r == w:
                for prefix in ["meng", "mem", "men", "me", "ber", "ter", "per", "pe", "se"]:
                    if w.startswith(prefix) and len(w) > len(prefix) + 3:
                        cand = w[len(prefix):]
                        if (PRPM_RAW_DIR / f"{cand}.json").exists():
                            r = cand
                            break
        if not r:
            r = w
            
        root_jawi = None
        r_fname = f"_reserved_{r}.json" if r in WINDOWS_RESERVED else f"{r}.json"
        r_path = PRPM_RAW_DIR / r_fname
        if r_path.exists():
            try:
                with open(r_path, "r", encoding="utf-8") as f:
                    rd = json.load(f)
                    root_jawi = rd.get("jawi")
            except Exception:
                pass
        return r, root_jawi

    def assemble_word_packet(self, word: str, rank: int) -> dict:
        w = word.lower().strip()
        prpm = self.get_prpm_data(w)
        kaikki_entries = self.kaikki.get(w, [])
        
        ipas = []
        glosses = []
        for k in kaikki_entries:
            for s in k.get("sounds", []) or []:
                if s.get("ipa"):
                    ipas.append(s.get("ipa"))
            for sense in k.get("senses", []) or []:
                for g in sense.get("glosses", []) or []:
                    glosses.append(g)

        root, root_jawi = self.resolve_root(w)
        kd = prpm.get("kamus_dewan") or prpm.get("kamus_pelajar") or prpm.get("definisi_melayu") or ""
        trimmed_kd = kd[:300] + ("..." if len(kd) > 300 else "")

        return {
            "word": w,
            "rank": rank,
            "jawi": prpm.get("jawi"),
            "syllables": prpm.get("syllables"),
            "core_dbp_definition": trimmed_kd,
            "resolved_root": {
                "root_word": root,
                "root_jawi": root_jawi,
                "is_root": (root == w)
            },
            "ipas": list(set(ipas))[:2],
            "glosses": glosses[:2],
            "shortcuts": self.reverse_shortcuts.get(w, [])[:2]
        }

def select_top_100_source_only(kb: LinguisticKnowledgeBase) -> list[dict]:
    with open(DATA_DIR / "candidate_pool_15k.json", "r", encoding="utf-8") as f:
        pool = json.load(f)

    shards = {}
    for letter in "abcdefghijklmnopqrstuvwxyz":
        with open(SHARDS_DIR / f"{letter}.json", "r", encoding="utf-8") as sf:
            shards[letter] = json.load(sf)
    with open(SHARDS_DIR / "other.json", "r", encoding="utf-8") as sf:
        shards["other"] = json.load(sf)

    def get_state(w):
        c = w[0].lower()
        entry = shards.get(c, shards["other"]).get(w)
        return entry.get("data_state") if entry else None

    selected = []
    for item in pool[1000:2000]:
        w = item["word"]
        # Skip if already enriched
        if (ENRICHED_DIR / f"{w}.json").exists():
            continue
            
        prpm = kb.get_prpm_data(w)
        kd = prpm.get("kamus_dewan") or prpm.get("kamus_pelajar") or prpm.get("definisi_melayu")
        if not kd:
            continue
            
        if get_state(w) != "source_only":
            continue
            
        selected.append(kb.assemble_word_packet(w, item["rank"]))
        if len(selected) == 100:
            break

    return selected

SCHEMA_PROMPT = """
You are the authoritative Malay cognitive lexicographer and Lead Engineer for Open-Melayu.
Synthesize complete, production-grade 8-dimension cognitive dictionary entries for the given Malay words.

Return a single JSON object mapping each word to its complete 8-dimension entry:
{
  "<word>": {
    "headword": {
      "word": "<word>",
      "syllables": "<syllables from packet>",
      "ipa": "<IPA from packet or standard>",
      "jawi": "<Jawi from packet>",
      "frequency_rank": <rank>,
      "status": "official"
    },
    "morphology": {
      "is_root": true | false,
      "root_word": "<root_word from packet>",
      "affix": "<affix or null>",
      "affix_type": "prefix" | "suffix" | "circumfix" | "none",
      "formula": "<formula, e.g. meN- + kawal → mengawal or ∅ + balas → balas>",
      "pattern_note": "<concise phonological rule>",
      "word_family": [
        { "word": "<family word 1>", "affix": "<affix>", "gloss": "<Chinese brief meaning>" },
        { "word": "<family word 2>", "affix": "<affix>", "gloss": "<Chinese brief meaning>" }
      ],
      "root_jawi": "<root_jawi from packet or same as jawi>"
    },
    "senses": [
      {
        "id": 1,
        "pos": "verb" | "noun" | "adjective" | "adverb" | "preposition" | "conjunction" | "particle",
        "zh_definition": "<Precise Chinese definition>",
        "en_definition": "<Clear English definition>",
        "ms_definition": "<Official Malay definition>",
        "nuances": "<Pragmatic notes>",
        "collocations": [
          { "ms": "<High frequency collocation 1>", "zh": "<Chinese translation 1>" },
          { "ms": "<High frequency collocation 2>", "zh": "<Chinese translation 2>" }
        ]
      }
    ],
    "dual_scenarios": [
      {
        "scenario": "formal",
        "context": "公文 / 新闻 / 职场汇报",
        "ms": "<Authentic standard Malaysian Malay sentence>",
        "zh": "<Chinese translation>",
        "en": "<English translation>"
      },
      {
        "scenario": "colloquial",
        "context": "WhatsApp / 日常口语交流",
        "ms_spoken": "<Spoken sentence with authentic particles>",
        "ms_standard": "<Standard equivalent sentence>",
        "zh": "<Colloquial Chinese translation>",
        "en": "<English translation>",
        "spoken_features": ["<feature 1>"],
        "messages": [
          {
            "speaker": "Name (关系, e.g. Farah (朋友))",
            "ms_spoken": "<First turn spoken Malay with particles dah/kat/nak/je>",
            "ms_standard": "<Standard Malay equivalent>",
            "zh": "<Chinese translation>"
          },
          {
            "speaker": "Name (关系, e.g. Amir (同事))",
            "ms_spoken": "<Second turn reply in spoken Malay>",
            "ms_standard": "<Standard Malay equivalent>",
            "zh": "<Chinese translation>"
          }
        ]
      }
    ],
    "spoken_shortcuts": [
      { "abbr": "<SMS shortcut>", "full_form": "<word>", "note": "<context>" }
    ],
    "cultural_pragmatics": {
      "register": "standard" | "formal" | "colloquial" | "intimate",
      "politeness_note": "<Politeness guidance in Malaysian society>",
      "usage_etiquette": "<Practical usage advice>"
    },
    "etymology": {
      "origin": "<Austronesian / Sanskrit / Arabic / Tamil / English / Dutch>",
      "source_language": "<Language name>",
      "root_origin": "<Original etymon>",
      "cognitive_memory_aid": "<Memorable mnemonic hook>",
      "historical_story": "<Vivid 2-3 sentence narrative detailing the word's historical origin and evolution into modern Malay>"
    }
  }
}

CRITICAL RULES:
1. Provide 1 core sense per word. The sense MUST contain at least 2 distinct collocations.
2. WhatsApp colloquial scenario MUST have `messages` containing at least 2 turns with speaker name and social relationship.
3. Every entry MUST have a non-empty `etymology.historical_story` AND `etymology.cognitive_memory_aid`.
4. Output MUST be ONLY the raw JSON object. No markdown code fences, no extra text.
"""

def validate_entry(entry: dict, word: str) -> tuple[bool, str]:
    if not isinstance(entry, dict):
        return False, "Not a dictionary"
    
    head = entry.get("headword", {})
    if not head or head.get("word", "").lower() != word.lower():
        return False, f"Headword mismatch for {word}"
    jawi = head.get("jawi")
    if jawi and set(jawi) == {'?'}:
        return False, f"Pure question mark Jawi for {word}"
        
    morph = entry.get("morphology", {})
    if not morph or "is_root" not in morph or "formula" not in morph:
        return False, f"Invalid morphology for {word}"
        
    senses = entry.get("senses", [])
    if not senses or not isinstance(senses, list):
        return False, f"Missing senses for {word}"
    for s in senses:
        collocs = s.get("collocations", [])
        if len(collocs) < 2:
            return False, f"Sense {s.get('id')} has <2 collocations in {word}"
        if not s.get("zh_definition"):
            return False, f"Missing zh_definition in {word}"
            
    scenarios = entry.get("dual_scenarios", [])
    if len(scenarios) < 2:
        return False, f"Missing dual scenarios in {word}"
    colloquial = next((sc for sc in scenarios if sc.get("scenario") == "colloquial"), None)
    if not colloquial:
        return False, f"Missing colloquial scenario in {word}"
    msgs = colloquial.get("messages", [])
    if len(msgs) < 2:
        return False, f"Colloquial scenario has <2 messages in {word}"
    for m in msgs:
        if not m.get("speaker") or not m.get("ms_spoken") or not m.get("zh"):
            return False, f"Incomplete message turn in {word}"

    etym = entry.get("etymology", {})
    story = etym.get("historical_story", "")
    aid = etym.get("cognitive_memory_aid", "")
    if not story or len(story.strip()) < 15:
        return False, f"Missing/short historical_story in {word}"
    if not aid or len(aid.strip()) < 5:
        return False, f"Missing cognitive_memory_aid in {word}"
        
    prag = entry.get("cultural_pragmatics", {})
    if not prag.get("politeness_note") or not prag.get("usage_etiquette"):
        return False, f"Incomplete cultural_pragmatics in {word}"
        
    return True, "OK"

def process_micro_batch(batch_idx: int, packets: list) -> dict:
    start_time = time.time()
    words = [p["word"] for p in packets]
    out_file = AUDIT_DIR / f"fast_b{batch_idx+1}_output.json"
    
    prompt = f"""{SCHEMA_PROMPT}

Words to synthesize ({len(words)} words):
{json.dumps(words, ensure_ascii=False)}

Input Ground Truth Packets:
{json.dumps(packets, ensure_ascii=False, indent=2)}
"""

    cmd = [
        CODEX_EXE, "exec",
        "-C", str(ROOT_DIR),
        "--ephemeral",
        "-o", str(out_file),
        "-"
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            encoding="utf-8",
            timeout=240
        )
        elapsed = round(time.time() - start_time, 1)
        if proc.returncode != 0:
            return {"batch_idx": batch_idx, "status": "error", "error": f"Code {proc.returncode}", "words": words, "elapsed": elapsed}
            
        if not out_file.exists():
            return {"batch_idx": batch_idx, "status": "error", "error": "Output missing", "words": words, "elapsed": elapsed}

        with open(out_file, "r", encoding="utf-8") as f:
            raw = f.read().strip()

        clean_json = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
        clean_json = re.sub(r"^```\s*$", "", clean_json, flags=re.MULTILINE).strip()
        data = json.loads(clean_json)

        validated_entries = {}
        errors = {}
        for w in words:
            if w not in data:
                errors[w] = "Missing in output JSON"
                continue
            entry = data[w]
            ok, err = validate_entry(entry, w)
            if not ok:
                errors[w] = err
            else:
                entry["sociolinguistic_register"] = entry.get("cultural_pragmatics", {})
                validated_entries[w] = entry

        status = "ok" if not errors else ("partial" if validated_entries else "error")
        return {
            "batch_idx": batch_idx,
            "status": status,
            "validated": validated_entries,
            "errors": errors,
            "words": words,
            "elapsed": elapsed
        }

    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return {"batch_idx": batch_idx, "status": "error", "error": str(e), "words": words, "elapsed": elapsed}

def main():
    print("=" * 70)
    print("  OPEN-MELAYU TOP 1,001 - 2,000 EXPANSION: 100 WORDS (25-30 RPM FAST)")
    print("=" * 70)

    kb = LinguisticKnowledgeBase()
    packets = select_top_100_source_only(kb)
    print(f"[*] Screened and assembled {len(packets)} core Malay words from Top 1,001-2,000.")
    print(f"[*] Ranks: #{packets[0]['rank']} ({packets[0]['word']}) to #{packets[-1]['rank']} ({packets[-1]['word']})")

    # 4 words per batch = 25 batches
    micro_batch_size = 4
    batches = [packets[i:i + micro_batch_size] for i in range(0, len(packets), micro_batch_size)]
    concurrency = len(batches) # 25 concurrent threads (25 RPM)

    print(f"\n[*] Firing {concurrency}-way parallel worker pool (4 words per micro-batch)...")
    print(f"[*] Running at ~25-30 RPM maximum velocity...")
    t0 = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = {executor.submit(process_micro_batch, i, b): i for i, b in enumerate(batches)}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            idx = res["batch_idx"] + 1
            status = res["status"]
            elapsed = res["elapsed"]
            val_cnt = len(res.get("validated", {}))
            if status == "ok":
                print(f"  [Worker B{idx:02d}] PASS: {val_cnt}/4 words validated in {elapsed}s")
            elif status == "partial":
                print(f"  [Worker B{idx:02d}] PARTIAL: {val_cnt}/4 words validated in {elapsed}s. Errors: {res.get('errors')}")
            else:
                print(f"  [Worker B{idx:02d}] FAIL: {res.get('error')} in {elapsed}s")
            results.append(res)

    total_time = round(time.time() - t0, 1)
    print(f"\n[*] All {concurrency} parallel workers finished in {total_time}s.")

    all_validated = {}
    missing_words = []
    for res in results:
        val = res.get("validated", {})
        all_validated.update(val)
        for w in res.get("words", []):
            if w not in val:
                missing_words.append(w)

    print(f"[*] Validated entries: {len(all_validated)} / 100 words.")

    # Retry pass if any missing
    if missing_words:
        print(f"[!] Retrying {len(missing_words)} missing words: {missing_words}...")
        retry_packets = [p for p in packets if p["word"] in missing_words]
        # Split into micro-batches of 2
        retry_batches = [retry_packets[i:i+2] for i in range(0, len(retry_packets), 2)]
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(retry_batches)) as executor:
            ret_futs = [executor.submit(process_micro_batch, 100+i, rb) for i, rb in enumerate(retry_batches)]
            for rf in concurrent.futures.as_completed(ret_futs):
                r_res = rf.result()
                all_validated.update(r_res.get("validated", {}))

    print(f"\n[*] Final Total Validated: {len(all_validated)} / 100 words.")
    if len(all_validated) < 95:
        print("[!] Too many failures. Aborting commit.")
        sys.exit(1)

    # 1. Atomic Commit to data/enriched/<word>.json
    print(f"[*] Atomically committing {len(all_validated)} entries to {ENRICHED_DIR}...")
    for w, entry in all_validated.items():
        w_path = ENRICHED_DIR / f"{w}.json"
        with open(w_path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    print("[+] Enriched files committed successfully.")

    # 2. Sync to Shards
    print("[*] Synchronizing to 27 static shards via src/sync_enriched_to_shards.py...")
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_enriched_to_shards.py")], check=True)

    # 3. Dynamic Three-State Conservation & Manifest Update
    print("[*] Verifying three-state conservation across all 27 shards...")
    total_shard_words = 0
    enriched_count = 0
    source_only_count = 0
    missing_source_count = 0

    for letter in list("abcdefghijklmnopqrstuvwxyz") + ["other"]:
        with open(SHARDS_DIR / f"{letter}.json", "r", encoding="utf-8") as sf:
            sdata = json.load(sf)
        total_shard_words += len(sdata)
        for w, entry in sdata.items():
            state = entry.get("data_state")
            if state == "enriched":
                enriched_count += 1
            elif state == "source_only":
                source_only_count += 1
            elif state == "missing_source":
                missing_source_count += 1

    print(f"  - Total words in shards: {total_shard_words}")
    print(f"  - Enriched count: {enriched_count}")
    print(f"  - Source-only count: {source_only_count}")
    print(f"  - Missing-source count: {missing_source_count}")
    conservation_check = (total_shard_words == 15000 and (enriched_count + source_only_count + missing_source_count == 15000))
    print(f"  - Conservation check: {conservation_check}")

    if not conservation_check:
        print("[!] Conservation check failed! Shard state inconsistent.")
        sys.exit(1)

    # Update manifest.json
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_build_id = "om-20261102-v2"
    manifest_data = {
        "build_id": new_build_id,
        "timestamp": now_ts,
        "total_words": 15000,
        "enriched_count": enriched_count,
        "source_only_count": source_only_count,
        "missing_source_count": missing_source_count,
        "conservation_check": True
    }
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    print(f"[+] manifest.json updated with build_id: {new_build_id}")

    # Update data.js
    with open(DATA_JS, "r", encoding="utf-8") as f:
        data_js = f.read()
    data_js = re.sub(r"const DATA_VERSION = ['\"][^'\"]+['\"];", f"const DATA_VERSION = '{new_build_id}';", data_js)
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(data_js)
    print(f"[+] data.js synchronized with build_id: {new_build_id}")

    # Write execution evidence log
    evidence = {
        "timestamp": now_ts,
        "expansion_batch": "Top 1001-2000 Batch 1 (Fast 25-30 RPM)",
        "words_targeted": 100,
        "words_succeeded": len(all_validated),
        "total_time_sec": total_time,
        "new_enriched_count": enriched_count,
        "new_source_only_count": source_only_count,
        "sample_words": [p["word"] for p in packets[:10]],
        "build_id": new_build_id
    }
    with open(AUDIT_DIR / "expansion_batch1_fast_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("  EXPANSION BATCH 1 SUCCESSFULLY COMPLETED & DEPLOYED")
    print("=" * 70)

if __name__ == "__main__":
    main()
