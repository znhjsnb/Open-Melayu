"""
Open-Melayu Top 1,001 - 2,000 Master Pipeline (Complete 718-Word Push)
Iterates through all remaining genuine core Malay words in Top 1,001 - 2,000 in rounds of 100 words.
For each round:
1. Gathers 100 words and assembles linguistic ground-truth packets.
2. Dispatches 25 parallel worker threads (4 words per micro-batch, ~25-30 RPM).
3. Validates entries against strict 8-dimension gate.
4. Auto-retries any straggler words until 100% round completion.
5. Atomically commits to data/enriched/, syncs 27 shards, and verifies 15k conservation.
6. Advances until all 718 core words are fully enriched (total library 1,818 entries).
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
            for suffix in ["kan", "i", "an", "nya", "ku", "mu", "lah", "kah"]:
                if w.endswith(suffix) and len(w) > len(suffix) + 2:
                    cand = w[:-len(suffix)]
                    if (PRPM_RAW_DIR / f"{cand}.json").exists():
                        r = cand
                        break
            if not r or r == w:
                for prefix in ["meng", "mem", "men", "me", "ber", "ter", "per", "pe", "se"]:
                    if w.startswith(prefix) and len(w) > len(prefix) + 2:
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
        
        # If derivative without direct definition, fallback to root definition summary
        if not kd and root != w:
            r_data = self.get_prpm_data(root)
            r_kd = r_data.get("kamus_dewan") or r_data.get("kamus_pelajar") or r_data.get("definisi_melayu") or ""
            kd = f"Kata dasar [{root}]: {r_kd}"

        trimmed_kd = kd[:300] + ("..." if len(kd) > 300 else "")

        jawi_val = prpm.get("jawi") or root_jawi
        syl_val = prpm.get("syllables")

        return {
            "word": w,
            "rank": rank,
            "jawi": jawi_val,
            "syllables": syl_val,
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
      "origin": "<Austronesian / Sanskrit / Arabic / Tamil / English / Dutch / Persian>",
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
    out_file = AUDIT_DIR / f"full2000_b{batch_idx}_output.json"
    
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

def get_all_remaining_candidates(kb: LinguisticKnowledgeBase) -> list[dict]:
    with open(DATA_DIR / "candidate_pool_15k.json", "r", encoding="utf-8") as f:
        pool = json.load(f)

    slice_1000_2000 = pool[1000:2000]
    valid_candidates = []

    for item in slice_1000_2000:
        w = item["word"]
        if (ENRICHED_DIR / f"{w}.json").exists():
            continue
            
        pdata = kb.get_prpm_data(w)
        kd = pdata.get("kamus_dewan") or pdata.get("kamus_pelajar") or pdata.get("definisi_melayu")
        
        root, root_jawi = kb.resolve_root(w)
        root_kd = None
        if root != w:
            r_data = kb.get_prpm_data(root)
            root_kd = r_data.get("kamus_dewan") or r_data.get("kamus_pelajar")
            
        if kd or root_kd:
            valid_candidates.append(kb.assemble_word_packet(w, item["rank"]))

    return valid_candidates

def sync_and_check_conservation(build_num: int):
    # Sync shards
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_enriched_to_shards.py")], check=True, capture_output=True)

    # Calculate counts
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

    conservation_check = (total_shard_words == 15000 and (enriched_count + source_only_count + missing_source_count == 15000))
    if not conservation_check:
        raise ValueError(f"Conservation broken! Shards: {total_shard_words}, E:{enriched_count}, S:{source_only_count}, M:{missing_source_count}")

    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_build_id = f"om-20261102-v{build_num}"
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

    with open(DATA_JS, "r", encoding="utf-8") as f:
        data_js = f.read()
    data_js = re.sub(r"const DATA_VERSION = ['\"][^'\"]+['\"];", f"const DATA_VERSION = '{new_build_id}';", data_js)
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(data_js)

    return enriched_count, source_only_count, missing_source_count, new_build_id

def main():
    print("=" * 75)
    print("  OPEN-MELAYU TOP 1,001 - 2,000 MASTER EXPANSION PIPELINE")
    print("=" * 75)

    kb = LinguisticKnowledgeBase()
    candidates = get_all_remaining_candidates(kb)
    total_to_enrich = len(candidates)
    print(f"[*] Total genuine Malay core words to enrich in 1001-2000: {total_to_enrich} words.")

    round_idx = 1
    build_counter = 3
    overall_start = time.time()
    
    while True:
        remaining = get_all_remaining_candidates(kb)
        if not remaining:
            print("\n🎉 ALL CANDIDATES IN TOP 1,001 - 2,000 ARE 100% ENRICHED!")
            break

        # Process up to 100 words per round
        round_words = remaining[:100]
        round_count = len(round_words)
        print(f"\n" + "-" * 75)
        print(f"  [ROUND {round_idx}] Processing {round_count} words (Remaining pool: {len(remaining)})")
        print(f"  Words range: #{round_words[0]['rank']} ({round_words[0]['word']}) to #{round_words[-1]['rank']} ({round_words[-1]['word']})")
        print("-" * 75)

        # Micro-batch size: 4 words -> ~25 workers
        micro_size = 4
        batches = [round_words[i:i + micro_size] for i in range(0, round_count, micro_size)]
        concurrency = len(batches)

        t_round_start = time.time()
        results = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(process_micro_batch, (round_idx * 100) + i, b): i for i, b in enumerate(batches)}
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                b_id = res["batch_idx"]
                status = res["status"]
                elapsed = res["elapsed"]
                val_cnt = len(res.get("validated", {}))
                w_cnt = len(res.get("words", []))
                if status == "ok":
                    print(f"    [Worker B{b_id}] PASS: {val_cnt}/{w_cnt} in {elapsed}s")
                elif status == "partial":
                    print(f"    [Worker B{b_id}] PARTIAL: {val_cnt}/{w_cnt} in {elapsed}s. Errors: {res.get('errors')}")
                else:
                    print(f"    [Worker B{b_id}] FAIL in {elapsed}s: {res.get('error')}")
                results.append(res)

        # Validate and retry missing words
        round_validated = {}
        missing_in_round = []
        for res in results:
            val = res.get("validated", {})
            round_validated.update(val)
            for w in res.get("words", []):
                if w not in val:
                    missing_in_round.append(w)

        print(f"[*] Round {round_idx} primary pass: {len(round_validated)}/{round_count} validated.")

        if missing_in_round:
            print(f"[!] Retrying {len(missing_in_round)} stragglers: {missing_in_round}...")
            retry_pkts = [p for p in round_words if p["word"] in missing_in_round]
            retry_batches = [retry_pkts[i:i + 2] for i in range(0, len(retry_pkts), 2)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(retry_batches)) as executor:
                ret_futs = [executor.submit(process_micro_batch, (round_idx * 1000) + i, rb) for i, rb in enumerate(retry_batches)]
                for rf in concurrent.futures.as_completed(ret_futs):
                    r_res = rf.result()
                    round_validated.update(r_res.get("validated", {}))
            print(f"[+] After retry: {len(round_validated)}/{round_count} validated.")

        # Commit round entries to data/enriched/
        print(f"[*] Committing {len(round_validated)} entries to {ENRICHED_DIR}...")
        for w, entry in round_validated.items():
            w_path = ENRICHED_DIR / f"{w}.json"
            with open(w_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)

        # Sync to shards and bump build id
        e_cnt, s_cnt, m_cnt, b_id = sync_and_check_conservation(build_counter)
        build_counter += 1
        round_elapsed = round(time.time() - t_round_start, 1)
        speed = round(len(round_validated) / (round_elapsed / 60.0), 1)

        print(f"[+] Round {round_idx} SUCCESS: {len(round_validated)} words in {round_elapsed}s ({speed} words/min).")
        print(f"[+] Current Total Enriched: {e_cnt} | Source-only: {s_cnt} | Build: {b_id}")

        # Update progress evidence
        evidence = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "round": round_idx,
            "round_words_count": len(round_validated),
            "round_elapsed_sec": round_elapsed,
            "total_enriched": e_cnt,
            "total_source_only": s_cnt,
            "total_missing_source": m_cnt,
            "build_id": b_id
        }
        with open(AUDIT_DIR / f"pipeline_round_{round_idx}_evidence.json", "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2)

        round_idx += 1
        time.sleep(2)

    total_pipeline_sec = round(time.time() - overall_start, 1)
    print("\n" + "=" * 75)
    print(f"  ALL ROUNDS COMPLETED IN {total_pipeline_sec}s ({total_pipeline_sec/60:.1f} mins)!")
    print("=" * 75)

if __name__ == "__main__":
    main()
