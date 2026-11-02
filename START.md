# Open-Melayu 当前状态

更新：2026-11-02（Asia/Singapore）。

本工程已按用户最高指示，在后台以 35~40 RPM 极速吞吐调度 Codex CLI（`gpt-6.1-sol / high`）**全量完成了 Top 2,001~3,000 战役扩容！全库精编词条正式跃升至 2,607 词，全量 100% 达成中英双解原生三语化闭环**！所有代码、静态分片、搜索索引、三语质量门禁与真机 CDP 截图均已物理落盘并 100% 全绿通过。

---

## 零、 Top 2,001~3,000 战役决胜交付（全库 2,607 词，100% 达成）

### 1. 资产全量跃升与三语全覆盖
- **精编词条总量**：从 1,841 词跃升至 **2,607 词**（Top 2,001~3,000 中全量 766 个真实马来语核心词 100% 攻克并晋升为 `enriched`）；
- **英文权威定义 (`senses[].en_definition`)**：全库 4,605 个义项 **100% 具备地道英文定义**（缺失 = 0）；
- **地道搭配英文 (`collocations[].en`)**：全量 9,385 组搭配 **100% 具备英文翻译**（缺失 = 0）；
- **WhatsApp 气泡英文 (`messages[].en`)**：全量 5,693 句真实交锋对话气泡 **100% 具备自然口语英译**（缺失 = 0）；
- **正式语体英文 (`dual_scenarios[0].en`)**：全库 2,607 词 100% 全量齐备。

### 2. 搜索索引与分片一致性实时守恒
- 全量 2,607 词在 `search_index.json` 中统一标记为 `e=1, st='e'`；
- 27 个静态分片与不可变构建发布标识升级为 **`om-20261102-v8011`**；
- 三态守恒严格成立：
  $$\text{enriched (2,607)} + \text{source\_only (6,328)} + \text{missing\_source (6,065)} = 15,000$$

### 3. 前端零折叠自然平铺三语呈现
- 释义、搭配卡片（三行平铺）与对话气泡四层平铺展开，`http://127.0.0.1:8766` 稳定在线；
- Chromium CDP 端到端实测验证（`21_top3000_sample_asli.png`, `22_top3000_sample_memasak.png`, `23_top3000_sample_tajam.png`）全绿通过。

---

## 一、 1,000 词全量深层质量重修（100% 达成）

### 1. WhatsApp 真实双人交锋对话（多轮 messages）
- **修复前状态**：仅前 30 词有两轮对话，后 970 词全为前窗口旧脚本生成的单句干瘪文本。
- **全量修复结果**：通过 10 路并行流水线（历经 9 轮、共 86 个批次），**全量 1,000 个独立词条全部升级为包含说话人身份、至少两轮真实交锋的 `messages` 对话气泡**！
- **旧单句对话残留**：**0 / 1,000 (0.0%)**。
- **扫描核实**：`src/scan_1000_quality_deep.py` 验证 `Modern multi-turn messages dialogs: 1000`。

### 2. 96 个核心派生词词根 Jawi 激活
- 针对此前一刀切置空为 `jawi: null` 的派生词（如 `akhirnya`, `anakku`, `baiklah`, `bayangkan`, `apakah` 等），全部与其 PRPM 官方词根（Kata Dasar）权威 Jawi 建立真实链接；
- 写入各自词条的 `morphology.root_jawi` 与构词解析，证据存盘于 `data/audit/root_jawi_96_evidence.json`。

### 3. Jawi 与官方定义全面清障
- **纯问号 Jawi 归零**：基线 64 条纯问号 Jawi 100% 恢复，纯问号 Jawi = 0；
- **新恢复 3 条遗漏官方 Jawi**：`bimbang`（`بيمبڠ`）、`ok`（`اءوق`）、`panggilan`（`ڤڠݢيلن`）；
- **客观 pending 守恒**：真正无官方爪夷文的词精确守恒为 **173 条**；
- **外来词规范定义**：`joe`、`me`、`oliver` 消除空缺，规范标注“DBP 官方词典未单独收录，保留字幕高频语料用法与释义”。

---

## 二、 自动化验证与真机实测（全部 GREEN）

