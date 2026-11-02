import os
import json
import bz2

RAW_DIR = r"c:\Users\d\Documents\open-melayu\raw"

def check_rules():
    p = os.path.join(RAW_DIR, "malaya_colloquial_rules.json")
    with open(p, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"[Malaya Rules] Count: {len(data)}")
    samples = ['tak', 'nak', 'diorang', 'xde', 'dkt', 'sbb', 'korg', 'mcm', 'yg', 'blh']
    for s in samples:
        print(f"  {s} -> {data.get(s)}")

def check_tatoeba():
    sent_path = os.path.join(RAW_DIR, "zsm_sentences.tsv.bz2")
    sentences = {}
    with bz2.open(sent_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                sid, lang, text = parts[0], parts[1], parts[2]
                sentences[sid] = text
    print(f"[Tatoeba] Total Malay sentences: {len(sentences)}")
    
    eng_links_path = os.path.join(RAW_DIR, "zsm-eng_links.tsv.bz2")
    eng_links = []
    with bz2.open(eng_links_path, 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                eng_links.append((parts[0], parts[1]))
    print(f"[Tatoeba] Malay-English linked pairs: {len(eng_links)}")

if __name__ == "__main__":
    check_rules()
    check_tatoeba()
