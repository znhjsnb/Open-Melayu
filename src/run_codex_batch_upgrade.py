"""
Automated Codex CLI runner to upgrade dual_scenarios for a batch of 10 words.
Feeds prompt via stdin (preventing Windows stdin hang) and parses output JSON.
Applies validated multi-turn messages directly to data/enriched/<word>.json.
"""

import json
import os
import re
import subprocess
import sys

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = r"C:\Users\d\Documents\open-melayu"
ENRICHED_DIR = os.path.join(ROOT_DIR, "data", "enriched")
BATCH_WORDS = ['tapi', 'pergi', 'orang', 'adalah', 'nak', 'ia', 'jadi', 'sekarang', 'lagi', 'pada']

# 1. Gather context for the 10 words
context_list = []
for w in BATCH_WORDS:
    fpath = os.path.join(ENRICHED_DIR, f"{w}.json")
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
   - "ms_spoken": Authentic street/WhatsApp Malay with natural contractions/slang (e.g. nak, gi, xde, je, kot, kan)
   - "ms_standard": Formal Standard Malay restoration of the spoken sentence
   - "zh": Accurate Chinese translation
3. Maintain the word's target usage naturally in the dialogue.
4. Output MUST be ONLY valid JSON in the following format (no markdown, no extra commentary):
{{
  "tapi": {{
    "context": "WhatsApp / ...",
    "messages": [ ... ],
    "spoken_features": [ ... ]
  }},
  ...
}}
"""

out_tmp = os.path.join(ROOT_DIR, "data", "audit", "codex_batch4_output.json")
prompt_file = os.path.join(ROOT_DIR, "data", "audit", "batch4_prompt.txt")

with open(prompt_file, "w", encoding="utf-8") as pf:
    pf.write(prompt)

print(f"[*] Dispatching batch of 10 words to Codex CLI (gpt-6.1-sol / high)...")
print(f"[*] Target words: {', '.join(BATCH_WORDS)}")

CODEX_EXE = r"C:\Users\d\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe"

# Execute codex CLI non-interactively using python subprocess
cmd = [
    CODEX_EXE, "exec",
    "-C", ROOT_DIR,
    "--ephemeral",
    "-o", out_tmp,
    "-"
]

proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True, encoding="utf-8")

print(f"[*] Codex CLI finished with code: {proc.returncode}")
if proc.stderr:
    print(f"[Codex stderr]: {proc.stderr[:300]}")

# Read and validate generated JSON
if not os.path.exists(out_tmp):
    print("Error: output file was not generated.")
    sys.exit(1)

with open(out_tmp, "r", encoding="utf-8") as f:
    raw_content = f.read().strip()

# Clean potential markdown fences
clean_json = re.sub(r"^```json\s*", "", raw_content, flags=re.MULTILINE)
clean_json = re.sub(r"^```\s*$", "", clean_json, flags=re.MULTILINE).strip()

try:
    generated = json.loads(clean_json)
except Exception as e:
    print(f"JSON parse error: {e}\nRaw output preview:\n{clean_json[:500]}")
    sys.exit(1)

print("\n[*] Validating and applying generated messages to enriched files...")
applied_count = 0
for w in BATCH_WORDS:
    if w not in generated:
        print(f"Warning: {w} missing from generated output!")
        continue
    w_data = generated[w]
    msgs = w_data.get("messages", [])
    if len(msgs) < 2:
        print(f"Warning: {w} generated fewer than 2 messages!")
        continue

    fpath = os.path.join(ENRICHED_DIR, f"{w}.json")
    with open(fpath, "r", encoding="utf-8") as f:
        entry = json.load(f)

    # Find colloquial scenario
    found = False
    for sc in entry.get("dual_scenarios", []):
        if sc.get("scenario") == "colloquial":
            sc["messages"] = msgs
            if w_data.get("context"):
                sc["context"] = w_data["context"]
            if w_data.get("spoken_features"):
                sc["spoken_features"] = w_data["spoken_features"]
            # Set the first spoken text as representative
            sc["ms_spoken"] = msgs[0]["ms_spoken"]
            sc["ms_standard"] = msgs[0]["ms_standard"]
            sc["zh"] = msgs[0]["zh"]
            found = True
            break
    
    if found:
        with open(fpath, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
        applied_count += 1
        print(f"  -> Applied {len(msgs)} messages for [{w}]")

print(f"\n[SUCCESS] Successfully upgraded {applied_count}/{len(BATCH_WORDS)} words with Codex CLI!")
