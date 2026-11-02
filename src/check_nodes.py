import paramiko

nodes = [
    {'name': 'spider-1', 'ip': '139.180.130.187', 'pass': '}e3QM(Z(q__Rpda{', 'task': 'Shard 1 (0-1000)', 'dir': '/root/prpm_cache'},
    {'name': 'spider-2', 'ip': '139.180.219.108', 'pass': 'k%6My,LR(soz-s%d', 'task': 'Shard 2 (3000-6000) [DONE]', 'dir': '/root/prpm_cache'},
    {'name': 'spider-2 (offload)', 'ip': '139.180.219.108', 'pass': 'k%6My,LR(soz-s%d', 'task': 'Shard 1 Part 2 (1000-2000)', 'dir': '/root/shard1_p2_cache'},
    {'name': 'spider-3', 'ip': '198.13.58.126',   'pass': 'Lz3)qA{rDUBato+n', 'task': 'Shard 3 (6000-9000) [DONE]', 'dir': '/root/prpm_cache'},
    {'name': 'spider-3 (offload)', 'ip': '198.13.58.126',   'pass': 'Lz3)qA{rDUBato+n', 'task': 'Shard 1 Part 3 (2000-3000)', 'dir': '/root/shard1_p3_cache'},
    {'name': 'spider-4', 'ip': '149.28.159.229', 'pass': '?R2fzP[k?)(pk,(U', 'task': 'Shard 4 (9000-12000) [DONE]', 'dir': '/root/prpm_cache'},
    {'name': 'spider-5', 'ip': '45.32.46.237',   'pass': 's7+ZnR?cjSi9yuu+', 'task': 'Shard 5 (12000-15000)', 'dir': '/root/prpm_cache'},
]

print("================== CLUSTER LIVE ORCHESTRATION STATUS ==================")
for n in nodes:
    try:
        c = paramiko.SSHClient()
        c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        c.connect(n['ip'], port=22, username='root', password=n['pass'], timeout=5)
        
        cmd = f"""
        echo "COUNT: $(ls -1 {n['dir']}/*.json 2>/dev/null | wc -l)"
        echo "STATUS_FILE: $(tail -n 2 {n['dir']}/status.txt 2>/dev/null)"
        echo "TARBALL: $(ls -lh {n['dir']}/*.tar.gz 2>/dev/null)"
        """
        stdin, stdout, stderr = c.exec_command(cmd)
        output = stdout.read().decode('utf-8', errors='ignore').strip().split('\n')
        
        count = 0
        status_text = ""
        tarball_text = ""
        for line in output:
            line = line.strip()
            if line.startswith("COUNT:"):
                cnt_str = line.split(":", 1)[1].strip()
                count = int(cnt_str) if cnt_str.isdigit() else 0
            elif line.startswith("STATUS_FILE:"):
                status_text = line.split(":", 1)[1].strip()
            elif line.startswith("TARBALL:"):
                tarball_text = line.split(":", 1)[1].strip()
                
        print(f"[{n['name']} | IP: {n['ip']}]")
        print(f"  Role: {n['task']} | Valid JSON: {count}")
        if tarball_text:
            print(f"  Package: {tarball_text}")
        if status_text:
            print(f"  Status: {status_text}")
        c.close()
    except Exception as e:
        print(f"[{n['name']}] Connection Error: {e}")

print("========================================================================")