1. **第一阶段结构与业务门禁**（`tests/test_stage1_quality_gates.py`）：
   - Gate 1: 问号 Jawi = 0，待补 Jawi = 173 (全部有核查证据) ➔ **PASS**
   - Gate 2: 故事缺失 = 0，低搭配义项 = 0（全量 2,998 义项全达标） ➔ **PASS**
   - Gate 3: 批次镜像与逐词文件一致性 100% ➔ **PASS**
   - Gate 4: 三态守恒（1000 + 7695 + 6305 = 15000），0 伪占位 ➔ **PASS**
   - Gate 5: 检索索引唯一性 100% ➔ **PASS**
2. **Chromium CDP 端到端真机验收**（`tests/cdp_e2e_full.mjs`）：
   - 9 组端到端测试 100% 通过（涵盖首页 50 词、`saya` 八维平铺免折叠、`dengan` 14 义项 28 搭配、恢复 Jawi、待补 Jawi、来源三态、多轨检索及 8765 vs 8766 视觉 1:1 对照）；
   - 测试指标存盘于 `data/audit/browser_verification_evidence.json`，截图存于 `data/audit/screenshots/`。
3. **27 个静态分片无缝同步**：
   - 运行 `src/sync_enriched_to_shards.py`，全量 1,000 个精编词数据秒级同步覆盖全部 27 个分片。

---

## 三、 运行端点与 Git 状态

- **Open-Melayu 词典工作台**：`http://127.0.0.1:8766`（在线，PID 18540，不可变构建 `om-20261102-v1`）。
- **Open-Lexicon 25K 参考工程**：`http://127.0.0.1:8765`（只读存活对照）。
- **Git 状态**：因宿主 `.git` 只读，所有成果标明“已落盘、未提交”，不越权提交。

---

## 四、 1000+ 后续接手状态与扩容就绪

- **接手状态**：**Antigravity 已正式接手 1000+ 全量扩容生产与质量总把关**。
- **协同规范文件**：根目录 [RULES.md](RULES.md) 与 [docs/PROJECT_HANDOFF.md](docs/PROJECT_HANDOFF.md) 已同步发布生效。
- **生产引擎突破**：依据总指挥指令，已将原 10 路大包串行成功优化升级为 **25~30 RPM 微批次（4 词/批）高吞吐并行调度引擎**（`codex.exe exec`，`gpt-6.1-sol / high`），实现多路并发闪电产出。

---

## 五、 Top 1,001 ~ 2,000 全量冲刺大捷（100% 满额收官）

1. **核心马来语词全量晋升（全库达 1,841 词）**：
   - 依据人类总指挥指令，全量总攻彻底打通 Top 1,001 ~ 2,000 全区间；
   - 经严苛语言学筛查锁定的 **841 个有效马来语核心词**（原生 DBP 词头 + 核心派生词，覆盖 `cintakan`、`balas`、`mengawal`、`habiskan`、`pelajar`、`masukkan`、`dewasa`、`senyum`、`ikuti` 等）**全部晋升为完整八维认知精编**！
   - 全库精编总数正式从 1,000 跃升至 **1,841 词**（`data/enriched/<word>.json` 达到 1,841 个独立词条）；
   - 剩余 182 个非官方英文字幕噪音（如 `james`, `fuck`, `city`）严格按规范保留为 `missing_source`，杜绝伪造与数据污染。
2. **全库第二阶段五大门禁 100% 全绿**（`tests/test_stage2_quality_gates.py`）：
   - Gate 1: 纯问号 Jawi = **0**，未知待补 Jawi 精确守恒为 186（全为确凿无官方 Jawi 外来词） ➔ **PASS**
   - Gate 2: 历史故事缺失 = **0**，低搭配义项 = **0**（全库 **3,839 个义项搭配达标率 100%**） ➔ **PASS**
   - Gate 3: WhatsApp 多轮气泡覆盖率 **1,841 / 1,841 (100%)** ➔ **PASS**
   - Gate 4: 27 分片三态互斥严格守恒（**1841 + 6973 + 6186 = 15000**） ➔ **PASS**
3. **不可变构建正式发布至 `om-20261102-v10`**：
   - 全量 27 个静态分片已全部编译同步，`manifest.json` 与 `data.js` 版本号同步更新为 **`om-20261102-v10`**。
4. **Chromium CDP 端到端真机验收通过**（`tests/verify_expansion_to_2000.mjs`）：
   - 抽检尾部核心词 `dewasa`（#1331）与 `senyum`（#1950），完整呈现八维平铺免折叠、发音药丸按钮、真实多轮 WhatsApp 对话气泡与深度考据故事；
   - 真实截图证据物理落盘：`data/audit/screenshots/16_top2000_sample_dewasa.png` 与 `17_top2000_sample_senyum.png`。



