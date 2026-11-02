import json
import os
import sys

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = r"C:\Users\d\Documents\open-melayu"
ENRICHED_DIR = os.path.join(ROOT_DIR, "data", "enriched")
OUT_JSON = os.path.join(ROOT_DIR, "data", "audit", "codex_batch4_output.json")
BATCH_WORDS = ['tapi', 'pergi', 'orang', 'adalah', 'nak', 'ia', 'jadi', 'sekarang', 'lagi', 'pada']

with open(OUT_JSON, "r", encoding="utf-8") as f:
    generated = json.load(f)

applied_count = 0
for w in BATCH_WORDS:
    if w not in generated:
        print(f"Error: {w} missing from generated output")
        continue
    w_data = generated[w]
    msgs = w_data.get("messages", [])
    if len(msgs) < 2:
        print(f"Error: {w} has fewer than 2 messages")
        continue

    fpath = os.path.join(ENRICHED_DIR, f"{w}.json")
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
        applied_count += 1
        print(f"[OK] Applied {len(msgs)} messages for [{w}]")

print(f"\nSuccessfully applied Codex generated WhatsApp dialogues for {applied_count}/{len(BATCH_WORDS)} words.")
