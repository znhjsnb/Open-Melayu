import os
import urllib.request
import shutil

RAW_DIR = r"c:\Users\d\Documents\open-melayu\raw"

sources = [
    ("https://huggingface.co/datasets/miserableface/kaikki-melayu-entries/resolve/main/entries-ms.parquet",
     os.path.join(RAW_DIR, "entries-ms.parquet"),
     "Kaikki Melayu Entries MS Parquet (17.5k entries)"),
    ("https://huggingface.co/datasets/miserableface/melayu-wordnet/resolve/main/wordnet-ms.parquet",
     os.path.join(RAW_DIR, "wordnet-ms.parquet"),
     "Wordnet Bahasa MS Parquet (105k rows)"),
]

for url, dest, desc in sources:
    if os.path.exists(dest):
        print(f"[i] {dest} exists, skipping.")
        continue
    print(f"[*] Downloading {desc}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=120) as resp, open(dest, 'wb') as f:
            shutil.copyfileobj(resp, f)
        print(f"[+] Downloaded {dest} ({os.path.getsize(dest)/(1024*1024):.2f} MB)")
    except Exception as e:
        print(f"[-] Failed {desc}: {e}")
