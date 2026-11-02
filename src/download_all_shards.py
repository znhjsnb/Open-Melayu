import paramiko
from pathlib import Path

dest_dir = Path(r"c:\Users\d\Documents\open-melayu\.audit-tmp")
dest_dir.mkdir(parents=True, exist_ok=True)

downloads = [
    {"ip": "139.180.130.187", "pass": "}e3QM(Z(q__Rpda{", "remote": "/root/prpm_cache/shard_1.tar.gz", "local": "shard_1.tar.gz"},
    {"ip": "139.180.219.108", "pass": "k%6My,LR(soz-s%d", "remote": "/root/shard1_p2_cache/shard_1.tar.gz", "local": "shard_1_p2.tar.gz"},
    {"ip": "198.13.58.126",   "pass": "Lz3)qA{rDUBato+n", "remote": "/root/shard1_p3_cache/shard_1.tar.gz", "local": "shard_1_p3.tar.gz"},
    {"ip": "45.32.46.237",   "pass": "s7+ZnR?cjSi9yuu+", "remote": "/root/prpm_cache/shard_5.tar.gz", "local": "shard_5.tar.gz"},
]

for d in downloads:
    local_path = dest_dir / d["local"]
    print(f"Downloading {d['remote']} from {d['ip']} -> {local_path}...")
    try:
        t = paramiko.Transport((d["ip"], 22))
        t.connect(username="root", password=d["pass"])
        sftp = paramiko.SFTPClient.from_transport(t)
        sftp.get(d["remote"], str(local_path))
        sftp.close()
        t.close()
        print(f"  [SUCCESS] {d['local']}: {local_path.stat().st_size / 1024:.1f} KB")
    except Exception as e:
        print(f"  [ERROR] {e}")
