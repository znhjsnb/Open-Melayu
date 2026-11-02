# Codex CLI 任务指令：Open-Melayu 分布式爬虫与双轨生产架构【严苛技术审计】

你是本次工程的**主架构与门禁审查官 (Codex CLI)**。
当前工作区：`c:\Users\d\Documents\open-melayu`。

技术管家 (Antigravity) 与用户共同推演制定了一套关于【PRPM 官方数据分布式爬取与 Codex 20路并发双轨生产】的技术架构方案。
用户指示：**“定好后你得交给 codex 审核你的方案有无问题”**。

请你以极度严谨、实事求是、拒绝客套的技术标准，对该方案进行深度技术审计，并出具正式的审计报告 `docs/CODEX_PLAN_AUDIT_REPORT.md`。

---

## 审查材料与代码资产
1. 方案文档：`docs/PLAN_DISTRIBUTED_CRAWLER_AND_CODEX.md`
2. Cloud-Init 启动脚本源码：`src/vultr_cloud_init.sh`
3. 真实候选词表 Gist：`https://gist.githubusercontent.com/znhjsnb/2e0d74a6f08e5daaf46286230cf2653b/raw/9238ee3cd59b6e188cfb245eec77abd8c65e561e/candidate_words_15k.txt`
4. 本地环境约束：
   - 用户主力网络通过东京 Vultr VPS (`45.32.36.128`, Hysteria 2)；
   - 本地已有 PRPM 缓存：`raw/prpm_cache/`；
   - 目标产出：7 维词库 Schema，15,000 词。

---

## 核心审查维度（必须给出严谨论证与代码级排查）

### 1. 脚本可执行性与 Linux 兼容性审查 (`src/vultr_cloud_init.sh`)
- 在 Ubuntu 24.04 LTS (Noble Numbat) 环境下：
  - `apt-get install -y python3-bs4` 是否真实可用？会不会触发 PEP 668 (externally-managed-environment) 阻断？
  - `hostname` 提取逻辑 `echo "$HOSTNAME" | grep -o -E '[0-9]+'` 是否健壮？如果主机名是 `spider-1`、`spider-01` 或默认 `vultr-guest` 会发生什么？
  - 后台启动 Python HTTP 服务 `python3 -m http.server 8080` 是否存在安全或端口被 ufw 拦截的风险？
  - 脚本生成的 `shard_${SHARD_NUM}.tar.gz` 打包命令是否存在由于路径通配符导致的打包失败或缺少根目录文件？

### 2. 爬虫抗封禁与网络拓扑审查
- PRPM (`prpm.dbp.gov.my`) 网站特性：
  - 实测 TTFB 为 11.3 秒。单机 5 线程并发（每线程随机间隔 0.3~0.8s）对该站点的 IIS/ASP.NET 后端压力是否合理？是否会触发 503 Service Unavailable、429 Too Many Requests 或临时封锁？
  - 将爬虫流量完全剥离至 5 台独立 Vultr 新加坡/多地 VPS，是否彻底切断了与用户主力东京 IP `45.32.36.128` 的关联？对主力节点的保护是否 100% 成立？

### 3. 两边速率匹配与时间窗口论证
- 爬虫全集群吞吐量测算（5 台机 x 5 线程 = 25 线程）：
  - 测算完成 15,000 词的确切时间区间。
- Codex 下游编写速度测算（5 词微批次，20 线程并发）：
  - 测算 15,000 词的编写耗时与配额消耗。
  - 验证“爬虫是否必然大幅领先于 Codex 编写”，是否存在生产端空转等待爬虫数据的死锁或阻塞风险？

### 4. 极端异常与容错方案审查
- 如果 5 台机器中有 1 台由于机房故障宕机或卡住，剩余机器能否正常完成？未爬取的词如何快速识别并由本地或单机补漏？
- 本地 Windows 拉取 5 个 `shard_X.tar.gz` 时的解压与合并逻辑是否可靠？是否存在文件名大小写敏感冲突（Windows NTFS 不区分大小写，而 Linux ext4 区分大小写）？马来语词条是否存在纯大小写异形词？

---

## 交付产物
将审查结论、潜在致命缺陷（Bug / Risk）、优化修复建议以及最终门禁判定（APPROVED / CONDITIONAL APPROVED / REJECTED）严谨写入：
`docs/CODEX_PLAN_AUDIT_REPORT.md`。
