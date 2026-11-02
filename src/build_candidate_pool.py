"""
Build the Open-Melayu 15,000 Candidate Lexicon Pool:
Cross-referencing:
1. OpenSubtitles spoken frequency ranking
2. DBP vocabulary list (standard spelling check)
3. Kaikki Wiktionary (IPA, senses, etymology)
4. malayrootwords (Kata Dasar root mapping)
5. Malaya normalizer (slang/chat abbreviation mapping)
6. Tatoeba sentence link availability
"""
import os
import json
import bz2

RAW_DIR = r"c:\Users\d\Documents\open-melayu\raw"
DATA_DIR = r"c:\Users\d\Documents\open-melayu\data"
os.makedirs(DATA_DIR, exist_ok=True)

def load_data():
    print("[*] Loading DBP list...")
    with open(os.path.join(RAW_DIR, "dbp_malay_words_v2.json"), 'r', encoding='utf-8') as f:
        dbp_set = set(w.strip().lower() for w in json.load(f))
        
    print("[*] Loading Malaya colloquial rules...")
    with open(os.path.join(RAW_DIR, "malaya_colloquial_rules.json"), 'r', encoding='utf-8') as f:
        colloquial_rules = json.load(f)
        
    print("[*] Loading Malay root words mapping...")
    with open(os.path.join(RAW_DIR, "malay_rootwords.json"), 'r', encoding='utf-8') as f:
        root_mapping = json.load(f)
        
    print("[*] Loading Kaikki index...")
    kaikki_map = {}
    with open(os.path.join(RAW_DIR, "kaikki_malay.jsonl"), 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            item = json.loads(line)
            w = item.get('word', '').strip().lower()
            if w and w not in kaikki_map:
                ipa = None
                sounds = item.get('sounds', []) or []
                for s in sounds:
                    if 'ipa' in s:
                        ipa = s['ipa']
                        break
                etym = item.get('etymology_text')
                senses = [s.get('glosses', []) for s in item.get('senses', [])]
                pos = item.get('pos')
                kaikki_map[w] = {
                    'pos': pos,
                    'ipa': ipa,
                    'etymology': etym,
                    'senses_count': len(senses)
                }

    print("[*] Loading Tatoeba sentence index...")
    tatoeba_sentences = set()
    with bz2.open(os.path.join(RAW_DIR, "zsm_sentences.tsv.bz2"), 'rt', encoding='utf-8', errors='ignore') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 3:
                # Add individual words in sentence
                words = [w.lower() for w in parts[2].split()]
                tatoeba_sentences.update(words)

    print("[*] Processing Frequency Words Top 15,000...")
    candidates = []
    freq_path = os.path.join(RAW_DIR, "opensubtitles_frequency_ms_full.txt")
    with open(freq_path, 'r', encoding='utf-8', errors='ignore') as f:
        rank = 0
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.rsplit(maxsplit=1)
            if len(parts) != 2:
                continue
            word, count_str = parts[0].strip().lower(), parts[1]
            try:
                count = int(count_str)
            except:
                continue
                
            rank += 1
            if rank > 15000:
                break
                
            k_info = kaikki_map.get(word)
            root = root_mapping.get(word)
            slang_norm = colloquial_rules.get(word)
            in_dbp = word in dbp_set
            
            # Determine category tags
            tags = []
            if slang_norm:
                tags.append("colloquial_shortcut")
            if in_dbp:
                tags.append("standard_dbp")
            if k_info:
                tags.append("wiktionary_documented")
            if root:
                tags.append("derived_imbuhan")
            elif in_dbp and not root:
                tags.append("potential_root")
                
            entry = {
                'rank': rank,
                'word': word,
                'frequency_count': count,
                'in_dbp': in_dbp,
                'in_kaikki': bool(k_info),
                'pos_kaikki': k_info['pos'] if k_info else None,
                'ipa': k_info['ipa'] if k_info else None,
                'root_word': root,
                'colloquial_expansion': slang_norm,
                'has_tatoeba': word in tatoeba_sentences,
                'tags': tags
            }
            candidates.append(entry)

    out_file = os.path.join(DATA_DIR, "candidate_pool_15k.json")
    with open(out_file, 'w', encoding='utf-8') as f:
        json.dump(candidates, f, ensure_ascii=False, indent=2)
    print(f"[+] Successfully compiled {len(candidates)} candidates to {out_file}")

    # Also extract Pilot 50 candidates
    pilot_50 = []
    # Pick diverse 50: key verbs, high freq words, common slang, derivations
    pilot_targets = [
        "saya", "yang", "aku", "dia", "awak", "kau", "ini", "di", "tak", "dan",
        "akan", "tidak", "kita", "apa", "kamu", "itu", "untuk", "ada", "boleh", "mereka",
        "nak", "tahu", "macam", "jadi", "orang", "diorang", "kat", "bila", "buat", "tengok",
        "ajar", "belajar", "mengajar", "pelajar", "pelajaran", "makan", "makanan", "jalan", "berjalan", "perjalanan",
        "kerja", "pekerja", "pekerjaan", "minum", "minuman", "rumah", "buku", "cantik", "besar", "baik"
    ]
    pilot_set = set(pilot_targets)
    for c in candidates:
        if c['word'] in pilot_set:
            pilot_50.append(c)
            pilot_set.remove(c['word'])
    # If any remaining
    for w in list(pilot_set):
        k_info = kaikki_map.get(w)
        pilot_50.append({
            'rank': -1,
            'word': w,
            'frequency_count': 0,
            'in_dbp': w in dbp_set,
            'in_kaikki': bool(k_info),
            'pos_kaikki': k_info['pos'] if k_info else None,
            'ipa': k_info['ipa'] if k_info else None,
            'root_word': root_mapping.get(w),
            'colloquial_expansion': colloquial_rules.get(w),
            'has_tatoeba': w in tatoeba_sentences,
            'tags': ['pilot_target']
        })

    pilot_file = os.path.join(DATA_DIR, "pilot_50_candidates.json")
    with open(pilot_file, 'w', encoding='utf-8') as f:
        json.dump(pilot_50, f, ensure_ascii=False, indent=2)
    print(f"[+] Successfully compiled {len(pilot_50)} Pilot candidates to {pilot_file}")

if __name__ == "__main__":
    load_data()
