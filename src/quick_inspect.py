import paramiko

nodes = [
    {'name': 'spider-1', 'ip': '139.180.130.187', 'pass': '}e3QM(Z(q__Rpda{', 'shard': 1},
    {'name': 'spider-2', 'ip': '139.180.219.108', 'pass': 'k%6My,LR(soz-s%d', 'shard': 2},
    {'name': 'spider-4', 'ip': '149.28.159.229', 'pass': '?R2fzP[k?)(pk,(U', 'shard': 4},
]

for n in nodes:
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(n['ip'], port=22, username='root', password=n['pass'], timeout=6)
        cmd = """
        echo "=== TARBALLS ==="
        ls -lh /root/prpm_cache/*.tar.gz /root/staging/*.tar.gz 2>/dev/null
        echo "=== JSON COUNT ==="
        ls -1 /root/prpm_cache/*.json 2>/dev/null | wc -l
        echo "=== STATUS ==="
        tail -n 2 /root/prpm_cache/status.txt 2>/dev/null
        """
        stdin, stdout, stderr = c.exec_command(cmd)
        print(f"[{n['name']} (Shard {n['shard']})]")
        print(stdout.read().decode('utf-8', errors='ignore'))
        c.close()
    except Exception as e:
        print(f"[{n['name']}] Error: {e}")
