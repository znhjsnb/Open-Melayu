"""
Deployer for new spider-3 and spider-5 instances
"""
import time
import paramiko

NEW_NODES = [
    {"name": "spider-3", "ip": "139.180.191.198", "pass": "?5gBP!PVhLvmd$V4", "shard": 3},
    {"name": "spider-5", "ip": "45.76.147.100",   "pass": "B=x3nHiwJu,]N}JQ", "shard": 5},
]

from remote_cluster_manager import REMOTE_WORKER_CODE

def deploy_new_node(node):
    print(f"[*] Waiting for {node['name']} ({node['ip']}) SSH to become ready...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    connected = False
    for attempt in range(20):
        try:
            client.connect(node['ip'], port=22, username='root', password=node['pass'], timeout=5)
            connected = True
            break
        except Exception as e:
            time.sleep(5)
            
    if not connected:
        print(f"[-] Could not connect to {node['name']} after 100 seconds!")
        return False

    print(f"[+] Connected to {node['name']}! Setting up environment...")
    
    setup_cmd = """
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq && apt-get install -y -qq python3 python3-bs4 curl coreutils
    mkdir -p /root/open_melayu_crawler /root/prpm_cache /root/staging
    curl -sL "https://gist.githubusercontent.com/znhjsnb/2e0d74a6f08e5daaf46286230cf2653b/raw/9238ee3cd59b6e188cfb245eec77abd8c65e561e/candidate_words_15k.txt" -o /root/open_melayu_crawler/words.txt
    """
    stdin, stdout, stderr = client.exec_command(setup_cmd)
    stdout.channel.recv_exit_status()

    # Upload worker.py
    sftp = client.open_sftp()
    with sftp.file('/root/open_melayu_crawler/worker.py', 'w') as f:
        f.write(REMOTE_WORKER_CODE)
    sftp.close()

    # Setup systemd services
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
    
    stdin, stdout, stderr = client.exec_command("systemctl daemon-reload && systemctl enable --now spider-http && systemctl restart spider-crawler && sleep 2 && systemctl is-active spider-crawler")
    out = stdout.read().decode().strip()
    client.close()
    print(f"[+] {node['name']} (Shard {node['shard']}) service status: {out}!")
    return True

if __name__ == "__main__":
    for n in NEW_NODES:
        deploy_new_node(n)
