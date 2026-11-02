"""
Continuous Background PRPM Crawler for Open-Melayu:
- Reads priority candidates from data/candidate_pool_15k.json
- Automatically checks raw/prpm_cache/{word}.json, skips already cached
- Polite jittered rate limiting (0.7s ~ 1.2s)
- Automatic fallback: direct connection -> local proxy (127.0.0.1:7897) if direct times out
- Never crashes on network error; logs gracefully and proceeds
- Saves detailed checkpoint progress to data/crawler_progress.json
"""
import os
import sys
import re
import time
import json
import random
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"c:\Users\d\Documents\open-melayu"
CACHE_DIR = os.path.join(ROOT_DIR, "raw", "prpm_cache")
DATA_DIR = os.path.join(ROOT_DIR, "data")
CANDIDATE_FILE = os.path.join(DATA_DIR, "candidate_pool_15k.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "crawler_progress.json")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
]

def make_request(url: str, proxy: str = None, timeout: int = 8) -> str:
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9,ms;q=0.8'
    }
    req = urllib.request.Request(url, headers=headers)
    if proxy:
        req.set_proxy(proxy, 'http')
        req.set_proxy(proxy, 'https')
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode('utf-8', errors='ignore')

def fetch_prpm_word(word: str) -> dict:
    word = word.strip().lower()
    url = f"https://prpm.dbp.gov.my/Cari1?keyword={urllib.parse.quote(word)}"
    
    entry = {
        'word': word,
        'found_in_prpm': False,
        'syllables': None,
        'jawi': None,
        'kamus_dewan': None,
        'kamus_pelajar': None,
        'raw_definitions': []
    }
    
    html = None
    # 1. Try direct with 7s timeout
    try:
        html = make_request(url, proxy=None, timeout=7)
    except Exception as e_direct:
        # 2. Try via local Clash proxy 127.0.0.1:7897 with 8s timeout
        try:
            html = make_request(url, proxy="127.0.0.1:7897", timeout=8)
        except Exception as e_proxy:
            entry['error'] = f"Direct: {e_direct}; Proxy: {e_proxy}"
            return entry

    if html:
        soup = BeautifulSoup(html, 'html.parser')
        panes = soup.find_all('div', class_='tab-pane')
        for pane in panes:
            text = pane.get_text(separator=' ', strip=True)
            if not text:
                continue
            entry['raw_definitions'].append(text)
            entry['found_in_prpm'] = True
            
            # Extract syllables
            syl_match = re.search(r'\[([a-z\.\s\-]+)\]', text, re.IGNORECASE)
            if syl_match and not entry['syllables']:
                entry['syllables'] = syl_match.group(1).strip()
                
            # Extract Jawi
            jawi_span = pane.find('font', class_='cadr')
            if jawi_span and not entry['jawi']:
                entry['jawi'] = jawi_span.get_text(strip=True)
                
            if 'Kamus Dewan' in text and not entry['kamus_dewan']:
                entry['kamus_dewan'] = text
            elif 'Kamus Pelajar' in text and not entry['kamus_pelajar']:
                entry['kamus_pelajar'] = text

    return entry

def run_continuous_crawler(max_count: int = None, delay: float = 0.8):
    print("[*] PRPM Continuous Background Crawler started...")
    
    if not os.path.exists(CANDIDATE_FILE):
        print(f"[-] Candidate file {CANDIDATE_FILE} not found!")
        return

    with open(CANDIDATE_FILE, 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    total_candidates = len(candidates)
    crawled_this_session = 0
    found_count = 0
    skipped_count = 0

    start_time = time.time()
    
    for idx, item in enumerate(candidates, 1):
        if max_count and crawled_this_session >= max_count:
            print(f"[*] Reached session limit of {max_count} words.")
            break
            
        word = item['word'].strip().lower()
        cache_path = os.path.join(CACHE_DIR, f"{word}.json")
        
        if os.path.exists(cache_path):
            skipped_count += 1
            continue

        # Fetch with error suppression
        try:
            entry = fetch_prpm_word(word)
        except Exception as e:
            entry = {'word': word, 'found_in_prpm': False, 'error': str(e)}

        crawled_this_session += 1
        
        if entry.get('found_in_prpm'):
            found_count += 1

        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)

        # Update progress checkpoint every 5 items
        if crawled_this_session % 5 == 0 or idx == total_candidates:
            progress = {
                'total_candidates': total_candidates,
                'current_index': idx,
                'crawled_this_session': crawled_this_session,
                'found_this_session': found_count,
                'cached_total': len(os.listdir(CACHE_DIR)),
                'elapsed_seconds': round(time.time() - start_time, 1),
                'last_word': word,
                'last_found': entry.get('found_in_prpm'),
                'updated_at': time.strftime("%Y-%m-%d %H:%M:%S")
            }
            with open(PROGRESS_FILE, 'w', encoding='utf-8') as pf:
                json.dump(progress, pf, ensure_ascii=False, indent=2)

            print(f"[{idx}/{total_candidates}] Crawled '{word}' (PRPM: {entry.get('found_in_prpm')}) | Total cached: {progress['cached_total']}", flush=True)

        # Polite jitter
        sleep_time = delay + random.uniform(0.1, 0.4)
        time.sleep(sleep_time)

    print(f"[+] Crawler session finished. Crawled: {crawled_this_session}, Found in PRPM: {found_count}, Skipped existing: {skipped_count}", flush=True)

if __name__ == "__main__":
    max_c = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_continuous_crawler(max_count=max_c, delay=0.8)

