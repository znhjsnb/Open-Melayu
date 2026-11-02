# Antigravity 会话事实与幻觉审查

审查日期：2026-11-01。依据：本工程 `docs/CONVERSATION_FOR_AUDIT.md`、`task_codex_hallucination_audit.md`、本地六文件实测、英文工程只读检查与一手在线资料。

**总体判断：英文工程的资产规模与 57 项测试结果可以复现；马来语素材介绍存在多处严重的统计单位混淆、官方性拔高与未获数据支持的覆盖承诺。** 这些错误会直接影响选词、成本估算与架构判断，不能以“约数”概括过去。但现有证据也不足以把所有陈述归为捏造，或判断发言者主观上故意造假。

## 1. 范围与评级原则

所给“完整逐轮记录”实际只包含 Step 0、10、11、159、183、184 的节选，中间大量步骤缺失。因此不能声称已审查 Antigravity 在所有轮次的每一段发言，也不能给“全会话幻觉率”。任务中列出的部分语言学/竞品断言在节选里没有原话，以下明确标为“任务转述”，不伪造它们的原始上下文。

- ✅ **已核实**：有本地计数、实际执行或直接支持该命题的一手来源。
- ⚠️ **口径/适用范围有偏差**：基础部分成立，但省略条件可能误导。
- ❌ **与证据矛盾/严重失实**：实际数据直接反证，或把没有的关键字段当作现成资产。
- **未能核实**：缺少原话、执行日志、当前远端状态或足够来源；它不等于“已证伪”。对“世界最顶级、全部、完全缺少”等无基准断言不授予已核实评级。

当前测量不能证明过去某个时点发生过什么；代码和文档也不能证明当时确实执行了某命令。技术结果、历史动作、产品评价分开判断。

## 2. 英文工程状态与测试

已读取 `C:/Users/d/Documents/dict/AGENTS.md`、`RULES.md`、`README.md` 与交接页相关状态。本轮没有修改该工程的代码、配置、数据库或 Git。

| 断言 | 证据与本次结果 | 评级 |
| --- | --- | --- |
| 当前分支 main，工作区 clean | `git --no-optional-locks status --short --branch` 仅返回 `## main...origin/main`，无工作区变更条目 | ✅ 当前可核实 |
| HEAD 为 23308a0 | 完整值 `23308a0e995d56926c81583b72ebab8739a41b59` | ✅ |
| main 与 origin/main 一致 | 当前本地 remote-tracking ref 与 HEAD 完整哈希相同 | ✅ 仅限本地跟踪引用 |
| 已推送且真实远端当前相同 | `git ls-remote origin refs/heads/main` 因宿主凭据/TLS 环境失败；网页读取也未获得提交证据。不能用本地 origin/main 证明实时远端 | 未能核实；不能评“捏造” |
| `node --test tests/frontend.test.mjs tests/frontend.interactions.test.mjs` 57/57 通过 | 默认命令本次因 `spawn EPERM` 失败；同一文件与数据在单进程模式 57/57 通过、0 跳过、0 失败，耗时约 2.78 秒 | ⚠️ 结果可复现，命令条件表述缺失 |
| 25,006 词头、58,574 义项、27 分片 | 独立读取 search_index 与全部 shard：index 25,006、分片 27、键数与唯一键数均 25,006、`senses` 总数 58,574；模块测试亦核对一致 | ✅ 数量；不证明每条语义正确 |
| 已完成浏览器视觉/所有交互验收 | 节选未直接这样说；现有交接页反而明确视觉验收未完成。Node 模块与 DOM 替身测试不证明真实浏览器渲染、焦点与语音都正确 | 不扩大原断言；若据 57 项宣称全端验收，则不成立 |

### 2.1 测试复现方式

原测试的 after hook 会写 `dict/.tmp/frontend-module-results.json`，而本轮权限只允许写 Open-Melayu。故先把英文工程 `app/static/` 和两个原测试复制到本工程 `.audit-tmp/dict-check/`，对 **39 个源文件逐一核对 SHA-256**，运行前后再核对源文件未变；未改写测试以绕过断言。

```powershell
python src/audit_conversation_claims.py
```

脚本先运行原命令并保留其失败记录，仅在出现 `EPERM` 时改用：

