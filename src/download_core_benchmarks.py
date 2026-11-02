import os
import urllib.request
import shutil

RAW_DIR = r"c:\Users\d\Documents\open-melayu\raw"

sources = [
    # 1. Kaikki Malay JSONL (27.5 MB)
    ("https://kaikki.org/dictionary/Malay/kaikki.org-dictionary-Malay.jsonl",
     os.path.join(RAW_DIR, "kaikki_malay.jsonl"),
     "Kaikki Official Malay JSONL"),
    # 2. Malaysia-AI DBP Malay Words (Dewan Bahasa dan Pustaka Official Words)
    ("https://huggingface.co/datasets/malaysia-ai/DBP/resolve/main/malay-words-v2.json",
     os.path.join(RAW_DIR, "dbp_malay_words_v2.json"),
     "DBP Official Malay Words v2 (HuggingFace)"),
    # 3. Zahier Nasrudin Malay root words (CSV/Rda raw)
    ("https://raw.githubusercontent.com/zahiernasrudin/malaytextr/master/data-raw/rootwords.csv",
     os.path.join(RAW_DIR, "malay_rootwords_zahier.csv"),
     "Zahier Malay Root Words CSV"),
]

for url, dest, desc in sources:
    if os.path.exists(dest):
        print(f"[i] {dest} already exists ({os.path.getsize(dest)/(1024*1024):.2f} MB), skipping.")
        continue
    print(f"[*] Downloading {desc} from {url}...")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=120) as response, open(dest, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        print(f"[+] Downloaded {dest} ({os.path.getsize(dest)/(1024*1024):.2f} MB)")
    except Exception as e:
        print(f"[-] Failed {desc}: {e}")
