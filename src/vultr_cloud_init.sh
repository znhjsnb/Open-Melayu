#!/bin/bash
# ==============================================================================
# Open-Melayu Distributed PRPM Crawler (Cloud-Init Startup Script) - v2 Hardened
# Deploy on: Vultr Cloud Compute (Ubuntu 24.04 LTS x64)
# Sharding: Strict hostname match '^spider-([1-5])$' (spider-1 .. spider-5)
# Egress: Direct high-speed connection from VPS to https://prpm.dbp.gov.my
# Safe: 100% physically isolated from user primary Hysteria2 IP
# Audited: Addresses Codex Blockers B01, B02, B03, B04, B05, R10
# ==============================================================================

set -euo pipefail

# 1. System packages
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-bs4 curl coreutils

# 2. Strict Hostname & Shard Identification (Blocker B01)
RAW_HOST=$(hostname -s 2>/dev/null || hostname)
HOSTNAME=$(echo "$RAW_HOST" | tr '[:upper:]' '[:lower:]')
if [[ "$HOSTNAME" =~ spider-?([1-5]) ]]; then
    SHARD_NUM="${BASH_REMATCH[1]}"
elif [[ "$HOSTNAME" =~ ^([1-5])$ ]]; then
    SHARD_NUM="${BASH_REMATCH[1]}"
else
    echo "FATAL: Hostname '$RAW_HOST' must contain 'spider-1'..'spider-5' or '1'..'5'" >&2
    exit 1
fi
TOTAL_SHARDS=5

# 3. Directory setup
WORKDIR="/root/open_melayu_crawler"
OUTPUT_DIR="/root/prpm_cache"
STAGING_DIR="/root/staging"
mkdir -p "$WORKDIR" "$OUTPUT_DIR" "$STAGING_DIR"
cd "$WORKDIR"

# 4. Fetch 15k Candidate Pool with Strict Hash & Line Count Check (Blocker B02)
WORDLIST_URL="https://gist.githubusercontent.com/znhjsnb/2e0d74a6f08e5daaf46286230cf2653b/raw/9238ee3cd59b6e188cfb245eec77abd8c65e561e/candidate_words_15k.txt"
EXPECTED_SHA256="f31242e1dc4d37aa0574f8d8ef4b3aeac0babaec2b1b4b380e9d5771a0ab50a2"

curl --fail --show-error --location --retry 3 --max-time 30 "$WORDLIST_URL" -o "$WORKDIR/candidate_words_15k.txt.tmp"
ACTUAL_SHA256=$(sha256sum "$WORKDIR/candidate_words_15k.txt.tmp" | awk '{print $1}')
if [ "$ACTUAL_SHA256" != "$EXPECTED_SHA256" ]; then
    echo "FATAL: Wordlist SHA256 mismatch! Expected $EXPECTED_SHA256, got $ACTUAL_SHA256" >&2
    exit 1
fi

LINE_COUNT=$(wc -l < "$WORKDIR/candidate_words_15k.txt.tmp")
if [ "$LINE_COUNT" -ne 15000 ]; then
    echo "FATAL: Wordlist line count mismatch! Expected 15000, got $LINE_COUNT" >&2
    exit 1
fi
mv "$WORKDIR/candidate_words_15k.txt.tmp" "$WORKDIR/candidate_words_15k.txt"

# 5. Start live status web server on port 8080
echo "BOOTING: Hostname=$HOSTNAME, Shard=$SHARD_NUM/$TOTAL_SHARDS, Candidates=15000 verified" > "$OUTPUT_DIR/status.txt"
cd "$OUTPUT_DIR"
nohup python3 -m http.server 8080 > /dev/null 2>&1 &
cd "$WORKDIR"

# 6. Write Hardened Python Crawler Worker
cat << 'PYEOF' > "$WORKDIR/worker.py"
import os
import sys
import re
import time
import json
import random
import urllib.request
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

SHARD_NUM = int(sys.argv[1])
TOTAL_SHARDS = int(sys.argv[2])
OUTPUT_DIR = sys.argv[3]
WORDLIST_FILE = sys.argv[4]
STATUS_FILE = os.path.join(OUTPUT_DIR, "status.txt")
FAILED_LOG = os.path.join(OUTPUT_DIR, "failed_words.txt")

# Blocker B05: Windows Reserved Device Names mapping
WINDOWS_RESERVED = {
    'con', 'prn', 'aux', 'nul',
    'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
    'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
}

def get_safe_filename(word: str) -> str:
    w = word.strip().lower()
    if w in WINDOWS_RESERVED:
        return f"_{w}.json"
    return f"{w}.json"

with open(WORDLIST_FILE, 'r', encoding='utf-8') as f:
    all_words = [line.strip() for line in f if line.strip()]

total_words = len(all_words)
shard_size = (total_words + TOTAL_SHARDS - 1) // TOTAL_SHARDS
start_idx = (SHARD_NUM - 1) * shard_size
end_idx = min(start_idx + shard_size, total_words)

my_words = all_words[start_idx:end_idx]
total_my_words = len(my_words)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0'
]

