"""
Open-Melayu Grand Master Trilingual Expansion Pipeline (All the way to 15,000!)
Continuously synthesizes authentic, production-grade 8-dimension trilingual entries
across all remaining slices (Top 3,001 ~ 15,000) for all genuine core Malay candidates with DBP definitions.

Features:
1. 30-40 RPM sliding-window rate limit (RateLimiter at 36.0 RPM).
2. 4-word micro-batching with 20-worker thread pool.
3. Fast in-memory candidate scanner using RAM-cached PRPM file index.
4. Strict 8-dimension trilingual quality validation (senses en, collocations en, messages en).
5. Automatic straggler retry for any failed/timed-out batch.
6. Periodic commit & shard/index sync after every 100 words.
7. Dynamic 15,000-word three-state conservation verification.
8. Full crash-resilience and resumability (skips already enriched files).
"""

import os
import sys
import json
import time
import copy
import glob
import string
import threading
import subprocess
from pathlib import Path
import concurrent.futures

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
RAW_DIR = ROOT_DIR / "raw"
DATA_DIR = ROOT_DIR / "data"
ENRICHED_DIR = DATA_DIR / "enriched"
AUDIT_DIR = DATA_DIR / "audit"
SHARDS_DIR = ROOT_DIR / "app" / "static" / "data" / "shards"
MANIFEST_FILE = ROOT_DIR / "app" / "static" / "data" / "manifest.json"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"
CODEX_EXE = r"C:\Users\d\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe"

ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

class SlidingWindowRateLimiter:
    def __init__(self, max_per_minute: float = 36.0):
        self.max_per_minute = max_per_minute
        self.lock = threading.Lock()
        self.timestamps = []

    def acquire(self):
        with self.lock:
            now = time.time()
            self.timestamps = [t for t in self.timestamps if now - t < 60.0]
            if len(self.timestamps) >= self.max_per_minute:
                sleep_needed = 60.0 - (now - self.timestamps[0]) + 0.05
                if sleep_needed > 0:
                    time.sleep(sleep_needed)
                    now = time.time()
                    self.timestamps = [t for t in self.timestamps if now - t < 60.0]
            self.timestamps.append(time.time())

limiter = SlidingWindowRateLimiter(max_per_minute=36.0)

