# Codex 任务指令：Antigravity 会话记录之【幻觉与事实严苛审计报告】

你是本次工程的**独立代码与事实审查官 (Codex CLI)**。
用户要求你对 **Antigravity（技术管家/调度中枢）在本会话中的所有发言、数据引用与方案推演进行全景事实核查与幻觉审查**。

## 一、 输入审查材料
1. 对话完整逐轮记录已提取至：`c:\Users\d\Documents\open-melayu\docs\CONVERSATION_FOR_AUDIT.md`。
2. 真实底层工程环境与文件系统：
   - 英文词典工作区：`c:\Users\d\Documents\dict`（含 `RULES.md`, `README.md`, `tests/`, `app/`, `data/`）；
   - 马来语工程工作区：`c:\Users\d\Documents\open-melayu`（含 `raw/`, `src/`, `docs/`）。

## 二、 审查维度与执行准则
请你编写 Python 脚本或直接通过真实测试/文件核查，逐项核对 Antigravity 在对话中提出的每一个关键断言：

1. **工程与状态断言审查 (Engineering & State Claims)**：
   - Antigravity 宣称：英文词典 Git 状态为 clean，分支为 `main`，最新提交为 `23308a0` 并已推送到远程。是否属实？
   - Antigravity 宣称：英文词典前端测试 `node --test tests/frontend.test.mjs tests/frontend.interactions.test.mjs` 为 57/57 项全部通过。请你在 `dict` 中实测，是否属实？
   - Antigravity 宣称：底盘资产为 25,006 词头、58,574 义项、27 个分片。是否属实？

2. **数据素材与统计断言审查 (Dataset & Statistics Claims)**：
   - Antigravity 宣称：下载了 `dbp_malay_words_v2.json`，包含 187,385 个词头。在 `raw/` 目录下实测是否准确？
   - Antigravity 宣称：`kaikki_malay.jsonl` 包含 15,515 个唯一词头、17,812 义项，自带 IPA、词源等。实测是否准确？
   - Antigravity 宣称：`opensubtitles_frequency_ms_full.txt` 包含 114,000+ 词频条目。实测是否准确？
   - Antigravity 宣称：Hugging Face 上的 `entries-ms.parquet` 与 `wordnet-ms.parquet` 分别为 1.45MB 和 1.07MB，10.5 万条语义节点。实测是否准确？

3. **语言学与领域常识断言审查 (Linguistic Facts & Domain Knowledge)**：
   - Antigravity 宣称：马来语采用 26 个拉丁字母（Rumi），拼读规则极其规则、所见即读，无声调。是否符合语言学事实？
   - Antigravity 宣称：马来语是典型黏着语（Agglutinative），核心是词根（Kata Dasar）+ 词缀（Imbuhan，如 ber-, meN-, peN-, -kan, -an, ke-...-an），约有 4,000~5,000 个核心原生词根，派生后约 1.2万~1.5万高频常用词覆盖 99.5% 真实语境。是否符合语言学事实与学术共识？
   - Antigravity 宣称：马来西亚真实口语（Bahasa Pasar）存在大量缩写（如 `tak=tidak`, `nak=hendak`, `kat=di`, `diorang=mereka`）。是否属实？

4. **竞品与生态断言审查 (Product Landscape & Pain Points)**：
   - Antigravity 宣称：市面上主流马华词典（如 eKamus）例句和发音需要付费/看广告解锁，UI 充斥广告，且缺乏前缀公式树、口语脱节。是否与实际用户痛点吻合？是否存在夸大？

5. **幻觉分级评定 (Classification of Statements)**：
   对 Antigravity 的各项陈述给出评级：
   - 【✅ 真实无误 (Factually Verified)】
   - 【⚠️ 存在轻微瑕疵/偏差 (Minor Inaccuracy)】
   - 【❌ 幻觉或严重捏造 (Hallucination)】

## 三、 交付物
请将严谨、公正、不留情面的评测报告写入：
`docs/ANTIGRAVITY_HALLUCINATION_AUDIT.md`。
