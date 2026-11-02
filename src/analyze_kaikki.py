import os
import json

p = r"c:\Users\d\Documents\open-melayu\raw\kaikki_malay.jsonl"
words = set()
pos_counts = {}
with open(p, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        try:
            item = json.loads(line)
            w = item.get('word')
            if w:
                words.add(w.lower())
            pos = item.get('pos', 'unknown')
            pos_counts[pos] = pos_counts.get(pos, 0) + 1
        except:
            pass

print(f"Total lines/senses: {sum(pos_counts.values())}")
print(f"Unique words: {len(words)}")
print(f"POS distribution: {pos_counts}")