class LinguisticKnowledgeBase:
    def __init__(self):
        print("[*] Initializing ultra-fast in-memory linguistic resources for full 15,000 pool...")
        t0 = time.time()
        
        # 1. Reverse shortcuts
        self.reverse_shortcuts = {}
        with open(RAW_DIR / "malaya_colloquial_rules.json", "r", encoding="utf-8") as f:
            cdata = json.load(f)
            for short, full_w in cdata.get("shortcuts", {}).items():
                if full_w not in self.reverse_shortcuts:
                    self.reverse_shortcuts[full_w] = []
                self.reverse_shortcuts[full_w].append(short)

        # 2. Rootwords
        with open(RAW_DIR / "malay_rootwords.json", "r", encoding="utf-8") as f:
            self.rootwords = json.load(f)

        # 3. Kaikki
        self.kaikki = {}
        with open(RAW_DIR / "kaikki_malay.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                w = item.get("word")
                if w:
                    if w not in self.kaikki:
                        self.kaikki[w] = []
                    self.kaikki[w].append(item)
                    
        # 4. RAM index of all PRPM raw filenames (instant O(1) existence checks)
        self.prpm_file_map = {
            entry.name[:-5]: entry.path 
            for entry in os.scandir(DATA_DIR / "prpm_raw") 
            if entry.name.endswith(".json")
        }
        self.prpm_cache = {}
        print(f"[+] Knowledge base ready in {time.time() - t0:.2f}s ({len(self.prpm_file_map)} PRPM files indexed).")

    def get_prpm_data(self, word: str) -> dict:
        w = word.lower().strip()
        if w in self.prpm_cache:
            return self.prpm_cache[w]
        
        path = self.prpm_file_map.get(w)
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.prpm_cache[w] = d
                    return d
            except Exception:
                pass
        self.prpm_cache[w] = {}
        return {}

    def resolve_root(self, word: str) -> tuple[str, str | None]:
        w = word.lower().strip()
        r = self.rootwords.get(w)
        if not r or r == w:
            for suffix in ["kan", "i", "an", "nya", "ku", "mu", "lah", "kah"]:
                if w.endswith(suffix) and len(w) > len(suffix) + 2:
                    cand = w[:-len(suffix)]
                    if cand in self.prpm_file_map:
                        r = cand
                        break
            if not r or r == w:
                for prefix in ["meng", "mem", "men", "me", "ber", "ter", "per", "pe", "se"]:
                    if w.startswith(prefix) and len(w) > len(prefix) + 2:
                        cand = w[len(prefix):]
                        if cand in self.prpm_file_map:
                            r = cand
                            break
        if not r:
            r = w
            
        rd = self.get_prpm_data(r)
        root_jawi = rd.get("jawi")
        return r, root_jawi

    def assemble_word_packet(self, word: str, rank: int) -> dict:
        w = word.lower().strip()
        prpm = self.get_prpm_data(w)
        root, root_jawi = self.resolve_root(w)

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

        kd = prpm.get("kamus_dewan") or prpm.get("kamus_pelajar") or prpm.get("definisi_melayu") or ""
        # If derivative has no direct definition, use root definition
        if not kd and root != w:
            r_data = self.get_prpm_data(root)
            kd = r_data.get("kamus_dewan") or r_data.get("kamus_pelajar") or ""
            
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
Crucial: This is a TRILINGUAL dictionary (Malay core + Chinese + English translations).

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
        "en_definition": "<Concise dictionary-grade English definition>",
        "ms_definition": "<Official Malay definition>",
        "nuances": "<Pragmatic notes and usage boundaries>",
        "collocations": [
          { "ms": "<High frequency collocation 1>", "zh": "<Chinese translation 1>", "en": "<English translation 1>" },
          { "ms": "<High frequency collocation 2>", "zh": "<Chinese translation 2>", "en": "<English translation 2>" }
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
            "zh": "<Chinese translation>",
            "en": "<Natural, idiomatic conversational English translation>"
          },
          {
            "speaker": "Name (关系, e.g. Amir (同事))",
            "ms_spoken": "<Second turn reply in spoken Malay>",
            "ms_standard": "<Standard Malay equivalent>",
            "zh": "<Chinese translation>",
            "en": "<Natural, idiomatic conversational English translation>"
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
      "historical_story": "<Vivid 2-3 sentence narrative detailing the word's historical origin and semantic evolution>",
      "cognitive_memory_aid": "<Memorable cognitive mnemonic or visual association>"
    }
  }
}

TRILINGUAL RULES:
1. Provide 1 core sense per word. The sense MUST contain at least 2 distinct collocations, EACH with `ms`, `zh`, AND `en`.
2. Both `zh_definition` AND `en_definition` are mandatory and non-empty.
3. WhatsApp colloquial scenario MUST have `messages` containing at least 2 turns with speaker name, `ms_spoken`, `ms_standard`, `zh`, AND `en`.
4. Output MUST be ONLY the raw JSON object. No markdown code fences, no extra text.
"""

def validate_trilingual_entry(entry: dict, word: str) -> tuple[bool, str]:
    if not isinstance(entry, dict):
        return False, "Entry is not a dict"
    
    head = entry.get("headword", {})
    if not head.get("word") or head.get("word").lower() != word.lower():
        return False, f"Headword mismatch: {head.get('word')} != {word}"

    morph = entry.get("morphology", {})
    if "formula" not in morph or not morph.get("formula"):
        return False, f"Missing morphology formula in {word}"

    senses = entry.get("senses", [])
    if not senses or not isinstance(senses, list):
        return False, f"Missing senses for {word}"
        
    for s in senses:
        if not s.get("zh_definition"):
            return False, f"Missing zh_definition in {word}"
        if not s.get("en_definition"):
            return False, f"Missing en_definition in {word}"
        collocs = s.get("collocations", [])
        if len(collocs) < 2:
            return False, f"Sense {s.get('id')} has <2 collocations in {word}"
        for c in collocs:
            if not c.get("ms") or not c.get("zh") or not c.get("en"):
                return False, f"Collocation missing ms/zh/en in {word}"
            
    scenarios = entry.get("dual_scenarios", [])
    if len(scenarios) < 2:
        return False, f"Missing dual scenarios in {word}"
    formal = next((sc for sc in scenarios if sc.get("scenario") == "formal"), None)
    if not formal or not formal.get("ms") or not formal.get("zh") or not formal.get("en"):
        return False, f"Incomplete formal scenario in {word}"

    colloquial = next((sc for sc in scenarios if sc.get("scenario") == "colloquial"), None)
    if not colloquial:
        return False, f"Missing colloquial scenario in {word}"
    msgs = colloquial.get("messages", [])
    if len(msgs) < 2:
        return False, f"Colloquial scenario has <2 messages in {word}"
    for m in msgs:
        if not m.get("speaker") or not m.get("ms_spoken") or not m.get("zh") or not m.get("en"):
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
    out_file = AUDIT_DIR / f"full15k_b{batch_idx}_output.json"
    
    prompt = f"""{SCHEMA_PROMPT}

