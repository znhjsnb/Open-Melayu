# Open-Melayu 新窗口接管提示词

以下正文可直接用作新会话任务指令；八维 Schema 和详细验收统一引用 `docs/PROJECT_HANDOFF.md`，不复制第二份规范。

---

你接手 Open-Melayu 马来语认知词典，担任核心代码与内容编写者、事实审查者。工作目录固定：`C:\Users\d\Documents\open-melayu`。按已授权的 Codex CLI `gpt-6.1-sol / high` 请求配置工作，不擅自换模型、扩量或恢复 30 路生产，不调用付费外部 API。

本任务授权你完成下面三阶段修复、适配及验证。授权范围内持续推进，不反复问“是否继续”；只询问真正缺少的授权或影响结果的产品选择。先读文件再改，保留既有有效成果。

## 先建立事实基线

Windows PowerShell 读 Markdown 使用 `Get-Content -Encoding UTF8`。依次读取：

1. `C:/Users/d/.codex/skills/engineering-workflow/SKILL.md` 与 `C:/Users/d/.codex/USER_COLLABORATION_PROFILE.md`。
2. 本工程 `START.md`、`docs/PROJECT_HANDOFF.md`、`docs/CODEX_PHASE3_HALLUCINATION_AUDIT.md`；按需读 `data/audit/phase3_evidence.json`、三批来源说明、`docs/WORKBENCH_PLAN_AUDIT_REPORT.md` 的未关闭条件。
3. 参考工程 `C:\Users\d\Documents\dict\RULES.md` 的产品与审美部分及其 `app\static\` 源文件。

本工程当前没有根目录 RULES.md，不虚构已读，也不照搬英文工程权限、数据库或历史验收。检查 git status、实际分支与关键文件差异；当前宿主 .git 只读且本仓尚无提交，不能假定已有安全检查点。

已核实基线（2026-11-01 审计，2026-11-02 文档定向复核）：

- data/enriched/ 有 1,000 个独立词条 JSON，另有三个各 10 词的批次数组，共 1,003 文件。它们是半成品，不能称全部验收通过。
- 64 个非空 Jawi 为纯问号，其 PRPM 缓存均有非问号值可逐词核对恢复；另有 176 词缺 Jawi、225 词缺音节。Batch 1–3 的 30 词缺历史故事，127 义项未达两组搭配；joe、me、oliver 另有马来语定义来源缺口。问题集合不能直接相加。
- 15,000 词索引和 27 分片真实存在；索引 5,254,564 字节，约 5.01 MiB / 5.25 MB。历史三态为 1,000 enriched + 7,695 source_only + 6,305 missing_source，守恒成立；enriched 标志不等于新门禁通过。
- PRPM 14,977 缓存文件中，8,558 有任一词典定义字段、7,098 有 Jawi；Kaikki 8,168 个唯一词形有 IPA；另有 4,310 词根映射、3,374 口语规则、7,791 行 Tatoeba 例句。数量不等于全覆盖、全官方或无需筛选。
- 旧校验器会放过假 Jawi 与空嵌套对象；历史曾绕过门禁从 staging 补写。当前导出器误标缺来源占位为 DBP 定义，app.js 漏渲染搭配和历史故事。文档已纠正口径，生产问题待你实施修复。

## 统一八维，保留 JSON 兼容

按交接文档第 3 节 Schema 和业务门禁执行：

1. 基础标杆 `headword`：DBP 音节/Jawi、IPA、字幕词频位序，分别标来源。
2. 构词母体 `morphology`：Kata Dasar、现代构词公式、词族关系。
3. 权威释义 `senses`：实际官方原义、编辑改述、细微语境与使用边界。
4. 地道搭配 `collocations`：实际存于 **`senses[].collocations`**，每义项至少两组马来语—中文搭配。
5. 双境对抗 `dual_scenarios`：正式公文/新闻语体与 WhatsApp 口语气泡、标准语还原、翻译、省变音说明。
6. 口语速查 `spoken_shortcuts`：缩写、吞音、变音与限制，无可靠形式可空。
7. 社交礼仪 `cultural_pragmatics`：代词礼貌层级、皇室/正式/平辈边界；`sociolinguistic_register` 是兼容别名，两键并存须相等。
8. 深度认知 `etymology`：有依据的 `historical_story` 与明确区分史实的 `cognitive_memory_aid`。

八项教学功能由七个主容器承载，不按顶层键数计维，不拿别名凑一维。前端映射八项完整视图，不重复存一份顶层搭配。未知值保留 null 和原因，不编造；结构、来源完整度和编辑复核分别报告。

## 阶段一：数据清洗与门禁修复

1. 记录输入快照和问题清单，从 data/prpm_raw/ 逐词恢复 64 个纯问号 Jawi，核对词头及词位，显式 UTF-8 写入并保留变更/来源记录。不改原始缓存，不把词根拼写当派生词拼写；176 个未知 Jawi 另列 pending。
2. 按交接清单升级 Batch 1–3 的前 30 词：每义项补两组不同搭配、每词补有依据的词源历史故事，保留记忆口诀及既有来源限制；升级口语对话以至少两轮 messages 标明人物关系。同步逐词文件、三个批次数组和对应验证。词源未明就写清已知与未知，不造历史。
3. 修正 src/export_web_shards.py 的 missing_source 占位及官方误标，保留候选可检索性；同步索引、详情徽标、列表、复制/导出等所有文案。source_only 标明实际来源及核对状态，不一律冒充 Kamus Dewan。
4. 将归一化 Schema 与业务门禁接入生产/导出，检查逐义搭配、故事、乱码、别名冲突、返回词头集合、批次镜像及来源状态。失败不得直接从 staging 晋升入库，pending 不计成品。joe、me、oliver 不能用伪官方定义填满。
5. 修复“v1 manifest + data.js v2 + 原地覆盖”问题：一致输入快照、不可变版本资源、全部校验后最后切换 manifest、缓存同版、失败保留旧版。沿用现有 C01–C12 的有效条件，不擅换技术栈。

验收：64 条恢复有逐词证据，纯问号 Jawi 为 0；前 30 词搭配与故事缺项清零；缺来源词不再冒充官方；15,000 候选与 27 分片覆盖、ID、三态和构建版本一致。分类变化记录原因和新计数，不硬凑旧数字，其余未知与待核来源如实列出。

## 阶段二：老前端 1:1 移植与八维平铺渲染

只读源：`C:\Users\d\Documents\dict\app\static\`。
写入目标：`C:\Users\d\Documents\open-melayu\app\static\`。

以源 index.html、styles.css、app.js、worker.js、db.js 为成熟基准，1:1 对照布局、排版、配色、密度、主题、导航和交互。检查 data.js、sw.js、字体/图标依赖，适配马来语 Schema 与独立缓存命名空间；不接英文 SQLite，不照搬英语考试标签。

审美要求已定：

- **八维默认平铺展开，拒绝手风琴、默认折叠、“更多”或 Tab 隐藏核心内容。**
- 单词与例句采用带喇叭图标的高亮实体发音药丸按钮。
- 自然曲线 `cubic-bezier(0.16, 1, 0.3, 1)`，点击 `active:scale-[0.98]` 或等价 CSS；只对 transform/opacity 做动画，保持硬件加速及减少动效兼容。
- `/` 呼出聚焦，上下键切词，焦点/滚动连续，不劫持输入框和中文 IME。
- app.js 必须渲染全部八维，尤其 **每义项的 senses[].collocations 与 etymology.historical_story**。不能只改“7维”为“8维”徽标；Jawi 局部 RTL，未知字段简洁显示待补。

端口固定：Open-Melayu 为 `http://127.0.0.1:8766`，启动器 `C:\Users\d\Desktop\启动Open-Melayu词典工作台.bat`；Open-Lexicon 25K 保持 `http://127.0.0.1:8765`。不得改英文工程、停其进程或杀占端口的未知进程。需要服务操作先核身份；按实际加载机制验证页面刷新、Worker/IDB/SW 缓存和后台重载后的版本。

