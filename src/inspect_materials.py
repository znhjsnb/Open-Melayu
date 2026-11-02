import os
import json
import gzip

RAW_DIR = r"c:\Users\d\Documents\open-melayu\raw"

def inspect_dbp():
    p = os.path.join(RAW_DIR, "dbp_malay_words_v2.json")
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"[DBP] Type: {type(data)}, Count: {len(data)}")
        if isinstance(data, list) and len(data) > 0:
            print(f"[DBP] Sample 3: {data[:3]}")
        elif isinstance(data, dict):
            keys = list(data.keys())[:3]
            print(f"[DBP] Sample keys: {keys}, Sample val: {data[keys[0]]}")

def inspect_frequencies():
    p = os.path.join(RAW_DIR, "opensubtitles_frequency_ms_50k.txt")
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            lines = [f.readline().strip() for _ in range(10)]
        print(f"[Freq 50k] Top 10: {lines}")

def inspect_kaikki():
    p = os.path.join(RAW_DIR, "kaikki_malay.jsonl")
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
            data = json.loads(first_line)
        print(f"[Kaikki] First entry keys: {list(data.keys())}")
        print(f"[Kaikki] Word: {data.get('word')}, POS: {data.get('pos')}")
        if 'senses' in data and len(data['senses']) > 0:
            print(f"[Kaikki] Senses sample: {data['senses'][0].get('glosses')}")

if __name__ == "__main__":
    inspect_dbp()
    inspect_frequencies()
    inspect_kaikki()