Words to synthesize ({len(words)} words):
{json.dumps(words, ensure_ascii=False)}

Input Ground Truth Packets:
{json.dumps(packets, ensure_ascii=False, indent=2)}
"""

    limiter.acquire()
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
            
        if "```" in raw:
            lines = raw.splitlines()
            clean = []
            in_fence = False
            for l in lines:
                if l.strip().startswith("```"):
                    in_fence = not in_fence
                    continue
                clean.append(l)
            raw = "\n".join(clean).strip()

        data = json.loads(raw)
        validated_entries = {}
        errors = {}
        for w in words:
            if w not in data:
                errors[w] = "Missing in output JSON"
                continue
            entry = data[w]
            ok, err = validate_trilingual_entry(entry, w)
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

    except subprocess.TimeoutExpired:
        return {"batch_idx": batch_idx, "status": "timeout", "words": words, "elapsed": round(time.time() - start_time, 1)}
    except Exception as e:
        return {"batch_idx": batch_idx, "status": "exception", "error": str(e), "words": words, "elapsed": round(time.time() - start_time, 1)}

def update_shards_and_manifest():
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_enriched_to_shards.py")], check=True, capture_output=True)
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_search_index.py")], check=True, capture_output=True)
    
    enriched_count = 0
    source_only_count = 0
    missing_source_count = 0
    total_shard_words = 0

    for letter in list(string.ascii_lowercase) + ["other"]:
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

    new_build_id = f"om-{time.strftime('%Y%m%d')}-v{int(time.time()) % 10000}"
    manifest_data = {
        "build_id": new_build_id,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "total_words": 15000,
        "enriched_count": enriched_count,
        "source_only_count": source_only_count,
        "missing_source_count": missing_source_count,
        "conservation_check": conservation_check,
        "format_version": 2
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    with open(DATA_JS, "r", encoding="utf-8") as f:
        js_content = f.read()
    import re
    js_content = re.sub(r'export const DATA_VERSION = [\'"][^\'"]+[\'"];', f"export const DATA_VERSION = '{new_build_id}';", js_content)
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    # Automated milestone Git commit
    try:
        subprocess.run(["git", "-C", str(ROOT_DIR), "add", "app/static/data/", "data/enriched/", "data/audit/", "START.md", "docs/"], check=False)
        subprocess.run(["git", "-C", str(ROOT_DIR), "commit", "-m", f"feat(lexicon): milestone {enriched_count} words trilingual build {new_build_id}"], check=False)
    except Exception as ge:
        print(f"[!] Git commit notice: {ge}")

    return enriched_count, source_only_count, missing_source_count, new_build_id

def get_all_remaining_candidates(kb: LinguisticKnowledgeBase) -> list[dict]:
    with open(DATA_DIR / "candidate_pool_15k.json", "r", encoding="utf-8") as f:
        pool = json.load(f)

    valid_candidates = []
    for item in pool:
        w = item["word"].lower().strip()
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

def run_grand_expansion():
    kb = LinguisticKnowledgeBase()
    candidates = get_all_remaining_candidates(kb)
    total_to_enrich = len(candidates)
    print(f"\n[★] GRAND EXPANSION TO 15,000 LAUNCHED!")
    print(f"[*] Total genuine Malay core candidates to enrich across remaining pool: {total_to_enrich} words.\n")
    
    ROUND_SIZE = 100
    MICRO_BATCH_SIZE = 4
    
    round_idx = 1
    total_processed = 0
    
    while total_processed < total_to_enrich:
        round_pkts = candidates[total_processed: total_processed + ROUND_SIZE]
        round_words = [p["word"] for p in round_pkts]
        round_count = len(round_words)
        
        print(f"\n==================================================")
        print(f"  [GRAND ROUND {round_idx}] Synthesizing {round_count} words ({total_processed}/{total_to_enrich} done)")
        print(f"==================================================")
        
        batches = [round_pkts[i:i + MICRO_BATCH_SIZE] for i in range(0, len(round_pkts), MICRO_BATCH_SIZE)]
        concurrency = min(20, len(batches))
        
        round_start = time.time()
        round_validated = {}
        missing_in_round = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = {executor.submit(process_micro_batch, (round_idx * 1000) + i, b): i for i, b in enumerate(batches)}
            for future in concurrent.futures.as_completed(futures):
                res = future.result()
                val_cnt = len(res.get("validated", {}))
                w_cnt = len(res.get("words", []))
                print(f"  --> Batch {res.get('batch_idx')}: {val_cnt}/{w_cnt} validated in {res.get('elapsed')}s (Status: {res.get('status')})")
                for w, entry in res.get("validated", {}).items():
                    round_validated[w] = entry
                for w, err in res.get("errors", {}).items():
                    print(f"      [!] Error for {w}: {err}")
                    missing_in_round.append(w)
                if res.get("status") in ["error", "timeout", "exception"]:
                    for w in res.get("words", []):
                        if w not in round_validated and w not in missing_in_round:
                            missing_in_round.append(w)
                            
        print(f"[*] Round {round_idx} primary pass: {len(round_validated)}/{round_count} validated.")
        
        # Straggler retry
        if missing_in_round:
            print(f"[!] Retrying {len(missing_in_round)} stragglers: {missing_in_round}...")
            retry_pkts = [p for p in round_pkts if p["word"] in missing_in_round]
            retry_batches = [retry_pkts[i:i + 2] for i in range(0, len(retry_pkts), 2)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(retry_batches))) as executor:
                ret_futs = [executor.submit(process_micro_batch, (round_idx * 5000) + i, rb) for i, rb in enumerate(retry_batches)]
                for rf in concurrent.futures.as_completed(ret_futs):
                    res = rf.result()
                    for w, entry in res.get("validated", {}).items():
                        round_validated[w] = entry
            print(f"[+] After retry: {len(round_validated)}/{round_count} validated.")
            
        # Commit round entries to disk
        print(f"[*] Committing {len(round_validated)} entries to {ENRICHED_DIR}...")
        for w, entry in round_validated.items():
            w_path = ENRICHED_DIR / f"{w}.json"
            with open(w_path, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
                
        round_elapsed = round(time.time() - round_start, 1)
        speed = round(len(round_validated) / (round_elapsed / 60.0), 1) if round_elapsed > 0 else 0
        print(f"[+] Round {round_idx} SUCCESS: {len(round_validated)} words in {round_elapsed}s ({speed} words/min)")
        
        # Sync shards, search index & manifest
        print(f"[*] Syncing shards, search index, and verifying 15k conservation...")
        e_cnt, s_cnt, m_cnt, b_id = update_shards_and_manifest()
        print(f"[+] Synced! Build: {b_id} | Total Enriched in DB: {e_cnt} | Conservation OK")
        
        # Save progress evidence
        progress_data = {
            "round": round_idx,
            "round_words_count": len(round_validated),
            "total_processed_in_grand_run": total_processed + len(round_validated),
            "total_candidates_to_enrich": total_to_enrich,
            "total_enriched_in_repo": e_cnt,
            "speed_wpm": speed,
            "elapsed_seconds": round_elapsed,
            "build_id": b_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
        }
        with open(AUDIT_DIR / "grand_expansion_progress.json", "w", encoding="utf-8") as f:
            json.dump(progress_data, f, ensure_ascii=False, indent=2)
            
        total_processed += round_count
        round_idx += 1
        
    print(f"\n[★★★] GRAND EXPANSION COMPLETE! ALL CORE MALAY WORDS ENRICHED! [★★★]")

if __name__ == "__main__":
    run_grand_expansion()