```powershell
node --test --experimental-test-isolation=none tests/frontend.test.mjs tests/frontend.interactions.test.mjs
```

Node 版本 v24.19.0。完整命令、退出码、测试输出、源文件哈希和资产计数保存在 `data/audit/conversation_checks.json`。这是源代码与数据一致的隔离副本复现，不谎称在原目录直接写报告并跑通默认命令；也不证明历史上的那次执行确实发生。

## 3. 马来语素材断言

下列以本地输入 SHA-256 锁定的结果为准；可用 `python src/benchmark_audit.py` 重现。完整统计、分母、CSV 和限制见 [素材审计报告](BENCHMARK_AUDIT_REPORT.md)。

| Step 183 或任务转述中的断言 | 实测与纠正 | 评级 |
| --- | --- | --- |
| DBP 文件 187,385 词头、2.47 MB | 有 187,385 个唯一原字符串、2,467,611 字节，按十进制约 2.47 MB；规范化后 187,384 键 | ✅ 数量；⚠️ “词头”未限定质量/单位 |
| 这是“DBP 官方权威词库”，涵盖全部标准词头、官方词性 | 来源是 `malaysia-ai` 社区 HF 仓库；本地 JSON 仅字符串，没有词性和来源字段。未找到官方授权发布依据，也未证明完整性 | ❌ “已含官方词性/全部覆盖”失实；官方授权身份未证实 |
| “DBP 只有马—马释义”描述当前这个文件 | 此文件根本没有释义，只是字符串数组。其他 DBP 字典网页有释义不能转嫁到这个文件 | ❌ |
| 字幕 full 有 114,000+ 条 | 实为 106,821 行，少于该下限 7,179 行；规范化 106,819 键 | ❌ 明确数字错误 |
| full 和 50k 是互补词频素材 | 50k 精确等于 full 前 50,000 行，不能相加当成独立样本 | 若据此相加则 ❌；记录未明确相加，不强加指控 |
| 字幕能“真实记录马来西亚街头与网络聊天当前热度”，对标 COCA/BNC | 源是 OpenSubtitles2018，经 FrequencyWords 输出；无地区、句级上下文、现代聊天样本或平衡采样证据。只能用作一类字幕频率 | ⚠️ 场景与代表性严重外推；不是同等基准 |
| Kaikki 有 15,515 唯一词头 | 15,619 个原拼写，规范化后 15,515；说明规范化口径后成立 | ⚠️ 统计口径遗漏 |
| Kaikki 有 17,812“细分义项” | 17,812 是记录行数，真实 `senses[]` 总数 22,460；记录可多义项 | ❌ 单位错误，少计 4,648 义项 |
| Kaikki 自带 IPA、音节、词源、原始英文定义 | 确有这些字段；按规范化词头，IPA 52.65%、音节 32.67%、词源文本 55.33%，不能理解为全部配齐 | ✅ 字段存在；⚠️ 完备性被放大 |
| `entries-ms.parquet` 和 `wordnet-ms.parquet` 都是 Wordnet 网络 | 前者是 17,485 行 Kaikki 简化表；后者才来自 Wordnet Bahasa | ❌ 资源类别混淆 |
| Parquet 文件约 1.45 MB 和 1.07 MB | 1,448,922 与 1,066,523 字节，十进制近似正确 | ✅ |
| 105,028 条“语义节点”，含上位词/上下级关联 | 105,028 是 lemma–synset 对应行；只有 36,911 个不同 synset。全部 `role=lemma`、全部 `word=value`，不存在关系、释义或例句行 | ❌ 计数单位与可用能力同时失实 |
| “普林斯顿 Wordnet Bahasa” | Wordnet Bahasa 以 Princeton WordNet 编号对齐，不等于 Princeton 官方编写的马来语词典。文件编号为 PWN 3.0 offset-POS | ⚠️ 项目归属混淆 |
| 2026 年 10 月最新抽取 | HF 卡片声明 2026-10-27/28 抽取；没有固定上游 OMW commit，本地文件也未与卡片修订作逐字节比对。“最新”不能独立证明 | ⚠️ 有发布者声明，缺快照链 |
| 词族在原资料里“孤立”、没有串联 | `belajar` 有 `ber- + ajar` 模板与 pembelajaran 派生链接；`mengajar` 有 meng-+ajar，其他词也有 derived/related 等。规范化词头有派生链接 2,578 个 | ❌ “全无关系”被反证；“未形成完整教学词族”才准确 |
| WordNet“只有英文解释” | 本地 Wordnet Parquet 没有解释列/解释行；英文 gloss 主要来自 Kaikki | ❌ 对本地资产失实 |
| `tak` 在频率前 10 | 排名 9，146,394 次 | ✅ |
| 口语词被传统词典略过，本批都无对应 | 本地 Kaikki 已收 tak、nak、diorang、xde、sbb；只有 dkt 在指定六词中未命中 Kaikki。不能以 DBP 镜像缺失代表所有传统词典 | ❌ 泛化；个别资料有缺口成立 |
| “全网完全缺少高质量中文精译” | 本地缺乏系统逐义项中文字段成立；eKamus 已公开声明有马华/华马与成语双语内容。没比较准确率不能判全网质量皆差 | 未证实的绝对化断言，应撤回 |
| “开源界最顶级”“彻底补齐所有盲区” | 无资源对比实验或验收定义；Top15k 两词典联合只命中 65.07% 词种，带例文仅 8.11%，不是成品全覆盖 | 未证实的宣传；若理解为已全补齐则 ❌ |
| 已启动某模型、后台自动唤醒 | 现有脚本/报告说明本轮任务确实在进行，但没有提交前那次派发的进程日志、模型元数据或自动唤醒证据 | 历史调度细节未能核实，不由结果倒推 |

