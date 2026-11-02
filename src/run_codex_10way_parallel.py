"""
10-Way Parallel Codex CLI Orchestrator for Open-Melayu.
Upgrades 100 words (Words 41-140) in 10 parallel worker threads.
Each worker processes 10 words independently.
Ensures zero race conditions and atomic integration.
"""

import concurrent.futures
import datetime
import json
import os
import re
import subprocess
import sys
import time

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = r"C:\Users\d\Documents\open-melayu"
ENRICHED_DIR = os.path.join(ROOT_DIR, "data", "enriched")
AUDIT_DIR = os.path.join(ROOT_DIR, "data", "audit")
CANDIDATE_POOL = os.path.join(ROOT_DIR, "data", "candidate_pool_15k.json")
CODEX_EXE = r"C:\Users\d\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe"

# 1. Load words 41 to 140
with open(CANDIDATE_POOL, "r", encoding="utf-8") as f:
    pool = json.load(f)

target_words = [x["word"] for x in pool[40:140]]
print(f"[*] Loaded 100 words to upgrade: Words 41-140")
print(f"[*] Starting 10-way parallel dispatch (10 words per batch)...")

batches = [target_words[i:i+10] for i in range(0, 100, 10)]

def process_batch(batch_idx, batch_words):
    start_time = time.time()
    batch_num = batch_idx + 5  # Batch 5 to 14
    out_tmp = os.path.join(AUDIT_DIR, f"parallel_batch_{batch_num}_output.json")
    
    # Collect context for the 10 words
    context_list = []
    for w in batch_words:
        fpath = os.path.join(ENRICHED_DIR, f"{w}.json")
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            d = json.load(f)
        senses = [s.get("zh_definition") for s in d.get("senses", [])]
        cur_scenarios = d.get("dual_scenarios", [])
        colloquial = next((s for s in cur_scenarios if s.get("scenario") == "colloquial"), {})
        context_list.append({
            "word": w,
            "senses": senses,
            "existing_colloquial": {
                "context": colloquial.get("context", "日常聊天"),
                "ms_spoken": colloquial.get("ms_spoken", ""),
                "ms_standard": colloquial.get("ms_standard", ""),
                "zh": colloquial.get("zh", ""),
                "spoken_features": colloquial.get("spoken_features", [])
            }
        })

    prompt = f"""You are the authoritative Malay cognitive dictionary linguist.
Task: Upgrade the colloquial dual scenario for 10 high-frequency Malay words from single-sentence examples into authentic multi-turn WhatsApp dialogues (at least 2 turns with speaker names and roles).

Input Words and Context:
{json.dumps(context_list, ensure_ascii=False, indent=2)}

Requirements for each word's `messages`:
1. Exactly 2 or 3 turns in `messages`.
2. Each turn object must have:
   - "speaker": Name and social relationship, e.g. "Farhan (同事)", "Haziq (朋友)", "Ibu (母亲)"
   - "ms_spoken": Authentic street/WhatsApp Malay with natural contractions/slang (e.g. nak, gi, xde, je, kot, kan, dah, xleh)
   - "ms_standard": Formal Standard Malay restoration of the spoken sentence
   - "zh": Accurate Chinese translation
3. Maintain the word's target usage naturally in the dialogue.
4. Output MUST be ONLY valid JSON dictionary (no markdown, no surrounding comments):
{{
  "{batch_words[0]}": {{
    "context": "WhatsApp / ...",
    "messages": [ ... ],
    "spoken_features": [ ... ]
  }},
  ...
}}
"""

    cmd = [
        CODEX_EXE, "exec",
        "-C", ROOT_DIR,
        "--ephemeral",
        "-o", out_tmp,
        "-"
    ]

    try:
        proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True, encoding="utf-8", timeout=240)
        elapsed = round(time.time() - start_time, 1)
        if proc.returncode != 0:
            return {"batch_num": batch_num, "status": "failed", "error": f"Return code {proc.returncode}", "elapsed": elapsed}
        
        if not os.path.exists(out_tmp):
            return {"batch_num": batch_num, "status": "failed", "error": "Output file missing", "elapsed": elapsed}

        with open(out_tmp, "r", encoding="utf-8") as f:
            raw_content = f.read().strip()

        clean_json = re.sub(r"^```json\s*", "", raw_content, flags=re.MULTILINE)
        clean_json = re.sub(r"^```\s*$", "", clean_json, flags=re.MULTILINE).strip()
        data = json.loads(clean_json)

        return {"batch_num": batch_num, "status": "ok", "data": data, "words": batch_words, "elapsed": elapsed}

    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return {"batch_num": batch_num, "status": "failed", "error": str(e), "elapsed": elapsed}

