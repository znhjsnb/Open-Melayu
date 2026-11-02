"""
Open-Melayu Local Shard Collector & Aggregator
- Connects to 5 Vultr crawler nodes via HTTP port 8080
- Verifies sha256 checksums before unpacking
- Safely extracts into raw/prpm_cache (Windows NTFS safe)
- Audits full 15,000 candidate pool coverage
- Produces missing/failed word manifest for zero-gap guarantee
"""
import os
import sys
import json
import tarfile
import hashlib
import urllib.request

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"c:\Users\d\Documents\open-melayu"
CACHE_DIR = os.path.join(ROOT_DIR, "raw", "prpm_cache")
DATA_DIR = os.path.join(ROOT_DIR, "data")
CANDIDATE_FILE = os.path.join(DATA_DIR, "candidate_pool_15k.json")
STAGING_DIR = os.path.join(ROOT_DIR, ".audit-tmp", "shards_download")

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(STAGING_DIR, exist_ok=True)

WINDOWS_RESERVED = {
    'con', 'prn', 'aux', 'nul',
    'com1', 'com2', 'com3', 'com4', 'com5', 'com6', 'com7', 'com8', 'com9',
    'lpt1', 'lpt2', 'lpt3', 'lpt4', 'lpt5', 'lpt6', 'lpt7', 'lpt8', 'lpt9'
}

def get_expected_filename(word: str) -> str:
    w = word.strip().lower()
    if w in WINDOWS_RESERVED:
        return f"_{w}.json"
    return f"{w}.json"

def download_file(url: str, dest_path: str):
    print(f"[*] Downloading {url} -> {dest_path}")
    urllib.request.urlretrieve(url, dest_path)

def verify_sha256(file_path: str, expected_sha: str) -> bool:
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while chunk := f.read(65536):
            h.update(chunk)
    actual_sha = h.hexdigest().lower()
    return actual_sha == expected_sha.strip().lower()

def collect_from_ips(ip_list):
    if len(ip_list) != 5:
        print(f"[!] Warning: Expected 5 IPs, got {len(ip_list)}. Proceeding with provided IPs...")

    downloaded_shards = []
    for idx, ip in enumerate(ip_list, 1):
        ip = ip.strip()
        shard_num = idx
        tar_name = f"shard_{shard_num}.tar.gz"
        sha_name = f"shard_{shard_num}.sha256"
        
        tar_url = f"http://{ip}:8080/{tar_name}"
        sha_url = f"http://{ip}:8080/{sha_name}"
        
        local_tar = os.path.join(STAGING_DIR, tar_name)
        local_sha = os.path.join(STAGING_DIR, sha_name)
        
        try:
            download_file(sha_url, local_sha)
            with open(local_sha, 'r', encoding='utf-8') as sf:
                expected_sha = sf.read().split()[0]
                
            download_file(tar_url, local_tar)
            
            if verify_sha256(local_tar, expected_sha):
                print(f"[+] Shard {shard_num} checksum verified: {expected_sha}")
                downloaded_shards.append((shard_num, local_tar))
            else:
                print(f"[-] ERROR: Shard {shard_num} checksum mismatch! Skipping extract.")
        except Exception as e:
            print(f"[-] ERROR downloading Shard {shard_num} from {ip}: {e}")

    # Extract all verified shards into raw/prpm_cache
    print(f"\n[*] Extracting {len(downloaded_shards)} verified shards into {CACHE_DIR}...")
    for s_num, tar_path in downloaded_shards:
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=CACHE_DIR)
        print(f"[+] Extracted Shard {s_num}")

    # Final audit against 15,000 candidates
    audit_coverage()

def audit_coverage():
    if not os.path.exists(CANDIDATE_FILE):
        print("[-] Candidate file not found for audit.")
        return

    with open(CANDIDATE_FILE, 'r', encoding='utf-8') as f:
        candidates = json.load(f)

    total_candidates = len(candidates)
    cached_ok = 0
    missing = []
    error_entries = []

    for item in candidates:
        word = item['word']
        expected_file = get_expected_filename(word)
        full_path = os.path.join(CACHE_DIR, expected_file)
        
        if not os.path.exists(full_path):
            missing.append(word)
            continue
            
        try:
            with open(full_path, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
            if data.get('error'):
                error_entries.append((word, data['error']))
            else:
                cached_ok += 1
        except Exception as e:
            error_entries.append((word, str(e)))

    print("\n================== AUDIT REPORT ==================")
    print(f"Total Candidate Pool: {total_candidates}")
    print(f"Valid Cached Words:   {cached_ok} ({cached_ok/total_candidates*100:.1f}%)")
    print(f"Missing Files:        {len(missing)}")
    print(f"Error Entries:        {len(error_entries)}")
    print("==================================================")

    if missing or error_entries:
        gap_file = os.path.join(DATA_DIR, "crawler_gap_list.json")
        with open(gap_file, 'w', encoding='utf-8') as gf:
            json.dump({'missing': missing, 'errors': error_entries}, gf, ensure_ascii=False, indent=2)
        print(f"[!] Gap list saved to {gap_file} for gap filling.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        ips = sys.argv[1:]
        collect_from_ips(ips)
    else:
        print("Auditing existing cache...")
        audit_coverage()