## 阶段三：端到端浏览器实测与 Git 原子提交

- 用隔离夹具与全量结构门禁覆盖假/问号 Jawi、少搭配、缺故事、别名冲突、词头集合不符、误标、发布中断与缓存混版。历史 python src/audit_phase3.py 是审计复现入口，不能代替新门禁或靠修改历史判定抹平缺陷。
- 真实浏览器打开 8766，与 8765 在相同尺寸、主题和缩放下视觉对照，记录截图、时间、浏览器及 build_id。验证八维无需展开即可读、气泡、搭配、故事、局部 RTL、发音、键盘、词头/中文/Jawi/词根/别名搜索、快速切词、深链、刷新与离线边界。
- 样本至少含 saya、dengan、bangunan、belajar、kelihatan、okay、tv，并从本次构建各取一个 source_only、missing_source。声音、性能或受限场景未测就记未测，不计通过；不得读取真实学习数据库。
- 每个独立修复闭环门禁通过后原子提交，只暂存明确路径，不用 git add . 收走全仓未跟踪资产。先核来源许可、工作区和本仓实际分支，不覆盖他人成果，不自动推送。若 .git 仍只读，继续可做的修复与验证，保留差异、结果与拟提交清单，报告“已落盘、未提交”，由已有权限的宿主提交；不绕过权限、不伪报 hash。
- 更新 START.md 与 docs/PROJECT_HANDOFF.md 的实际状态，简报已修数量、门禁、浏览器证据、剩余缺口和真实 commit hash 或提交限制。

## 禁止事项

严禁擅自改成手风琴或丑化成熟页面；严禁只显示七项却称八维完整；严禁把未通过质检的数据称零缺陷；严禁用编辑示例冒充真实新闻/私人聊天、用 Kaikki 或推测冒充 DBP 官方原文；严禁伪造词源、Jawi 或填充释义；严禁绕过门禁补成品；严禁凭网卡速度/进程数证明模型满载或无风控；严禁越界改参考工程、全局配置、其他服务、真实学习记录或触发付费接口。

开始时简短汇报已核实状态及正在推进的第一项修复，随后持续完成三阶段。只对有证据的结果宣告完成。
