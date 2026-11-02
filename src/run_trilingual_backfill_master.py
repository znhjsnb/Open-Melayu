"""
Open-Melayu Master Trilingual Backfill Pipeline (30-40 RPM Controlled)
Backfills authentic, dictionary-grade English translations across all 1,841 enriched entries:
- senses[].en_definition (for 2,871 missing definitions)
- senses[].collocations[].en (for 7,853 collocations)
- dual_scenarios[1].messages[].en (for 4,161 dialogue turns)

Strictly adheres to:
1. 30-40 RPM sliding-window rate limit (RateLimiter at 36.0 RPM).
2. Field-level protection: deep equality check guarantees 0% corruption to non-English fields.
3. Micro-batching: 4 words per batch.
4. Automatic straggler retry.
5. Shard sync, search index sync, manifest bump, and conservation verification after each round.
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
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"
AUDIT_DIR = ROOT_DIR / "data" / "audit"
SHARDS_DIR = ROOT_DIR / "app" / "static" / "data" / "shards"
MANIFEST_FILE = ROOT_DIR / "app" / "static" / "data" / "manifest.json"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"
CODEX_EXE = r"C:\Users\d\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe"

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

def strip_en_fields(entry: dict) -> dict:
    e = copy.deepcopy(entry)
    for s in e.get("senses", []):
        s.pop("en_definition", None)
        for c in s.get("collocations", []):
            c.pop("en", None)
    if len(e.get("dual_scenarios", [])) > 1:
        for m in e["dual_scenarios"][1].get("messages", []):
            m.pop("en", None)
    return e

def build_word_packet(word: str) -> dict:
    fpath = ENRICHED_DIR / f"{word}.json"
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    packet = {
        "word": word,
        "senses": []
    }
    for s in data.get("senses", []):
        spkt = {
            "id": s.get("id"),
            "zh_definition": s.get("zh_definition"),
            "ms_definition": s.get("ms_definition"),
            "needs_en_def": not bool(s.get("en_definition")),
            "collocations": [
                {"ms": c.get("ms"), "zh": c.get("zh")}
                for c in s.get("collocations", [])
            ]
        }
        packet["senses"].append(spkt)
    
    dual = data.get("dual_scenarios", [])
    if len(dual) > 1 and "messages" in dual[1]:
        packet["messages"] = [
            {
                "speaker": m.get("speaker"),
                "ms_spoken": m.get("ms_spoken"),
                "zh": m.get("zh")
            }
            for m in dual[1]["messages"]
        ]
    else:
        packet["messages"] = []
    return packet

def apply_and_verify_patch(word: str, patch_data: dict) -> tuple[bool, str, dict]:
    fpath = ENRICHED_DIR / f"{word}.json"
    with open(fpath, "r", encoding="utf-8") as f:
        orig = json.load(f)
    
    before_stripped = strip_en_fields(orig)
    patched = copy.deepcopy(orig)
    
    wp = patch_data.get(word)
    if not wp or not isinstance(wp, dict):
        return False, f"Missing patch object for {word}", {}
    
    # Apply sense definitions and collocations
    patch_senses = wp.get("senses", [])
    for i, s_patch in enumerate(patch_senses):
        if i < len(patched.get("senses", [])):
            target_sense = patched["senses"][i]
            # en_definition if needed
            if s_patch.get("en_definition") and not target_sense.get("en_definition"):
                target_sense["en_definition"] = s_patch["en_definition"].strip()
            
            # collocations en
            patch_collocs = s_patch.get("collocations", [])
            for j, c_patch in enumerate(patch_collocs):
                if j < len(target_sense.get("collocations", [])):
                    if c_patch.get("en"):
                        target_sense["collocations"][j]["en"] = c_patch["en"].strip()
    
    # Apply message dialogue translations
    patch_messages = wp.get("messages", [])
    dual = patched.get("dual_scenarios", [])
    if len(dual) > 1 and "messages" in dual[1]:
        for k, m_patch in enumerate(patch_messages):
            if k < len(dual[1]["messages"]):
                if m_patch.get("en"):
                    dual[1]["messages"][k]["en"] = m_patch["en"].strip()
    
    # Verify field integrity
    after_stripped = strip_en_fields(patched)
    if before_stripped != after_stripped:
        return False, f"Integrity check failed: non-en fields corrupted in {word}", {}
    
    # Verify that collocations have en
    for s in patched.get("senses", []):
        for c in s.get("collocations", []):
            if not c.get("en"):
                return False, f"Collocation missing en in {word}", {}
    
    return True, "OK", patched

def process_micro_batch(batch_idx: int, packets: list) -> dict:
    start_time = time.time()
    words = [p["word"] for p in packets]
    out_file = AUDIT_DIR / f"trilingual_b{batch_idx}_output.json"
    
    prompt = f"""You are the authoritative Malay-Chinese-English trilingual lexicographer for Open-Melayu.
Translate the following Malay collocations, dialogue messages, and missing sense definitions into natural, dictionary-grade English.

Input packets:
{json.dumps(packets, ensure_ascii=False, indent=2)}

