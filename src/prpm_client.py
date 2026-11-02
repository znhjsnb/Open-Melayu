import os
import sys
import json
import re
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

CACHE_DIR = r"c:\Users\d\Documents\open-melayu\raw\prpm_cache"
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9,ms;q=0.8'
}

def query_prpm(word: str, force_refresh: bool = False) -> dict:
    word = word.strip().lower()
    cache_file = os.path.join(CACHE_DIR, f"{word}.json")
    
    if not force_refresh and os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass

    url = f"https://prpm.dbp.gov.my/Cari1?keyword={urllib.parse.quote(word)}"
    req = urllib.request.Request(url, headers=HEADERS)
    
    entry = {
        'word': word,
        'found_in_prpm': False,
        'syllables': None,
        'jawi': None,
        'kamus_dewan': None,
        'kamus_pelajar': None,
        'raw_definitions': []
    }
    
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html, 'html.parser')
            
            # Check for Kamus Bahasa Melayu panel
            panes = soup.find_all('div', class_='tab-pane')
            for pane in panes:
                text = pane.get_text(separator=' ', strip=True)
                if not text:
                    continue
                entry['raw_definitions'].append(text)
                entry['found_in_prpm'] = True
                
                # Syllable pattern: [be.la.jar]
                syl_match = re.search(r'\[([a-z\.\s\-]+)\]', text, re.IGNORECASE)
                if syl_match and not entry['syllables']:
                    entry['syllables'] = syl_match.group(1).strip()
                    
                # Jawi extraction
                jawi_span = pane.find('font', class_='cadr')
                if jawi_span and not entry['jawi']:
                    entry['jawi'] = jawi_span.get_text(strip=True)
                    
                if 'Kamus Dewan' in text and not entry['kamus_dewan']:
                    entry['kamus_dewan'] = text
                elif 'Kamus Pelajar' in text and not entry['kamus_pelajar']:
                    entry['kamus_pelajar'] = text

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
            
    except Exception as e:
        print(f"[-] Error querying PRPM for '{word}': {e}")
        entry['error'] = str(e)

    return entry

if __name__ == "__main__":
    test_words = ["ajar", "belajar", "pelajar", "tak"]
    print("[*] Testing PRPM live querying and caching...")
    for w in test_words:
        res = query_prpm(w)
        print(f"\n[Word: {w}]")
        print(f"  Found in PRPM: {res['found_in_prpm']}")
        print(f"  Syllables: {res['syllables']}")
        print(f"  Jawi: {res['jawi']}")
        if res['kamus_dewan']:
            print(f"  Kamus Dewan sample: {res['kamus_dewan'][:120]}...")
