import os
import sys
import json

sys.stdout.reconfigure(encoding='utf-8')

p = r"c:\Users\d\Documents\open-melayu\raw\kaikki_malay.jsonl"
targets = ["ajar", "belajar", "mengajar", "pelajar", "pelajaran"]
found = {}

with open(p, 'r', encoding='utf-8', errors='ignore') as f:
    for line in f:
        item = json.loads(line)
        w = item.get('word')
        if w in targets and w not in found:
            found[w] = {
                'word': w,
                'pos': item.get('pos'),
                'sounds': item.get('sounds'),
                'etymology': item.get('etymology_text'),
                'senses': [s.get('glosses') for s in item.get('senses', [])]
            }

for k, v in found.items():
    print(json.dumps(v, ensure_ascii=False, indent=2))