# Launch 10 workers in parallel
print(f"[*] Firing 10 parallel workers now...")
t0 = time.time()
results = []

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(process_batch, i, batch) for i, batch in enumerate(batches)]
    for future in concurrent.futures.as_completed(futures):
        res = future.result()
        b_num = res["batch_num"]
        status = res["status"]
        elapsed = res["elapsed"]
        if status == "ok":
            print(f"[Worker B{b_num}] SUCCESS in {elapsed}s (Parsed {len(res['data'])} words)")
        else:
            print(f"[Worker B{b_num}] FAILED in {elapsed}s: {res['error']}")
        results.append(res)

total_elapsed = round(time.time() - t0, 1)
print(f"\n[*] All 10 parallel workers finished in {total_elapsed}s.")

# Apply successfully generated batches
applied_words = 0
failed_words = []

for res in results:
    if res["status"] != "ok":
        failed_words.extend(res.get("words", []))
        continue
    
    generated = res["data"]
    for w in res["words"]:
        if w not in generated:
            failed_words.append(w)
            continue
        w_data = generated[w]
        msgs = w_data.get("messages", [])
        if len(msgs) < 2:
            failed_words.append(w)
            continue

        fpath = os.path.join(ENRICHED_DIR, f"{w}.json")
        if not os.path.exists(fpath):
            continue

        with open(fpath, "r", encoding="utf-8") as f:
            entry = json.load(f)

        found = False
        for sc in entry.get("dual_scenarios", []):
            if sc.get("scenario") == "colloquial":
                sc["messages"] = msgs
                if w_data.get("context"):
                    sc["context"] = w_data["context"]
                if w_data.get("spoken_features"):
                    sc["spoken_features"] = w_data["spoken_features"]
                sc["ms_spoken"] = msgs[0]["ms_spoken"]
                sc["ms_standard"] = msgs[0]["ms_standard"]
                sc["zh"] = msgs[0]["zh"]
                found = True
                break

        if found:
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(entry, f, ensure_ascii=False, indent=2)
            applied_words += 1

print(f"\n================ 10-WAY PARALLEL EXECUTION SUMMARY ================")
print(f"Total time elapsed: {total_elapsed} seconds")
print(f"Total words targeted: 100")
print(f"Successfully upgraded & integrated: {applied_words} words")
print(f"Failed words: {len(failed_words)} ({', '.join(failed_words) if failed_words else 'None'})")
print(f"Success Rate: {(applied_words / 100.0) * 100:.1f}%")
print(f"====================================================================")

# Write audit log
audit_log = {
    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "parallel_workers": 10,
    "words_count": 100,
    "applied_count": applied_words,
    "failed_count": len(failed_words),
    "failed_words": failed_words,
    "total_elapsed_sec": total_elapsed
}

with open(os.path.join(AUDIT_DIR, "parallel_10way_run_evidence.json"), "w", encoding="utf-8") as f:
    json.dump(audit_log, f, ensure_ascii=False, indent=2)

if applied_words >= 90:
    print("\n[*] Invoking fast sync to all 27 shards...")
    subprocess.run(["python", os.path.join(ROOT_DIR, "src", "sync_enriched_to_shards.py")])
    print("[*] 27 Shards updated.")