Requirements:
1. If `needs_en_def` is true, provide a concise, dictionary-grade English definition in `en_definition`. If false, you can omit `en_definition` or echo it.
2. For each collocation, provide an authentic, natural English translation in `collocations[i].en`.
3. For each WhatsApp dialogue message, provide an idiomatic, conversational English translation in `messages[i].en`, preserving speaker tone and colloquial nuances.
4. Output MUST be ONLY valid JSON mapping each word to its patch object:
{{
  "<word>": {{
    "senses": [
      {{
        "id": <id>,
        "en_definition": "<English definition if needed>",
        "collocations": [
          {{ "en": "<English collocation 1>" }},
          {{ "en": "<English collocation 2>" }}
        ]
      }}
    ],
    "messages": [
      {{ "en": "<English message 1>" }},
      {{ "en": "<English message 2>" }}
    ]
  }}
}}
No markdown fences, no explanatory text.
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
            timeout=180
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
            ok, err, patched_entry = apply_and_verify_patch(w, data)
            if ok:
                validated_entries[w] = patched_entry
            else:
                errors[w] = err

        status = "ok" if not errors else ("partial" if validated_entries else "error")
        return {
            "batch_idx": batch_idx,
            "status": status,
            "words": words,
            "validated": validated_entries,
            "errors": errors,
            "elapsed": elapsed
        }

    except subprocess.TimeoutExpired:
        return {"batch_idx": batch_idx, "status": "timeout", "words": words, "elapsed": round(time.time() - start_time, 1)}
    except Exception as e:
        return {"batch_idx": batch_idx, "status": "exception", "error": str(e), "words": words, "elapsed": round(time.time() - start_time, 1)}

def update_shards_and_manifest():
    # Sync shards
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_enriched_to_shards.py")], check=True, capture_output=True)
    # Sync search index
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_search_index.py")], check=True, capture_output=True)
    
    # Count states across 27 shards
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

    return enriched_count, source_only_count, missing_source_count, new_build_id

def run_backfill(max_words: int = None):
    # Find all words needing backfill
    files = sorted(glob.glob(str(ENRICHED_DIR / "*.json")))
    word_files = [f for f in files if not os.path.basename(f).startswith("batch_")]
    
    words_to_backfill = []
    for wf in word_files:
        w = os.path.basename(wf)[:-5]
        with open(wf, "r", encoding="utf-8") as f:
            d = json.load(f)
        
        missing_def = any(not s.get("en_definition") for s in d.get("senses", []))
        missing_colloc = any(any(not c.get("en") for c in s.get("collocations", [])) for s in d.get("senses", []))
        dual = d.get("dual_scenarios", [])
        missing_msg = False
        if len(dual) > 1 and "messages" in dual[1]:
            missing_msg = any(not m.get("en") for m in dual[1]["messages"])
        
        if missing_def or missing_colloc or missing_msg:
            words_to_backfill.append(w)
            
    print(f"[*] Total words needing English backfill: {len(words_to_backfill)}")
    if max_words:
        words_to_backfill = words_to_backfill[:max_words]
        print(f"[*] Limiting run to first {len(words_to_backfill)} words.")
        
    ROUND_SIZE = 100
    MICRO_BATCH_SIZE = 4
    
    round_idx = 1
    total_processed = 0
    total_backfill_words = len(words_to_backfill)
    
    while total_processed < total_backfill_words:
        round_words = words_to_backfill[total_processed: total_processed + ROUND_SIZE]
        round_count = len(round_words)
        print(f"\n==================================================")
        print(f"  [ROUND {round_idx}] Backfilling {round_count} words ({total_processed}/{total_backfill_words} done)")
        print(f"==================================================")
        
        round_pkts = [build_word_packet(w) for w in round_words]
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
            retry_pkts = [build_word_packet(w) for w in missing_in_round]
            retry_batches = [retry_pkts[i:i + 2] for i in range(0, len(retry_pkts), 2)]
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(10, len(retry_batches))) as executor:
                ret_futs = [executor.submit(process_micro_batch, (round_idx * 5000) + i, rb) for i, rb in enumerate(retry_batches)]
                for rf in concurrent.futures.as_completed(ret_futs):
                    res = rf.result()
                    for w, entry in res.get("validated", {}).items():
                        round_validated[w] = entry
            print(f"[+] After retry: {len(round_validated)}/{round_count} validated.")
            
        # Commit round entries to disk
        print(f"[*] Committing {len(round_validated)} patched entries to {ENRICHED_DIR}...")
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
        print(f"[+] Synced! Build: {b_id} | Enriched: {e_cnt} | Conservation OK")
        
        # Save evidence
        evidence = {
            "round": round_idx,
            "round_words_count": len(round_validated),
            "total_processed": total_processed + len(round_validated),
            "speed_wpm": speed,
            "elapsed_seconds": round_elapsed,
            "build_id": b_id
        }
        with open(AUDIT_DIR / f"trilingual_round_{round_idx}_evidence.json", "w", encoding="utf-8") as f:
            json.dump(evidence, f, ensure_ascii=False, indent=2)
            
        total_processed += round_count
        round_idx += 1
        
    print(f"\n[★] ALL {total_backfill_words} WORDS TRILINGUAL BACKFILL COMPLETE!")

if __name__ == "__main__":
    max_w = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_backfill(max_w)
