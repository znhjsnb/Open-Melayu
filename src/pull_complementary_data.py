"""
Pull and compile complementary authoritative P0 data sources:
1. Malaya official spoken/slang rules (MIT) -> raw/malaya_colloquial_rules.json
2. malaytextr root words (.rda) -> raw/malayrootwords.rda
3. Tatoeba Malay-English-Chinese aligned sentences -> raw/tatoeba_aligned_triplet.json
"""
import os
import sys
import urllib.request
import bz2
import json
import re

RAW_DIR = r"c:\Users\d\Documents\open-melayu\raw"
os.makedirs(RAW_DIR, exist_ok=True)

def download(url, dest, desc):
    if os.path.exists(dest):
        print(f"[i] {dest} already exists ({os.path.getsize(dest)/(1024):.1f} KB), skipping.")
        return True
    print(f"[*] Downloading {desc} from {url}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, 'wb') as f:
            f.write(resp.read())
        print(f"[+] Downloaded {dest} ({os.path.getsize(dest)/(1024):.1f} KB)")
        return True
    except Exception as e:
        print(f"[-] Failed {desc}: {e}")
        return False

def pull_malaya_rules():
    url = "https://raw.githubusercontent.com/malaysia-ai/malaya/master/malaya/text/rules.py"
    raw_py = os.path.join(RAW_DIR, "malaya_rules_raw.py")
    out_json = os.path.join(RAW_DIR, "malaya_colloquial_rules.json")
    
    if not os.path.exists(raw_py):
        download(url, raw_py, "Malaya text rules")
        
    if os.path.exists(raw_py) and not os.path.exists(out_json):
        print("[*] Extracting rules_normalizer from Malaya...")
        with open(raw_py, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Extract rules_normalizer dictionary
        # Find start of rules_normalizer = {
        m = re.search(r'rules_normalizer\s*=\s*\{([^}]+)\}', content, re.DOTALL)
        if m:
            dict_str = "{" + m.group(1) + "}"
            try:
                # Safely parse dict
                import ast
                rules_dict = ast.literal_eval(dict_str)
                with open(out_json, 'w', encoding='utf-8') as f:
                    json.dump(rules_dict, f, ensure_ascii=False, indent=2)
                print(f"[+] Successfully extracted {len(rules_dict)} slang/abbreviation mappings to {out_json}")
            except Exception as e:
                print(f"[-] ast eval error: {e}")

def pull_malaytextr_roots():
    url = "https://raw.githubusercontent.com/zahiernasrudin/malaytextr/master/data/malayrootwords.rda"
    dest = os.path.join(RAW_DIR, "malayrootwords.rda")
    download(url, dest, "malaytextr malayrootwords.rda")

def pull_tatoeba_sentences():
    base_url = "https://downloads.tatoeba.org/exports/per_language/zsm/"
    files = [
        ("zsm_sentences.tsv.bz2", "Tatoeba Malay sentences"),
        ("zsm-eng_links.tsv.bz2", "Tatoeba Malay-English links"),
        ("zsm-cmn_links.tsv.bz2", "Tatoeba Malay-Chinese links")
    ]
    for fn, desc in files:
        dest = os.path.join(RAW_DIR, fn)
        download(base_url + fn, dest, desc)

if __name__ == "__main__":
    print("[*] Step 1: Pulling Malaya rules...")
    pull_malaya_rules()
    print("[*] Step 2: Pulling malaytextr root words...")
    pull_malaytextr_roots()
    print("[*] Step 3: Pulling Tatoeba sentences...")
    pull_tatoeba_sentences()
    print("[+] All complementary sources processed.")
