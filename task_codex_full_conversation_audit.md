# Codex CLI 任务指令：Antigravity 全会话注意力涣散、事实准确性与幻觉深度审计报告

你是本次 Open-Melayu 工程的**首席独立审计与门禁审查官 (Codex CLI)**。
当前工作区：`c:\Users\d\Documents\open-melayu`。

用户发出明确质询：**“我不是还让你开一个对话审查吗？用于审计事实准确性等，你出现了注意力涣散问题”**。

请你针对全会话（共 988 个 Step，完整逐轮实录已提取至 `docs/FULL_CONVERSATION_FOR_AUDIT.md`），以最严苛、不留情面、用真实测试与历史日志说话的原则，出具正式的深度审计报告：
`docs/FULL_CONVERSATION_HALLUCINATION_AUDIT.md`。

---

## 核心审查维度（必须给出证据定位与判级）

### 一、 注意力涣散与目标漂移诊断 (Attention Drift & Goal Misalignment)
审查 Antigravity 在对话中的决策链路，重点分析为何出现注意力涣散与用户意图脱节：
1. **爬虫与双轨架构忽视**：
   - 用户早自第 670 轮起多次明确指示：“我希望后台一路一直爬，另一路来处理做词典”、“网络爬取需要我提供vps之类的吗”、“你要不要套皮vps乱序发起爬取”。
   - 为什么 Antigravity 在后续轮次中注意力涣散，依然沉溺于单线程编写 Batch 1、Batch 2，而没有及时建立稳固的双轨架构和速率基准？
2. **主力 IP 暴露与网络安全迟钝**：
   - 用户的开发环境通过 Vultr 东京 VPS (`45.32.36.128`, Hysteria 2) 翻墙。
   - Antigravity 所写的 `src/prpm_continuous_crawler.py` 实际上由于本地 TUN 路由和脚本超时回退机制，流量完全打在用户的东京主力 IP 上。
   - 为什么 Antigravity 没有主动监测出口 IP？为何轻率向用户断言“不需要 VPS，直接爬很安全”？这是认知短板还是对网络层盲目乐观导致的严重失察？

### 二、 事实准确性与幻觉断言排查 (Factual Accuracy & Hallucination Checks)
逐条核对并评定 Antigravity 在对话中提出的关键断言：
1. **速率断言**：
   - Antigravity 曾宣称：“PRPM 爬虫单线程每秒 1 词，每小时可爬 3,600 词，远超 Codex 编写速度，无需 VPS 代理”。
   - **事实核查**：真实测试 PRPM TTFB 高达 11.3 秒，加上直连 7 秒超时 Bug，单线程实际仅有 196 词/小时，被 Codex 20 线程编写速度（1,000 词/小时）彻底碾压。这项断言属于【严重失实/盲目估计】还是【数据推导幻觉】？
2. **数据资产断言**：
   - `candidate_pool_15k.json` 真实词数与结构；
   - 本地 `raw/prpm_cache/` 真实缓存数量与有效字段提取率；
   - Kaikki Wiktionary 与 DBP 真实交集与覆盖率。
3. **网络拓扑与代理断言**：
   - 本机 `curl https://api.ipify.org` 真实出口 IP 是否确为 `45.32.36.128`；
   - Vultr 新加坡机房在国内三大运营商网络下的真实路由表现（是否存在严重绕路）。

### 三、 评级与复盘改善标准
- 将各项问题明确归类为：
  - 【✅ 真实无误 (Factually Verified)】
  - 【⚠️ 存在轻微瑕疵/口径偏差 (Minor Inaccuracy)】
  - 【❌ 盲目推测/严重失实/注意力涣散 (Hallucination / Drift)】
- 明确指出 Antigravity 的行为模式缺陷，并给出不可逾越的工程整改准则。

---

## 交付产物
将详尽、严谨、客观的审计报告写入：
`docs/FULL_CONVERSATION_HALLUCINATION_AUDIT.md`。
