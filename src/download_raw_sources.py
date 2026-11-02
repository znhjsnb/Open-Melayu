"""
Download authoritative raw source datasets for Open-Melayu:
1. Kaikki.org Wiktionary Malay extraction (JSONL)
2. Frequency lists & Common word lists
3. Malay root word mappings (Kata Dasar)
4. Malay-Dataset bilingual dictionaries
"""
import os
import sys
import urllib.request
import gzip
import shutil
import json

RAW_DIR = r"c:\Users\d\Documents\open-melayu\raw"
os.makedirs(RAW_DIR, exist_ok=True)

def download_file(url, dest_path, description=""):
    print(f"[*] Downloading {description} from {url}...")
    try:
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, timeout=60) as response, open(dest_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"[+] Downloaded {dest_path} ({size_mb:.2f} MB)")
        return True
    except Exception as e:
        print(f"[-] Failed to download {url}: {e}")
        return False

def download_and_extract_kaikki():
    gz_path = os.path.join(RAW_DIR, "ms-extract.jsonl.gz")
    jsonl_path = os.path.join(RAW_DIR, "kaikki-malay.jsonl")
    url = "https://kaikki.org/dictionary/raw/ms/ms-extract.jsonl.gz"
    
    if os.path.exists(jsonl_path):
        print(f"[i] {jsonl_path} already exists, skipping download.")
        return
        
    if download_file(url, gz_path, "Kaikki Malay JSONL.GZ"):
        print("[*] Extracting gzip...")
        with gzip.open(gz_path, 'rb') as f_in, open(jsonl_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
        print(f"[+] Extracted to {jsonl_path} ({os.path.getsize(jsonl_path)/(1024*1024):.2f} MB)")
        try:
            os.remove(gz_path)
        except:
            pass

def download_other_sources():
    sources = [
        # frekwencja most common words
        ("https://raw.githubusercontent.com/frekwencja/most-common-words-multilingual/master/languages/ms.txt",
         os.path.join(RAW_DIR, "frequency_5000_frekwencja.txt"),
         "Frekwencja Top 5000 Malay"),
        # HermitDave FrequencyWords Malay (OpenSubtitles)
        ("https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/ms/ms_full.txt",
         os.path.join(RAW_DIR, "opensubtitles_frequency_ms_full.txt"),
         "OpenSubtitles Full Malay Frequency List"),
        ("https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/ms/ms_50k.txt",
         os.path.join(RAW_DIR, "opensubtitles_frequency_ms_50k.txt"),
         "OpenSubtitles Top 50k Malay Frequency List"),
        # GitHub raw malaya-dataset dictionary files
        ("https://raw.githubusercontent.com/huseinzol05/malay-dataset/master/dictionary/english-malay/clean-dictionary.json",
         os.path.join(RAW_DIR, "malaya_english_malay_clean.json"),
         "Malaya Dataset English-Malay Clean Dictionary"),
        ("https://raw.githubusercontent.com/huseinzol05/malay-dataset/master/dictionary/synonym/synonym.json",
         os.path.join(RAW_DIR, "malaya_synonym.json"),
         "Malaya Dataset 90k Synonyms"),
        ("https://raw.githubusercontent.com/huseinzol05/malay-dataset/master/normalization/normalizer/word.json",
         os.path.join(RAW_DIR, "malaya_normalizer_words.json"),
         "Malaya Normalizer Standard Words")
    ]
    
    for url, dest, desc in sources:
        if not os.path.exists(dest):
            download_file(url, dest, desc)
        else:
            print(f"[i] {dest} already exists, skipping.")

if __name__ == "__main__":
    download_other_sources()
    download_and_extract_kaikki()
