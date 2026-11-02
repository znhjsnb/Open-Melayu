import time
import paramiko

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect('139.180.130.187', port=22, username='root', password='}e3QM(Z(q__Rpda{', timeout=8)

# 1. Update timeout from 16 to 30
c.exec_command("sed -i 's/timeout=16/timeout=30/g' /root/open_melayu_crawler/worker.py")

# 2. Restart systemd service
c.exec_command("systemctl daemon-reload && systemctl enable --now spider-crawler && systemctl restart spider-crawler")
time.sleep(3)

# 3. Check status
stdin, stdout, stderr = c.exec_command("systemctl status spider-crawler --no-pager")
print(stdout.read().decode())
c.close()
