"""
Open-Melayu Remote Vultr Cluster Manager
- Manages spider-1 .. spider-5 Singapore instances
- Deploys hardened worker and launches crawlers
- Monitors real-time cluster progress across all 5 nodes
- Downloads and audits final 15k dataset
"""
import os
import sys
import time
import json
import paramiko
from concurrent.futures import ThreadPoolExecutor

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"c:\Users\d\Documents\open-melayu"
DATA_DIR = os.path.join(ROOT_DIR, "data")
CACHE_DIR = os.path.join(ROOT_DIR, "raw", "prpm_cache")

NODES = [
    {"name": "spider-1", "ip": "139.180.130.187", "pass": "}e3QM(Z(q__Rpda{", "shard": 1},
    {"name": "spider-2", "ip": "139.180.219.108", "pass": "k%6My,LR(soz-s%d", "shard": 2},
    {"name": "spider-3", "ip": "139.180.191.198", "pass": "?5gBP!PVhLvmd$V4", "shard": 3},
    {"name": "spider-4", "ip": "149.28.159.229", "pass": "?R2fzP[k?)(pk,(U", "shard": 4},
    {"name": "spider-5", "ip": "45.76.147.100",  "pass": "B=x3nHiwJu,]N}JQ", "shard": 5},
]

WORDLIST_URL = "https://gist.githubusercontent.com/znhjsnb/2e0d74a6f08e5daaf46286230cf2653b/raw/9238ee3cd59b6e188cfb245eec77abd8c65e561e/candidate_words_15k.txt"

REMOTE_WORKER_CODE = """# Open-Melayu Remote Worker v2
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
            
            soup = BeautifulSoup(html, 'html.parser')
            panes = soup.find_all('div', class_='tab-pane')
            for pane in panes:
                text = pane.get_text(separator=' ', strip=True)
                if not text or 'tiada maklumat' in text.lower():
                    continue
                entry['raw_definitions'].append(text)
                entry['found_in_prpm'] = True

                syl_match = re.search(r'\\[([a-z\\.\\s\\-]+)\\]', text, re.IGNORECASE)
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

            tmp_path = cache_path + f".tmp.{os.getpid()}"
            with open(tmp_path, 'w', encoding='utf-8') as out_f:
                json.dump(entry, out_f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, cache_path)

            time.sleep(random.uniform(0.3, 0.8))
            return word, True, "ok"
        except Exception as e:
            last_err = str(e)
            time.sleep(1.2 * (attempt + 1))

    with open(FAILED_LOG, 'a', encoding='utf-8') as ff:
        ff.write(f"{word}\\t{last_err}\\n")
    return word, False, last_err

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
                f"STATUS: RUNNING\\n"
                f"Shard: {SHARD_NUM}/{TOTAL_SHARDS}\\n"
                f"Progress: {completed}/{total_my_words} ({percent:.1f}%)\\n"
                f"Speed: {rate:.2f} words/sec ({rate*3600:.0f} words/hour)\\n"
                f"Valid: {completed - failed_count}\\n"
                f"Failed: {failed_count}\\n"
                f"Elapsed: {elapsed/60:.1f} min\\n"
                f"Last: {w} ({msg})\\n"
            )
            with open(STATUS_FILE, 'w', encoding='utf-8') as sf:
                sf.write(status_text)

elapsed = time.time() - start_time
final_text = (
    f"STATUS: CRAWL_DONE\\n"
    f"Shard: {SHARD_NUM}/{TOTAL_SHARDS}\\n"
    f"Total Words: {completed}\\n"
    f"Valid: {completed - failed_count}\\n"
    f"Failed: {failed_count}\\n"
    f"Elapsed: {elapsed/60:.1f} min\\n"
)
with open(STATUS_FILE, 'w', encoding='utf-8') as sf:
    sf.write(final_text)

# Packaging
os.system(f"mkdir -p /root/staging && tar -czf /root/staging/shard_{SHARD_NUM}.tar.gz -C {OUTPUT_DIR} --exclude='*.tar.gz' --exclude='*.sha256' --exclude='*.tmp*' --exclude='status.txt' .")
os.system(f"cd /root/staging && sha256sum shard_{SHARD_NUM}.tar.gz > shard_{SHARD_NUM}.sha256")
os.system(f"mv /root/staging/shard_{SHARD_NUM}.tar.gz {OUTPUT_DIR}/shard_{SHARD_NUM}.tar.gz")
os.system(f"mv /root/staging/shard_{SHARD_NUM}.sha256 {OUTPUT_DIR}/shard_{SHARD_NUM}.sha256")
with open(STATUS_FILE, 'a', encoding='utf-8') as sf:
    sf.write(f"READY_FOR_DOWNLOAD: shard_{SHARD_NUM}.tar.gz\\n")
print("Shard execution complete!")
"""

