import os
import sys
import json
import time
from prpm_client import query_prpm

sys.stdout.reconfigure(encoding='utf-8')

pilot_file = r"c:\Users\d\Documents\open-melayu\data\pilot_50_candidates.json"
with open(pilot_file, 'r', encoding='utf-8') as f:
    pilot_data = json.load(f)

words = [item['word'] for item in pilot_data]
print(f"[*] Starting PRPM polite crawl for {len(words)} pilot words...")

success_count = 0
found_count = 0

for idx, w in enumerate(words, 1):
    res = query_prpm(w)
    if res.get('found_in_prpm'):
        found_count += 1
    success_count += 1
    sys.stdout.write(f"\r[{idx}/{len(words)}] Fetched '{w}' | In PRPM: {res.get('found_in_prpm')} | Total found: {found_count}")
    sys.stdout.flush()
    time.sleep(0.3)

print(f"\n[+] Finished PRPM crawl for pilot 50 words! Found in official DBP: {found_count}/{len(words)}")
