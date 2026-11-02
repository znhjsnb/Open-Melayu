import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('139.180.130.187', port=22, username='root', password='}e3QM(Z(q__Rpda{', timeout=5)

cmd = """
echo "=== STATUS ==="
cat /root/prpm_cache/status.txt 2>/dev/null
echo "=== CACHED COUNT ==="
ls -1 /root/prpm_cache/*.json 2>/dev/null | wc -l
echo "=== FAILED ENTRIES ==="
cat /root/prpm_cache/failed_words.txt 2>/dev/null | tail -n 15
echo "=== SYSTEMD STATUS ==="
systemctl status spider-crawler --no-pager
"""
stdin, stdout, stderr = c.exec_command(cmd)
print(stdout.read().decode())
c.close()
