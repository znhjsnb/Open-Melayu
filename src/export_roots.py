import os
import json
import pyreadr

rda_path = r"c:\Users\d\Documents\open-melayu\raw\malayrootwords.rda"
out_json = r"c:\Users\d\Documents\open-melayu\raw\malay_rootwords.json"

result = pyreadr.read_r(rda_path)
print(f"RDA objects: {list(result.keys())}")

df = result[list(result.keys())[0]]
print(f"DataFrame shape: {df.shape}")
print(f"Columns: {list(df.columns)}")
print("Sample 5:")
print(df.head(5))

# Convert to dictionary: word -> root
mapping = {}
for idx, row in df.iterrows():
    w = str(row.iloc[0]).strip().lower()
    r = str(row.iloc[1]).strip().lower()
    if w and r:
        mapping[w] = r

with open(out_json, 'w', encoding='utf-8') as f:
    json.dump(mapping, f, ensure_ascii=False, indent=2)

print(f"[+] Saved {len(mapping)} word-to-root mappings to {out_json}")
