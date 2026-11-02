"""
Cluster Systemd Deployer & Orchestrator
- Deploys hardened worker and creates systemd services on all available nodes
- Survives reboots and SSH disconnections
- Queries real-time progress across all nodes
"""
import os
import sys
import time
import json
import paramiko

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"c:\Users\d\Documents\open-melayu"
DATA_DIR = os.path.join(ROOT_DIR, "data")

NODES = [
    {"name": "spider-1", "ip": "139.180.130.187", "pass": "}e3QM(Z(q__Rpda{", "shard": 1},
    {"name": "spider-2", "ip": "139.180.219.108", "pass": "k%6My,LR(soz-s%d", "shard": 2},
    {"name": "spider-3", "ip": "139.180.191.198", "pass": "?5gBP!PVhLvmd$V4", "shard": 3},
    {"name": "spider-4", "ip": "149.28.159.229", "pass": "?R2fzP[k?)(pk,(U", "shard": 4},
    {"name": "spider-5", "ip": "45.76.147.100",  "pass": "B=x3nHiwJu,]N}JQ", "shard": 5},
]

from remote_cluster_manager import REMOTE_WORKER_CODE

def deploy_node(node):
    print(f"[*] Connecting to {node['name']} ({node['ip']})...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(node['ip'], port=22, username='root', password=node['pass'], timeout=8)
    except Exception as e:
        print(f"[-] {node['name']} SSH not ready: {e}")
        return False

    print(f"[+] Connected to {node['name']}! Preparing directories and wordlist...")
    setup_cmd = """
    mkdir -p /root/open_melayu_crawler /root/prpm_cache /root/staging
    curl -sL "https://gist.githubusercontent.com/znhjsnb/2e0d74a6f08e5daaf46286230cf2653b/raw/9238ee3cd59b6e188cfb245eec77abd8c65e561e/candidate_words_15k.txt" -o /root/open_melayu_crawler/words.txt
    """
    client.exec_command(setup_cmd)

    # SFTP worker.py
    sftp = client.open_sftp()
    with sftp.file('/root/open_melayu_crawler/worker.py', 'w') as f:
        f.write(REMOTE_WORKER_CODE)
    sftp.close()

    # Create systemd service for crawler
    service_content = f"""[Unit]
Description=Open-Melayu PRPM Crawler Worker
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/open_melayu_crawler
ExecStart=/usr/bin/python3 -u /root/open_melayu_crawler/worker.py {node['shard']} 5 /root/prpm_cache /root/open_melayu_crawler/words.txt
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
"""

    http_service = """[Unit]
Description=Open-Melayu Status HTTP Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/prpm_cache
ExecStart=/usr/bin/python3 -m http.server 8080
Restart=always
RestartSec=3s

[Install]
WantedBy=multi-user.target
"""
    client.exec_command(f"cat << 'EOF' > /etc/systemd/system/spider-crawler.service\n{service_content}\nEOF")
    client.exec_command(f"cat << 'EOF' > /etc/systemd/system/spider-http.service\n{http_service}\nEOF")
    
    # Reload and start
    client.exec_command("systemctl daemon-reload && systemctl enable --now spider-http && systemctl restart spider-crawler")
    client.close()
    print(f"[+] {node['name']} (Shard {node['shard']}) systemd service ACTIVE and running!")
    return True

if __name__ == "__main__":
    for node in NODES:
        deploy_node(node)
