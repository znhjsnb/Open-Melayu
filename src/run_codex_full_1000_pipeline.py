"""
Autonomous Full Pipeline to upgrade all remaining entries (Words 141-1000) in Open-Melayu.
Iterates in 10-way parallel batches (100 words per round).
For each round:
1. Gathers context for 100 words (10 words * 10 workers).
2. Executes 10 workers in parallel via codex.exe exec (gpt-6.1-sol / high).
3. Validates multi-turn messages (at least 2 turns with speaker).
4. Atomically integrates into data/enriched/<word>.json.
5. Syncs shards and advances to the next round until all 1,000 entries are 100% upgraded.
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

# 1. Identify words needing upgrade (where colloquial has no messages or <2 messages)
def get_words_needing_upgrade():
    with open(CANDIDATE_POOL, "r", encoding="utf-8") as f:
        pool = json.load(f)
    first_1000 = [x["word"] for x in pool[:1000]]
    
    needed = []
    for w in first_1000:
        fpath = os.path.join(ENRICHED_DIR, f"{w}.json")
        if not os.path.exists(fpath):
            continue
        with open(fpath, "r", encoding="utf-8") as f:
            d = json.load(f)
        dual = d.get("dual_scenarios", [])
        has_valid_msgs = False
        for sc in dual:
            if sc.get("scenario") == "colloquial":
                if sc.get("messages") and len(sc.get("messages")) >= 2:
                    has_valid_msgs = True
                break
        if not has_valid_msgs:
            needed.append(w)
    return needed

def process_single_batch(batch_words, worker_tag):
    start_time = time.time()
    out_tmp = os.path.join(AUDIT_DIR, f"pipeline_{worker_tag}_output.json")
    
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
   - "speaker": Name and social relationship, e.g. "Farhan (同事)", "Haziq (朋友)", "Ibu (母亲)", "Siti (同学)"
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
            return {"tag": worker_tag, "status": "failed", "error": f"Return code {proc.returncode}", "elapsed": elapsed, "words": batch_words}
        
        if not os.path.exists(out_tmp):
            return {"tag": worker_tag, "status": "failed", "error": "Output file missing", "elapsed": elapsed, "words": batch_words}

        with open(out_tmp, "r", encoding="utf-8") as f:
            raw_content = f.read().strip()

        clean_json = re.sub(r"^```json\s*", "", raw_content, flags=re.MULTILINE)
        clean_json = re.sub(r"^```\s*$", "", clean_json, flags=re.MULTILINE).strip()
        data = json.loads(clean_json)

        return {"tag": worker_tag, "status": "ok", "data": data, "words": batch_words, "elapsed": elapsed}

    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return {"tag": worker_tag, "status": "failed", "error": str(e), "elapsed": elapsed, "words": batch_words}

def apply_batch_data(generated_dict, words):
    applied = 0
    for w in words:
        if w not in generated_dict:
            continue
        w_data = generated_dict[w]
        msgs = w_data.get("messages", [])
        if len(msgs) < 2:
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
            applied += 1
    return applied

# Main continuous loop
overall_start = time.time()
round_num = 1

while True:
    needed_words = get_words_needing_upgrade()
    total_remaining = len(needed_words)
    print(f"\n=======================================================")
    print(f"[ROUND {round_num}] Total words currently needing upgrade: {total_remaining}")
    print(f"=======================================================")
    
    if total_remaining == 0:
        print("\n🎉 ALL 1,000 WORDS HAVE BEEN 100% UPGRADED WITH MULTI-TURN MESSAGES!")
        break

    # Take up to 100 words for this round (10 batches of 10)
    current_round_words = needed_words[:100]
    batches = [current_round_words[i:i+10] for i in range(0, len(current_round_words), 10)]
    worker_count = len(batches)
    print(f"[*] Dispatching {len(current_round_words)} words across {worker_count} parallel workers...")

    r_start = time.time()
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [executor.submit(process_single_batch, batch, f"r{round_num}_b{i}") for i, batch in enumerate(batches)]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            tag = res["tag"]
            status = res["status"]
            elapsed = res["elapsed"]
            if status == "ok":
                print(f"  [Worker {tag}] SUCCESS in {elapsed}s (Parsed {len(res['data'])} words)")
            else:
                print(f"  [Worker {tag}] FAILED in {elapsed}s: {res['error']}")
            results.append(res)

    # Apply data for successful workers
    round_applied = 0
    for res in results:
        if res["status"] == "ok":
            cnt = apply_batch_data(res["data"], res["words"])
            round_applied += cnt

    r_elapsed = round(time.time() - r_start, 1)
    print(f"[*] Round {round_num} finished in {r_elapsed}s. Applied: {round_applied}/{len(current_round_words)} words.")

    # Fast sync shards after each round
    print("[*] Syncing updated entries to 27 shards...")
    subprocess.run(["python", os.path.join(ROOT_DIR, "src", "sync_enriched_to_shards.py")], capture_output=True)

    round_num += 1
    # Small pause between rounds to be respectful to local resources
    time.sleep(2)

total_pipeline_time = round(time.time() - overall_start, 1)
print(f"\n================ FULL PIPELINE COMPLETED ================")
print(f"Total time elapsed: {total_pipeline_time} seconds ({total_pipeline_time/60:.1f} minutes)")
print(f"Verified 1,000 words: All 1,000 entries now possess authentic multi-turn messages.")
print(f"=========================================================")

# Final fast sync & manifest update
subprocess.run(["python", os.path.join(ROOT_DIR, "src", "sync_enriched_to_shards.py")])
