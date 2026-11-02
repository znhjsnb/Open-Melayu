"""
Fast sync of enriched 1,000 entries into shards/<letter>.json.
Directly updates shard files in <1 second without full 15k raw PRPM reparsing.
"""

import json
import glob
import os
import sys

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = r"C:\Users\d\Documents\open-melayu"
ENRICHED_DIR = os.path.join(ROOT_DIR, "data", "enriched")
SHARDS_DIR = os.path.join(ROOT_DIR, "app", "static", "data", "shards")

files = glob.glob(os.path.join(ENRICHED_DIR, "*.json"))
word_files = [f for f in files if not os.path.basename(f).startswith("batch_")]

print(f"Syncing {len(word_files)} enriched files into shards...")

# Load all 27 shards into memory
shards = {}
for letter in "abcdefghijklmnopqrstuvwxyz":
    spath = os.path.join(SHARDS_DIR, f"{letter}.json")
    if os.path.exists(spath):
        with open(spath, "r", encoding="utf-8") as sf:
            shards[letter] = json.load(sf)
    else:
        shards[letter] = {}

other_path = os.path.join(SHARDS_DIR, "other.json")
if os.path.exists(other_path):
    with open(other_path, "r", encoding="utf-8") as sf:
        shards["other"] = json.load(sf)
else:
    shards["other"] = {}

updated_count = 0
for fpath in word_files:
    fname = os.path.basename(fpath)
    word = fname[:-5]
    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    first_char = word[0].lower()
    letter = first_char if first_char in shards else "other"

    # Wrap as web shard entry structure
    shards[letter][word] = {
        "id": data.get("headword", {}).get("frequency_rank", 1),
        "word": word,
        "is_enriched": True,
        "data_state": "enriched",
        "headword": data.get("headword", {}),
        "morphology": data.get("morphology", {}),
        "senses": data.get("senses", []),
        "dual_scenarios": data.get("dual_scenarios", []),
        "spoken_shortcuts": data.get("spoken_shortcuts", []),
        "cultural_pragmatics": data.get("cultural_pragmatics", {}),
        "sociolinguistic_register": data.get("sociolinguistic_register", data.get("cultural_pragmatics", {})),
        "etymology": data.get("etymology", {})
    }
    updated_count += 1

# Write back shards
for letter, shard_data in shards.items():
    spath = os.path.join(SHARDS_DIR, f"{letter}.json")
    with open(spath, "w", encoding="utf-8") as sf:
        json.dump(shard_data, sf, ensure_ascii=False, separators=(",", ":"))

print(f"Successfully synced {updated_count} enriched entries into all 27 shards!")
