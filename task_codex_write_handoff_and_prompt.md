# Codex 任务指令：编写权威《项目交接文档》与《新窗口接管提示词》

你是本次 Open-Melayu 词典项目的**独立核心审查与代码创作者 (Codex CLI, gpt-6.1-sol / high)**。
用户在审查 Antigravity 的汇报后指出：“8维度怎么只有7个？要不你让codex写一版handoff和prompt？”

请你亲自操刀，基于你在 `docs/CODEX_PHASE3_HALLUCINATION_AUDIT.md` 中核实的所有底层真实数据、工程代码与参考工程，编写以下两份权威交付文档：

---

## 一、 核心任务要求

### 1. 彻底澄清并规范化【8 维认知数据结构体系】
解决此前 7 维 vs 8 维的口径混乱，明确 8 维度的严格划分与 JSON Schema：
- 维度 1（基础标杆）：`headword`（官方 DBP 音节、爪夷文 Jawi、IPA、词频位序）
- 维度 2（构词母体）：`morphology`（Kata Dasar 词根、代数构词公式、形态词族树）
- 维度 3（权威释义）：`senses`（Kamus Dewan 官方释义、细微语境辨析与用法界限）
- 维度 4（地道搭配）：`collocations`（每义项至少 2 组地道实用双语搭配）
- 维度 5（双境对抗）：`dual_scenarios`（正式公文/新闻 vs WhatsApp 真实口语对抗气泡对话）
- 维度 6（口语速查）：`spoken_shortcuts`（Bahasa Pasar 口语真实缩写、吞音、变音速查表）
- 维度 7（社交礼仪）：`cultural_pragmatics`（Kata Ganti Nama 人称代词礼貌层级、皇室/正式/平辈社交红线）
- 维度 8（深度认知）：`etymology`（跨语系演变历史叙事、借词溯源与脑图记忆口诀）

同时规定如何向下兼容现有的 JSON 字段（例如 `collocations` 位于 `senses[].collocations`，`sociolinguistic_register` 与 `cultural_pragmatics` 互为映射别名）。

---

### 2. 重写交付物一：`docs/PROJECT_HANDOFF.md`
根据审计报告中的事实，全面修正原交接文档的漏洞与夸大，作为后续所有工程接手的唯一事实基准：
- **工程资产真实现状**：
  - 1,000 个独立 JSON 文件真实存在于 `data/enriched/`，但当前处于“半成品”状态（存在 64 个纯问号 Jawi、前 30 词缺少搭配与故事）；
  - 15,000 词 Web 检索索引与 27 个分片已构建（5.01 MiB / 5.25 MB），守恒验证成立；
  - 物理素材实际覆盖率客观说明（PRPM 8,558 词有释义、7,098 词有 Jawi；Kaikki 8,168 词有 IPA；4,310 词根库；3,374 口语规则；7,791 Tatoeba 例句）；
- **第一步必须执行的数据清障操作（Actionable Fixes）**：
  - 修复 64 个纯问号 Jawi（从 `data/prpm_raw/` 还原）；
  - 升级前 30 词（Batch 1~3）补全搭配与词源历史故事；
  - 修正 `export_web_shards.py` 中的 `missing_source` 占位标签；
- **老成熟前端 1:1 严格复刻指引**：
  - 源工程路径：`c:\Users\d\Documents\dict\app\static\`（`index.html`, `styles.css`, `app.js`, `worker.js`, `db.js`）；
  - 目标工程路径：`c:\Users\d\Documents\open-melayu\app\static\`；
  - 严格遵守 `c:\Users\d\Documents\dict\RULES.md` 的产品与审美红线：
    - **默认平铺展开，坚决拒绝手风琴折叠（核心学习审美）**；
    - 实体化发音药丸按钮；
    - Emil Kowalski 自然弹簧动效（`cubic-bezier(0.16, 1, 0.3, 1)`、`active:scale-[0.98]`、硬件加速）；
    - 全键盘流无缝支持（`/` 呼出聚焦、上下键切词）；
    - 前端 `app.js` 必须完整渲染上述全部 8 维度，不得遗漏搭配与词源故事；
- **端口与隔离规范**：
  - Open-Melayu 锁定端口 `8766`（启动脚本：`C:\Users\d\Desktop\启动Open-Melayu词典工作台.bat`）；
  - Open-Lexicon 25K 锁定端口 `8765`，互不干扰。

---

### 3. 重写交付物二：`docs/PROMPT_FOR_NEW_WINDOW.md`
编写供人类总指挥直接复制粘贴到全新会话窗口的【接手指挥提示词】：
- 语气干练、无废话、直击要害；
- 包含清晰的上下文定位（项目背景、当前状态、参考源路径、端口要求）；
- 包含阶段化任务拆解（阶段一：数据清洗与门禁修复；阶段二：老前端 1:1 移植与 8 维度平铺渲染；阶段三：端到端浏览器实测与 Git 原子提交）；
- 明确禁止事项（严禁擅自改动审美变成手风琴、严禁自作主张丑化页面、严禁把未通过质检的数据宣称为零缺陷）。

---

## 二、 执行与交付
1. 将重写后的权威交接文档写入：`docs/PROJECT_HANDOFF.md`；
2. 将完整的新窗口提示词写入：`docs/PROMPT_FOR_NEW_WINDOW.md`；
3. 输出简洁的摘要，汇报文档编写完成。