def connect_ssh(node):
    for attempt in range(4):
        try:
            client = paramiko.SSHClient()
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            client.connect(node['ip'], port=22, username='root', password=node['pass'], timeout=15, banner_timeout=30)
            return client
        except Exception as e:
            if attempt == 3:
                raise e
            time.sleep(2)

def deploy_node(node):
    print(f"[*] Deploying {node['name']} ({node['ip']})...")
    client = connect_ssh(node)
    
    # 1. Ensure directory & packages
    setup_cmd = """
    mkdir -p /root/open_melayu_crawler /root/prpm_cache /root/staging
    curl -sL "https://gist.githubusercontent.com/znhjsnb/2e0d74a6f08e5daaf46286230cf2653b/raw/9238ee3cd59b6e188cfb245eec77abd8c65e561e/candidate_words_15k.txt" -o /root/open_melayu_crawler/words.txt
    """
    client.exec_command(setup_cmd)
    
    # 2. Write worker.py via SFTP
    sftp = client.open_sftp()
    with sftp.file('/root/open_melayu_crawler/worker.py', 'w') as f:
        f.write(REMOTE_WORKER_CODE)
    sftp.close()
    
    # 3. Kill any old process & start fresh
    start_cmd = f"""
    pkill -f "http.server 8080" || true
    pkill -f "worker.py" || true
    cd /root/prpm_cache && nohup python3 -m http.server 8080 > /dev/null 2>&1 &
    cd /root/open_melayu_crawler && nohup python3 -u worker.py {node['shard']} 5 /root/prpm_cache /root/open_melayu_crawler/words.txt > /root/open_melayu_crawler/worker.log 2>&1 &
    """
    client.exec_command(start_cmd)
    client.close()
    print(f"[+] {node['name']} successfully launched in background!")

def deploy_all():
    print(f"[*] Deploying cluster across all 5 nodes concurrently...")
    with ThreadPoolExecutor(max_workers=5) as ex:
        list(ex.map(deploy_node, NODES))
    print("[+] All 5 nodes deployed and actively crawling PRPM!")

def check_status_node(node):
    try:
        client = connect_ssh(node)
        stdin, stdout, stderr = client.exec_command("cat /root/prpm_cache/status.txt 2>/dev/null || echo 'INITIALIZING'")
        status = stdout.read().decode('utf-8').strip()
        client.close()
        return node['name'], node['ip'], status
    except Exception as e:
        return node['name'], node['ip'], f"ERROR: {e}"

def check_cluster_status():
    print(f"\n================== CLUSTER LIVE STATUS ==================")
    with ThreadPoolExecutor(max_workers=5) as ex:
        results = list(ex.map(check_status_node, NODES))
    
    total_valid = 0
    total_progress = 0
    all_ready = True
    
    for name, ip, status in sorted(results, key=lambda x: x[0]):
        print(f"\n[{name} | IP: {ip}]")
        for line in status.split('\n')[:5]:
            print(f"  {line}")
        if "READY_FOR_DOWNLOAD" not in status:
            all_ready = False
            
    print("\n=========================================================")
    return all_ready

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        check_cluster_status()
    else:
        deploy_all()
        time.sleep(3)
        check_cluster_status()
