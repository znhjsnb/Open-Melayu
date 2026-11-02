"""
Offload Shard 1 work to completed nodes (spider-2 and spider-3)
- Spider-2 handles words 1000..2000
- Spider-3 handles words 2000..3000
- Spider-1 continues 0..1000
"""
import paramiko
import time

nodes_to_offload = [
    {
        'name': 'spider-2',
        'ip': '139.180.219.108',
        'pass': 'k%6My,LR(soz-s%d',
        'start_line': 1001,
        'end_line': 2000,
        'cache_dir': '/root/shard1_p2_cache',
        'words_file': '/root/open_melayu_crawler/words_p2.txt',
        'service_name': 'spider-shard1-p2',
    },
    {
        'name': 'spider-3',
        'ip': '198.13.58.126',
        'pass': 'Lz3)qA{rDUBato+n',
        'start_line': 2001,
        'end_line': 3000,
        'cache_dir': '/root/shard1_p3_cache',
        'words_file': '/root/open_melayu_crawler/words_p3.txt',
        'service_name': 'spider-shard1-p3',
    }
]

for node in nodes_to_offload:
    print(f"[*] Offloading to {node['name']} ({node['ip']})...")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(node['ip'], port=22, username='root', password=node['pass'], timeout=8)
    
    cmd_setup = f"""
    mkdir -p {node['cache_dir']}
    sed -n '{node['start_line']},{node['end_line']}p' /root/open_melayu_crawler/words.txt > {node['words_file']}
    wc -l {node['words_file']}
    """
    stdin, stdout, stderr = c.exec_command(cmd_setup)
    lines_count = stdout.read().decode().strip()
    print(f"    Words extracted: {lines_count}")
    
    service_content = f"""[Unit]
Description=Open-Melayu Shard 1 Offload
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/open_melayu_crawler
ExecStart=/usr/bin/python3 -u /root/open_melayu_crawler/worker.py 1 1 {node['cache_dir']} {node['words_file']}
Restart=on-failure
RestartSec=3s

[Install]
WantedBy=multi-user.target
"""
    c.exec_command(f"cat << 'EOF' > /etc/systemd/system/{node['service_name']}.service\n{service_content}\nEOF")
    c.exec_command(f"systemctl daemon-reload && systemctl restart {node['service_name']}")
    time.sleep(2)
    stdin, stdout, stderr = c.exec_command(f"systemctl is-active {node['service_name']}")
    status = stdout.read().decode().strip()
    print(f"[+] {node['name']} offload service status: {status}!")
    c.close()

print("[+] All offload services successfully started!")