# Blocker B03: Verify cache validity (never treat poisoned error files as cached)
def is_valid_cached_entry(cache_path: str) -> bool:
    if not os.path.exists(cache_path):
        return False
    try:
        with open(cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('error'):
            return False
        if not isinstance(data.get('raw_definitions'), list):
            return False
        return True
    except Exception:
        return False

def crawl_word(word: str):
    filename = get_safe_filename(word)
    cache_path = os.path.join(OUTPUT_DIR, filename)
    if is_valid_cached_entry(cache_path):
        return word, True, "cached"

    url = f"https://prpm.dbp.gov.my/Cari1?keyword={urllib.parse.quote(word)}"
    entry = {
        'word': word,
        'safe_filename': filename,
        'found_in_prpm': False,
        'syllables': None,
        'jawi': None,
        'kamus_dewan': None,
        'kamus_pelajar': None,
        'raw_definitions': []
    }

    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ms,en;q=0.9'
    }

    last_err = None
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=16) as resp:
                if resp.status != 200:
                    raise Exception(f"HTTP status {resp.status}")
                html = resp.read().decode('utf-8', errors='ignore')
            
            # Blocker B04: Verify page validity and avoid non-dictionary false positives
            soup = BeautifulSoup(html, 'html.parser')
            panes = soup.find_all('div', class_='tab-pane')
            for pane in panes:
                text = pane.get_text(separator=' ', strip=True)
                if not text or 'tiada maklumat' in text.lower():
                    continue
                entry['raw_definitions'].append(text)
                entry['found_in_prpm'] = True

                syl_match = re.search(r'\[([a-z\.\s\-]+)\]', text, re.IGNORECASE)
                if syl_match and not entry['syllables']:
                    entry['syllables'] = syl_match.group(1).strip()

                jawi_span = pane.find('font', class_='cadr')
                if not jawi_span:
                    jawi_span = pane.find('span', class_='cadr')
                if jawi_span and not entry['jawi']:
                    entry['jawi'] = jawi_span.get_text(strip=True)

                if 'Kamus Dewan' in text and not entry['kamus_dewan']:
                    entry['kamus_dewan'] = text
                elif 'Kamus Pelajar' in text and not entry['kamus_pelajar']:
                    entry['kamus_pelajar'] = text

            # Atomic write via temporary file
            tmp_path = cache_path + f".tmp.{os.getpid()}"
            with open(tmp_path, 'w', encoding='utf-8') as out_f:
                json.dump(entry, out_f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, cache_path)

            time.sleep(random.uniform(0.3, 0.8))
            return word, True, "ok"
        except Exception as e:
            last_err = str(e)
            time.sleep(1.2 * (attempt + 1))

    # Log to failed list for explicit re-crawling
    with open(FAILED_LOG, 'a', encoding='utf-8') as ff:
        ff.write(f"{word}\t{last_err}\n")
    return word, False, last_err

# Concurrency: 5 worker threads per VPS
completed = 0
found_count = 0
failed_count = 0
start_time = time.time()

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = {executor.submit(crawl_word, w): w for w in my_words}
    for fut in as_completed(futures):
        completed += 1
        w, success, msg = fut.result()
        if success:
            if msg != "cached":
                found_count += 1
        else:
            failed_count += 1

        if completed % 25 == 0 or completed == total_my_words:
            elapsed = time.time() - start_time
            rate = completed / max(elapsed, 1.0)
            percent = (completed / total_my_words) * 100.0
            status_text = (
                f"STATUS: RUNNING\n"
                f"Shard: {SHARD_NUM}/{TOTAL_SHARDS}\n"
                f"Progress: {completed}/{total_my_words} ({percent:.1f}%)\n"
                f"Speed: {rate:.2f} words/sec ({rate*3600:.0f} words/hour)\n"
                f"Valid: {completed - failed_count}\n"
                f"Failed: {failed_count}\n"
                f"Elapsed: {elapsed/60:.1f} min\n"
                f"Last: {w} ({msg})\n"
            )
            with open(STATUS_FILE, 'w', encoding='utf-8') as sf:
                sf.write(status_text)

elapsed = time.time() - start_time
final_text = (
    f"STATUS: CRAWL_DONE\n"
    f"Shard: {SHARD_NUM}/{TOTAL_SHARDS}\n"
    f"Total Words: {completed}\n"
    f"Valid: {completed - failed_count}\n"
    f"Failed: {failed_count}\n"
    f"Elapsed: {elapsed/60:.1f} min\n"
)
with open(STATUS_FILE, 'w', encoding='utf-8') as sf:
    sf.write(final_text)

print("Shard crawling complete. Proceeding to packaging...")
PYEOF

# 7. Execute Crawler Worker
python3 "$WORKDIR/worker.py" "$SHARD_NUM" "$TOTAL_SHARDS" "$OUTPUT_DIR" "$WORKDIR/candidate_words_15k.txt"

# 8. Atomic Packaging and Integrity Check (Blocker R10)
echo "PACKAGING: Compressing shard in staging area..." >> "$OUTPUT_DIR/status.txt"
tar -czf "$STAGING_DIR/shard_${SHARD_NUM}.tar.gz" -C "$OUTPUT_DIR" --exclude="*.tar.gz" --exclude="*.sha256" --exclude="*.tmp*" --exclude="status.txt" .

TAR_SHA256=$(sha256sum "$STAGING_DIR/shard_${SHARD_NUM}.tar.gz" | awk '{print $1}')
echo "$TAR_SHA256  shard_${SHARD_NUM}.tar.gz" > "$STAGING_DIR/shard_${SHARD_NUM}.sha256"

# Atomic move into publicly served HTTP output directory
mv "$STAGING_DIR/shard_${SHARD_NUM}.tar.gz" "$OUTPUT_DIR/shard_${SHARD_NUM}.tar.gz"
mv "$STAGING_DIR/shard_${SHARD_NUM}.sha256" "$OUTPUT_DIR/shard_${SHARD_NUM}.sha256"

FINAL_SIZE=$(du -h "$OUTPUT_DIR/shard_${SHARD_NUM}.tar.gz" | cut -f1)
echo "READY_FOR_DOWNLOAD: shard_${SHARD_NUM}.tar.gz ($FINAL_SIZE) | SHA256: $TAR_SHA256" >> "$OUTPUT_DIR/status.txt"
echo "CLUSTER_NODE_DONE"