HF 来源：[DBP 社区目录](https://huggingface.co/datasets/malaysia-ai/DBP/tree/main)、[Kaikki Parquet 固定卡片](https://huggingface.co/datasets/miserableface/kaikki-melayu-entries/blob/c8a4ca496502e76c5de947fdf8eb18e2966844c3/README.md)、[Wordnet Parquet 固定卡片](https://huggingface.co/datasets/miserableface/melayu-wordnet/blob/060b8b1b04493fc0191b62c3d2e95b8d1aaf7c49/README.md)。字幕来源与格式由 [FrequencyWords 维护者](https://github.com/hermitdave/FrequencyWords)说明。上游项目关系与编号见 [Wordnet Bahasa README](https://github.com/omwn/omw-data/blob/main/wns/msa/README)。

## 4. 语言学断言（任务转述，节选未给完整原话）

### 4.1 Rumi 26 字母、无声调、“所见即读”

Rumi 使用 26 个拉丁字母成立，但马来语也有 Jawi，不能据此删去 Jawi 需求。马来西亚向联合国提交的官方地名指南明确列出两种文字、26 字母，以及 e 对应不同元音。[官方指南](https://unstats.un.org/unsd/geoinfo/ungegn/docs/11th-uncsgn-docs/E_Conf.105_109_CRP.109_9_TG%20for%20Malaysia_annex..pdf)。

标准马来语通常按非声调语言描述，意为没有普通话式的词汇声调对立，不代表没有语调、韵律或地区差异。一项比较实验把马来语母语者列为非声调组，支持这个有限命题。[Intajamornrak 2017](https://digital.car.chula.ac.th/manusya/vol20/iss2/1/)。

“拼读相对规则”可作入门概括；“所见即读/无歧义”过度。DBP 明确列出同拼写、不同 e 读音与词义的 homograph，如 perang；不是看字母就能无条件决定读音。[DBP 同形词说明](https://dewanbahasa.jendeladbp.my/2024/03/18/12654/)。

评级：26 字母与标准语非声调 ✅；“所见即读”若作为严格规律 ⚠️。不能据此承诺由拼写自动生成的 IPA 100% 正确。

### 4.2 黏着语、4,000—5,000 根与 99.5% 覆盖

马来语有丰富黏着形态，尤其派生，研究亦同时讨论附缀、复合与重叠，不是只做根与前后缀的机械相加。[ACL 2011 原论文](https://aclanthology.org/P11-1130.pdf)、[Malay Lexicon Project 2 原研究摘要](https://pubmed.ncbi.nlm.nih.gov/35705853/)。这部分概括 ✅，不能据类型标签推出教学词汇总数。

本次未找到足以证明“4,000—5,000 个核心原生词根”是统一学术共识的口径。malaytextr 作者文档的 4,310 是词形→根映射行数，既不是不同根数，也不证明全部原生。另一方面，一项书面语研究分析了超过 6,400 个 simplex forms，进一步说明不同定义/语料会得到不同集合；simplex form 也不等同“核心原生根”。[malaytextr](https://github.com/zahiernasrudin/malaytextr)、[原研究](https://jpmm.um.edu.my/index.php/JML/article/view/3287)。评级：**未证实，不能包装为公认事实**。

“12,000—15,000 高频常用词覆盖 99.5% 真实语境”没有提供独立语料、token/type/lemma 单位、过滤方法或置信区间。本地字幕列表 Top12k 保留项频次占 **95.94%**，Top15k **96.77%**；这是保留词形的频次份额，更不能等同所有语境理解率。评级：**该数值未获来源支持，并被本地同类指标反证**。需要撤回无条件保证，而不是把目标 99.5% 换写成现状。

### 4.3 tak/nak/kat/diorang

口语简化与非正式形式确实存在。DBP 的答复支持 tak/tidak、nak/hendak 的对话用法及其正式书写限制；Malaya 规则记录 diorang/mereka 等映射。[DBP](https://kndbp.dbp.gov.my/soalanlazim/nb_soalan_lazim.aspx?ctl00_contentPlaceHolder_dgCarianBaruChangePage=21)、[Malaya 内嵌规则](https://github.com/malaysia-ai/malaya/blob/master/malaya/text/rules.py)。有限命题 ✅。

但 `kat=di` 是特定用法下的说明，不能全局替换；`dkt` 可能展开为 dekat。Bahasa Pasar、地区方言、标准口语、网络省字和语码转换也不是同一个标签。把所有非正式形式统称“不标准马来语”，或一律归为拼写错误，都会误导学习者。评级：⚠️ 场景与分类需补充。

## 5. 竞品与生态（任务转述，未取得手机实机）

eKamus 的开发者商店页确实标注“包含广告、应用内购”。这支持其有广告与内购模式，不能单独证明页面“充斥广告”或每个例句/每次发音都必须付费/看广告。[eKamus 官方商店页](https://play.google.com/store/apps/details?hl=zh&id=info.ekamus.android)。

同一开发者说明明确列出：离线马华/华马字典、kata dasar 显示、双语成语谚语、部分词条例句、同反义词、发音与语法资料。这些是发布者的功能声明，本次未安装 App 验证质量，但足以阻止在未测之前把它描述为“完全没有词根、例句、发音或成语”。该页面没有证明它已有完整可校验的词缀公式树，也不能证明它一定没有。

评级：

- 广告/内购存在 ✅（商店声明）。
- 广告密度、免费额度、具体功能解锁条件、交互干扰程度：**未能核实**，需记录具体版本、平台、账户、免费/付费状态和复现步骤。
- “完全缺词根显示/成语/例句/发音”：若曾作此绝对断言则 ❌；任务给出的“缺乏前缀公式树”尚未证实，不能扩大成“没有词根”。
- “主流马华词典普遍都这样”：没有多产品样本与统一检查表，**未证实的生态泛化**。

本审查没有用个别用户评价来替代实机测试，也没有为查付费条件而注册账户或购买内容。

## 6. 建议采用的更正表述

> 当前有一份社区托管的 DBP 名称词表、2018 字幕词频、English Wiktionary 经 Kaikki 提取的马来语词条，以及 Wordnet Bahasa 的词语—概念对应表。它们分别提供候选词形、字幕排序、部分发音/释义/构词信息与概念归属，覆盖和许可链仍不完整。已测得字幕全表 106,821 行，Kaikki 17,812 记录/22,460 义项，Wordnet 105,028 对应行/36,911 概念编号。下一步的价值是补齐并审校三语逐义项解释、现代构词和场景例句，尚不能承诺 99.5% 真实语境覆盖或整体优于所有竞品。

报告发布后应修正素材说明中的原错误，不把本报告中的架构建议再次宣传成“已实现”或“100% 语义无误”。应保留真实命令、快照、分母与未核实状态；不因用户要求“严苛”就把证据不足改判为恶意捏造。
