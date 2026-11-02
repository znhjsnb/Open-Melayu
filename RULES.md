# Open-Melayu 词典工程总则与协同规范 (RULES.md)

更新日期：2026-11-02（Asia/Singapore）。
适用范围：`C:\Users\d\Documents\open-melayu` 及其所有构建、生产与质检任务。

---

## 一、 人机协同格局与职责边界 (Zero Human-Relay Rule)

```mermaid
graph TD
    User["人类总指挥 (User / 产品负责人)"] --> Antigravity["Antigravity (技术总工 / 架构把关 / 人话翻译 / 流水线调度)"]
    Antigravity -.后台调用 codex.exe exec (gpt-6.1-sol / high).-> CodexEngine["Codex CLI 生产引擎 (八维内容生成)"]
    Antigravity -.结构门禁 & 严格先验.-> QualityGate["八维严苛质检门禁 (5大门禁 + CDP 真机实测)"]
    QualityGate -.秒级静态编译.-> Shards["27 Alphabetical Shards & Web Shell (8766)"]
```

1. **人类总指挥 (User)**：系统总调度与产品战略决策者。
2. **Antigravity (本座)**：
   - 负责技术总架构、底层环境运维、服务健康监控、质量门禁把关；
   - **人话翻译官**：把所有复杂的底层报错、模型天书堆栈挡在幕后，用大白话向人类总指挥汇报；
   - **流水线总调度**：在后台自动调度 `codex.exe exec` 驱动 `gpt-6.1-sol / high` 执行批量生产，**严禁让用户在多窗口间充当人肉传话筒**！
3. **Codex CLI 生产引擎**：
   - 主力模型配置锁定为 **`gpt-6.1-sol` 且 `reasoning_effort = "high"`**；
   - 严禁擅自更换未经授权的模型，严禁恢复旧有的粗暴无门禁 30 路盲跑，0 调用付费外部 API。

---

## 二、 八维教学功能与 Schema 契约

Open-Melayu 是面向严肃马来语学习者的认知词典，必须完整交付八维教学价值（由 7 个主容器规范承载，搭配存于 senses 内部）：

1. **基础标杆 (`headword`)**：词头、官方正字法音节划分、IPA（严谨宽式标音）、频次位序、带声波高亮实体发音药丸按钮；未取得官方资料者保留 `null` 并标明待补，严禁用纯问号或假字符填充。
2. **构词母体 (`morphology`)**：Kata Dasar（核心词根）、现代代数构词公式（如 `meN- + baca → membaca`）、词根芯片秒切、派生词芯片网格；**高频派生词必须显式关联词根（Kata Dasar）的权威爪夷文（`morphology.root_jawi`）**。
3. **权威释义 (`senses`)**：DBP 官方《Kamus Dewan》或《Kamus Pelajar》原文、中文精准定义、使用边界与语境辨析；外来词若官方未独立收录，必须透明注明“官方词典未单独收录，保留字幕高频语料用法”。
4. **地道搭配 (`collocations`)**：存储于 **`senses[].collocations`**，**每个义项必须提供至少 2 组**地道实用的双语搭配，并附带实体发音按钮。
5. **双境对抗 (`dual_scenarios`)**：
   - 正式公文/新闻语体（Berita / Dokumen）与 WhatsApp 街头口语（Bahasa Pasar）并列对照；
   - **WhatsApp 口语场景必须包含至少两轮真实交锋的 `messages` 气泡**（标明说话人身份与社会关系，如 `Farhan (同事)`、`Aiman (朋友)`），提供自然口语缩略、标准语规范还原与变音特征标签。
6. **口语速查 (`spoken_shortcuts`)**：常见吞音、缩写（如 `tak` ➔ `tidak`、`xde` ➔ `tidak ada`）及使用禁忌。
7. **社交礼仪 (`cultural_pragmatics`)**：代词礼貌层级、皇室/正式/平辈社交边界，防范称谓冒犯；`sociolinguistic_register` 是其兼容别名，两键并存须深度相等。
8. **深度认知 (`etymology`)**：严谨考据的历史演变叙事（`historical_story`，不穿凿附会）与明确区分于史实的脑图记忆口诀（`cognitive_memory_aid`）。

---

## 三、 产品与前端审美红线（严格继承 mature 设计系统）

- **默认全平铺自然滚动展开，坚决拒绝手风琴折叠**：严禁采用 `<details>`、Tab 分页、“查看更多”或折叠面板隐藏八维核心内容。
- **发音按钮实体化**：采用带小喇叭图标的高亮实体药丸按钮，声波波纹动画绑定音频状态，支持 Web Speech API 及无声降级。
- **自然物理动效**：动效锁定 `cubic-bezier(0.16, 1, 0.3, 1)`，点击按压触发 `active:scale-[0.98]`，仅对 `transform` 与 `opacity` 进行动画，尊重减少动效偏好。
- **全键盘极速流**：`/` 快速聚焦搜索框，上下方向键顺畅切词，滚动与焦点连续，绝不劫持输入框与中文 IME 输入法。
- **双语排版与文字方向**：爪夷文（Jawi）采用局部 `dir="rtl"`，绝不整体翻转网页；阿拉伯字符必须清洗尾部控制符（如 `\x81`）。

---

## 四、 1000+ 扩容生产与质量门禁规范

1. **并发策略：10 路受控并行（打包大吞吐）**：
   - 严禁粗暴的单词无脑高并发；
   - 统一采用 **“10 路线程并行，每路打包 10 词（每轮吞吐 100 词）”** 架构；
   - 严格守住本地代理网关的 **15 RPM 速率保护线**，彻底杜绝上游限流截断与 429 报错。
2. **原子发布与三态守恒**：
   - 每次扩写完成后，动态维护 15,000 候选词的三态互斥守恒：
     $$\text{enriched} + \text{source\_only} + \text{missing\_source} = 15,000$$
   - 校验通过后，使用 `src/sync_enriched_to_shards.py` 秒级更新 27 个静态分片，最后原子切换 `manifest.json` 与 `data.js` 版本号。
3. **出厂必检的五大自动化门禁**：
   - 门禁 1：纯问号 Jawi 必须为 0，未知待补 Jawi 必须有可查验依据；
   - 门禁 2：全量义项搭配达标率 100%（每义项 $\ge 2$ 组不同搭配），故事覆盖率 100%；
   - 门禁 3：全量词条 WhatsApp 口语对抗必须为 $\ge 2$ 轮带说话人的 `messages` 结构；
   - 门禁 4：无虚假 DBP 定义及徽标，无隐藏不可见控制字符；
   - 门禁 5：通过 Chromium CDP 无头浏览器真机端到端全量实测与截图落盘。
