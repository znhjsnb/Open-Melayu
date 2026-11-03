# Open-Melayu 当前状态

更新：2026-11-03（Asia/Singapore）。

本工程已完成 **15,000 词级马-中-英三语认知词典（Open-Melayu 15K）** 的生产与收官对齐！15,000 个候选词中，**14,748 词（98.32%）** 已完成八维认知精编并晋升为 `enriched`，`source_only` 全部清零归 0，剩余 **252 个（1.68%）** 残缺/外来未考证词条严格遵守 Gate 4 零伪造原则保留为 `missing_source`。全部 14,748 个精编词条 100% 达成中英双解三语字段覆盖、七主容器八维结构契约（含 `spoken_shortcuts: []` 与全量非空 `pos`）、与候选池/搜索索引 1:1 严格一致的 15,000 唯一位序 ID，以及三阶来源诚实分级（`official` 7,479 词 / `root_derived` 2,328 词 / `corpus_usage` 4,941 词，且 `official` 内部严格区分 `DBP 原文:` 直接引文与 `马来语释义 (基于 DBP 官方词条):` 编辑编写释义）。

---

## 零、 全库 15,000 候选池收官账本（14,748 Enriched + 0 Source Only + 252 Missing Source = 15,000）

### 1. 资产全量统计与三语覆盖（针对 14,748 个精编词）
- **精编词条总量**：**14,748 词**（`data/enriched/<word>.json` 共 14,748 个独立词条对象，无 legacy `batch_*.json` 重复镜像，禁用控制/格式字符 `U+0081/U+00AD/U+200B/U+200C/U+200E` 与空串 Jawi 全部归 0，纯问号 Jawi = 0）；
- **八维七容器结构契约**：14,748 词 100% 具备完整七主容器（含规范数组 `spoken_shortcuts`），全库 **28,017 个义项** 100% 具备非空词性 `pos` 与 $\ge 2$ 组不同搭配；
- **英文权威定义 (`senses[].en_definition`)**：全库 **28,017 个义项** 100% 具备英文定义（缺失 = 0）；
- **地道搭配英文 (`collocations[].en`)**：全量 **56,933 组搭配** 100% 具备英文翻译（缺失 = 0，低搭配义项 = 0）；
- **WhatsApp 气泡英文 (`messages[].en`)**：全量 **29,981 句对话气泡** 100% 具备口语英译（缺失 = 0，单轮对话 = 0）；
- **正式语体英文 (`dual_scenarios[0].en`)**：全库 14,748 词 100% 全量齐备。

### 2. 三阶来源诚实性（Gate 4 Provenance）与三态/ID 守恒
- **三阶来源精确分级**（基于本地 `data/prpm_raw/*.json` 物理证据，已移除旧白名单入口）：
  - `official`（**7,479 词**）：PRPM 具备直接马来语 DBP 词条（Kamus Dewan / Kamus Pelajar）；前端严格判断 `head.status === 'official' && s.ms_is_verbatim === true`，满足归一化连续子串匹配（清洗控制字符、合并空白并转小写）的 1,814 个义项展示 `DBP 原文:`，其余 12,505 个编辑归纳释义义项展示 `马来语释义 (基于 DBP 官方词条):`；
  - `root_derived`（**2,328 词**）：具备马来语词缀构词标记且词根具备直接马来语 DBP 词条，前端展示 `马来语释义 (基于 DBP 词根推导):`；
  - `corpus_usage`（**4,941 词**）：官方马来语词典未单独收录或仅见于英马词典/字幕高频借词与专名，前端展示 `马来语释义 (字幕高频语料用法):`。
- **搜索索引、27 分片与候选池位序 ID 一致性守恒**：
  - 全量 14,748 词在 `search_index.json` 中统一标记为 `e=1, st='e'`，候选池、精编文件、27 个分片与搜索索引的 15,000 个词形及位序 ID（1~15,000）100% 逐词一致；
  - 27 个静态分片与不可变构建发布标识升级为 **`om-20261103-v9756`**；
  - 三态守恒严格成立：
    $$\text{enriched (14,748)} + \text{source\_only (0)} + \text{missing\_source (252)} = 15,000$$

### 3. 自动化测试与 Chromium CDP 代表词真机验收
- `python -B -m pytest -p no:cacheprovider tests/test_stage3_trilingual_quality_gates.py -v`：**7 passed (returncode = 0)**；
- `node tests/verify_trilingual_e2e.mjs`：对 8 个代表词（覆盖 `official`、`root_derived`、`corpus_usage`、`missing_source` 四态）执行词头、三语字段、逐义项搭配数与来源标签硬断言，**returncode = 0**。

---

> **以下第一至第五节为早期阶段性历史里程碑记录（1,000 词 / 1,841 词阶段快照），保留备查；当前最新状态以第零节为准。**

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

- **Open-Melayu 词典工作台**：`http://127.0.0.1:8766`（在线，不可变构建 **`om-20261103-v9756`**）。
- **Open-Lexicon 25K 参考工程**：`http://127.0.0.1:8765`（只读存活对照）。
- **Git 状态**：全量 14,748 个精编词条、27 个静态分片、搜索索引、测试套件与审计报告均已提交至 `master` 分支，工作区洁净。

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



