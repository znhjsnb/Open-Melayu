# Open-Melayu 15K 独立终审复核报告

审计日期：2026-11-03（Asia/Singapore）  
有效全量核验开始时间：09:22:41（UTC+08:00）  
审计目标提交：`3268a293`  
实际 HEAD：`ce5a63341bacacebf667ebaf6ba9f78a3d9dc90b`  
审计构建：`om-20261103-v8488`  
审计方式：本地只读检查、统一 Python 脚本全量核验、原始 pytest 测试执行、来源与浏览器测试代码定向复核。

## 一、终审总体裁定

**三态守恒、三阶来源标签数量、指定字符清洗、隔离清单对齐及指定三语字段覆盖均通过；pytest 7 项实际通过。不能签署“此前 8 项问题全部关闭、五大门禁全部通过”。**

本次发现三个新增的分片 ID 错配，以及仍未关闭的来源标注、旧白名单入口、八维结构契约和浏览器验收问题。

| 审计项目 | 裁定 | 实测依据 |
|---|---|---|
| 15,000 词三态守恒 | **PASS** | `14,748 + 0 + 252 = 15,000` |
| 候选池、分片、索引词形及状态集合一致 | **PASS** | 三方均覆盖相同的 15,000 个词形，状态逐词一致 |
| 分片、索引及候选位序 ID 一致 | **FAIL** | `head`、`hung`、`stand` 三词错配 |
| 三阶来源标签数量与基础缓存证据检查 | **PASS** | `7,479 / 2,328 / 4,941`，相应直接词条或词根字段检查通过 |
| Gate 1：指定 Jawi 与四类字符清洗 | **PASS** | 纯问号、空串及指定四类字符均为 0 |
| Gate 2：故事与逐义搭配结构 | **PASS** | 故事全覆盖；28,017 个义项均有至少两组不同搭配 |
| Gate 3：WhatsApp 多轮角色化对话 | **PASS** | 14,748 词全覆盖，共 29,981 条完整消息 |
| Gate 4：来源诚实性完整验收 | **FAIL** | 编辑改述仍显示为“DBP 原文”；旧入口仍保留白名单放行 |
| Gate 5：全量 Chromium CDP 验收 | **未通过验收** | 现有脚本只覆盖 8 个样词，本轮未执行浏览器重跑 |
| 指定马—中—英字段覆盖 | **PASS** | 释义、搭配、正式场景、消息的三语字段缺失均为 0 |
| 八维完整结构契约 | **FAIL** | 7 词缺词性；10,641 个逐词文件未提供规范的口语速查数组 |
| pytest | **PASS** | pytest 9.2.0，7 passed，返回码 0 |
| 当前构建 Git 归档及工作区洁净 | **PASS** | 审计前后 `git status --short` 均为空 |

本表五大门禁沿用 `RULES.md` 的定义。测试文件内部的 Gate 编号另有排列，不能直接互换。

**最终签字结论：批准本报告明确列出的统计与结构检查结果；暂不批准“全库八维、来源诚实性及全量端到端全部验收通过”的整体收官签字。**

## 二、核验方法与快照边界

统一 Python 脚本读取了全部 14,748 个精编文件、14,977 个 PRPM 缓存文件、27 个分片、候选池、搜索索引、manifest 与隔离报告，并完成集合、状态、字段、来源及 ID 对账。

pytest 在同一进程中运行，执行原始测试文件的全部七项测试。已经读取的数据由内存快照提供，复用了 **83,581 次数据读取及 5 次目录枚举**，没有修改测试断言。

只读沙箱下，首次执行在 pytest 默认输出捕获创建临时文件时失败。改用 `-s` 后重新执行统一脚本并完成核验。因此，本轮实际发生了一次额外全量读取，未完全达到严格的单趟目标；最终 pytest 执行没有再重复读取全库磁盘文件。

审计未修改词条、分片、测试或项目文档，未执行生产和发布脚本。

`ce5a6334` 相对 `3268a293` 仅新增 `src/run_final_codex_signoff.py`，本报告核验的词条、分片、索引和测试内容与目标提交一致。审计结束时 HEAD、工作区洁净状态和 manifest 指纹保持不变。

## 三、15,000 词三态守恒与分片／索引一致性

### 3.1 三方状态账本

| 状态 | manifest | 分片实测 | 搜索索引实测 |
|---|---:|---:|---:|
| `enriched`／`st='e'` | 14,748 | 14,748 | 14,748 |
| `source_only`／`st='s'` | 0 | 0 | 0 |
| `missing_source`／`st='m'` | 252 | 252 | 252 |
| **合计** | **15,000** | **15,000** | **15,000** |

```text
14,748 enriched + 0 source_only + 252 missing_source = 15,000
```

精编覆盖率为 **98.32%**，隔离占比为 **1.68%**。不能将候选池覆盖 15,000 词表述为全部 15,000 词已完成精编。

其他检查结果：

| 检查项 | 结果 |
|---|---:|
| 独立精编 JSON 文件 | 14,748 |
| `batch_*.json` 历史镜像 | 0 |
| 候选池记录数／唯一词形数 | 15,000／15,000 |
| 索引记录数／唯一词形数 | 15,000／15,000 |
| 索引唯一 ID 数 | 15,000 |
| 分片数／唯一词形数 | 27／15,000 |
| 分片唯一 ID 数 | **14,997** |
| 跨分片重复词形 | 0 |
| 候选池、索引、分片词形集合差异 | 0 |
| 逐词状态及精编标记不一致 | 0 |
| `data.js` 与 manifest 构建标识 | 一致 |

### 3.2 三个实际 ID 错配

最后救回的三词已经进入精编库，但其精编文件中的 `frequency_rank` 被用于生成错误的分片 ID。

| 词形 | 候选池 rank | 搜索索引 ID | 精编 frequency_rank／分片 ID | 裁定 |
|---|---:|---:|---:|---|
| `head` | 6,740 | 6,740 | 1,689 | **FAIL** |
| `hung` | 6,183 | 6,183 | 10,079 | **FAIL** |
| `stand` | 11,421 | 11,421 | 1,732 | **FAIL** |

因此，**词形与状态对齐通过，完整 ID 一致性不通过**。现有 pytest 的索引测试仅检查总量，未发现这三处差异。

除口语速查缺省值问题外，本次比较的其他教学主字段在逐词文件与对应分片之间一致。口语速查的 10,641 处差异来自逐词文件未提供规范数组，而同步器在分片中补入 `[]`。

## 四、三阶来源诚实分级复核

### 4.1 数量与基础证据

| 标签 | 实测词数 | 本次确认的证据 |
|---|---:|---|
| `official` | **7,479** | 对应本地 PRPM 缓存具备非空马来语 DBP 定义字段 |
| `root_derived` | **2,328** | 标注词根不同于原词，且词根缓存具备非空马来语 DBP 定义字段 |
| `corpus_usage` | **4,941** | 当前未标作具有直接官方定义 |
| **合计** | **14,748** | 与精编总数一致 |

未发现 `official` 缺少上述基础缓存证据，或 `root_derived` 缺少上述词根缓存证据。2,328 个派生标签的基本构词标记检查通过；存在本地词根映射时，未发现与其标注词根冲突。

这些结果证明的是**字段与缓存关系**，不能独立证明全部构词关系、义项和引文均已完成语言学核实。

### 4.2 专名误配及原白名单十词

| 核验对象 | 实测结果 | 裁定 |
|---|---|---|
| `meera`、`milan`、`jedi` | 均为 `corpus_usage`，`headword.jawi=null`、`morphology.root_jawi=null` | **PASS** |
| `head`、`hung`、`stand` | 均为 `enriched`、`corpus_usage`，两类 Jawi 均为 null | **PASS**，另有前述 ID 错配 |
| 原白名单十词 | 全部已降为 `corpus_usage` | 当前数据 **PASS** |

原白名单十词为：

```text
bagai, butir, dikerjakan, drpd, edisi,
kamus, lazimnya, masing, massa, spt
```

将缺少本地证据的词保守标为 `corpus_usage`，不意味着否认这些词在真实马来语中的存在。

### 4.3 Gate 4 尚未关闭的原因

**第一，拥有官方词条与展示文本属于官方原文，仍未分开判断。**

前端 `app/static/app.js:531` 根据整词 `headword.status` 决定是否显示“DBP 原文”，没有检查当前义项文本是否为实际引文。

可直接复核的反例：

| 词形 | 本地缓存原文 | 当前 `ms_definition` | 当前标签 |
|---|---|---|---|
| `aa` | `kep Asia-Afrika.` | `Kependekan bagi Asia-Afrika.` | `DBP 原文:` |
| `ab` | `kep anggaran belanja.` | `Kependekan bagi anggaran belanja.` | `DBP 原文:` |

展开缩写可以用于教学，但应标作编辑展开或改述，不能直接称为原文。

本次对 **14,319 个 official 义项**进行清理指定字符、归一空白后的连续子串诊断，**12,401 个未直接匹配缓存文本**。该数字是待核查线索，**不是已证实的 12,401 条错误**；标点、来源署名和节选方式也会影响匹配。上述 `aa`、`ab` 已足以证明现有标签规则仍会混淆改述与引文。

**第二，旧白名单写入入口仍然存在。**

`src/run_overnight_closure_and_audit.py` 仍保留：

- 第 48 行开始的 `CORE_MALAY_WITHOUT_PRPM_FILE` 集合；
- 第 337—344 行将白名单成员或具有词根来源者直接设为 `official`；
- 第 471 行主流程实际调用该来源重写函数。

所以只能确认**新修复脚本绕过了旧白名单、当前数据已纠正**，不能确认“白名单已彻底移除”。重新运行旧入口仍可能覆盖现有三阶标签。

此外，新脚本的派生分类仍参考 `is_root`、词缀字段以及中文说明中的关键词排除规则。词根缓存存在可以验证，但不等于派生关系本身已经获得独立物理证据。

## 五、此前八项阻塞问题销账表

以下逐项对应上一版报告第八节。

| 序号 | 上轮问题 | 本次复核 | 销账状态 |
|---:|---|---|---|
| 1 | 专名错误词根触发官方标记 | `meera`、`milan`、`jedi` 的标签和 Jawi 已纠正；全库引文标签仍有问题 | 指定三词 **已关闭**；来源门禁未整体关闭 |
| 2 | 十词仅凭白名单获得 official | 十词当前均为 `corpus_usage`；旧生产入口仍保留白名单放行 | **部分关闭** |
| 3 | 残留 `U+0081` | 逐词内容及对应发布字段清洗检查为 0 | **已关闭** |
| 4 | 27 个 Jawi 空字符串 | 两类 Jawi 空串均为 0，纯问号均为 0 | **已关闭** |
| 5 | pytest 返回码 1 | pytest 9.2.0 实际执行，7 passed，返回码 0 | **已关闭** |
| 6 | CDP 覆盖不足、失败断言不足 | 已增加四状态硬断言并修复强制成功退出；仍只测 8 词，缺少目标词头断言 | **部分关闭** |
| 7 | Type B 将 255 全称 missing_source | 当前清单恰为 252，与分片集合相等，每词 reason 非空 | **已关闭** |
| 8 | 状态页过时、终态未归档 | 两文档顶部已更新，数据已提交，工作区干净；旧状态和过度验收声明仍需修订 | 数据归档 **已关闭**；文档结论部分关闭 |

不能将上述结果记为“8 项全部销账”。

## 六、八维教学与三语覆盖

### 6.1 八维检查

| 维度 | 本次结构实测 | 裁定 |
|---|---|---|
| 基础标杆 `headword` | 14,748 词均有词头；未知读音及 Jawi 保留 null；三词位序错误 | **部分通过** |
| 构词母体 `morphology` | 14,748 词均有非空公式和说明 | 结构 **PASS** |
| 释义 `senses` | 28,017 个义项三语定义齐全；7 词缺词性 | **部分通过** |
| 地道搭配 | 56,933 组；全部义项至少两组不同搭配 | 结构 **PASS** |
| 双境对抗 | 14,748 词均有正式及口语场景，多轮消息齐全 | 结构 **PASS** |
| 口语速查 `spoken_shortcuts` | 4,107 个逐词文件提供数组；10,641 个未提供规范数组 | 契约 **FAIL** |
| 社交礼仪 | 14,748 词具备相关对象和非空礼貌说明；并存别名未见冲突 | 结构 **PASS** |
| 深度认知 | 14,748 词均有历史故事及记忆口诀 | 结构 **PASS** |

缺少非空 `pos` 的七词为：

```text
erso, iebih, mae, pappi, rio, thats, tien
```

其中 `thats` 涉及两个义项，合计 **8 个义项**缺词性。

口语速查没有可靠内容时允许使用空数组；这与缺少规范容器不同。分片同步器补入 `[]`，不能据此声称原始逐词文件全部满足七容器契约。

结构通过也不构成全部词源叙事、翻译、构词或口语自然度已通过语言学认证。

### 6.2 指定三语字段覆盖

| 内容 | 总数 | 马来语非空 | 中文非空 | 英文非空 |
|---|---:|---:|---:|---:|
| 义项定义 | 28,017 | 28,017 | 28,017 | 28,017 |
| 搭配 | 56,933 | 56,933 | 56,933 | 56,933 |
| 正式场景 | 14,748 | 14,748 | 14,748 | 14,748 |
| WhatsApp 消息 | 29,981 | 29,981 | 29,981 | 29,981 |

全部 29,981 条消息同时具有非空 `speaker`、`ms_spoken` 和 `ms_standard`。全部精编词的口语场景均达到至少两条消息、至少两个不同说话人标识。

**指定三语字段覆盖率为 100%。该结论适用于 14,748 个精编词，不包括 252 个隔离词。**

### 6.3 Jawi 与字符清洗

| 检查项 | 实测 |
|---|---:|
| `headword.jawi` 空串 | 0 |
| `morphology.root_jawi` 空串 | 0 |
| 两类 Jawi 纯问号占位 | 0 |
| `U+0081` | 0 |
| `U+00AD` | 0 |
| `U+200B` | 0 |
| `U+200E` | 0 |
| `headword.jawi=null` | 5,696 |
| `morphology.root_jawi=null` | 6,168 |

扩大到 Unicode 控制／格式字符类别检查时，另见 **30 个 `U+200C`**。它不属于本次指定的四类禁用字符，且可能具有文字连接用途，本报告不据此认定污染；但不能将“四类字符为 0”扩大表述为“所有格式字符均为 0”。

未知 Jawi 保留 null 的做法通过指定检查；本报告未签署所有 null 字段均已完成独立逐词来源认证。

## 七、252 个 missing_source 隔离词审计清单

### 7.1 清单完整性

以 `data/audit/quarantine_triage_report.json` 的 `type_b_missing_source_words` 为逐词依据：

| 检查项 | 结果 |
|---|---:|
| 清单词数 | 252 |
| 分片 missing_source 数 | 252 |
| 两集合是否完全相等 | **是** |
| 空白 reason | 0 |
| 清单 final_data_state 错误 | 0 |
| 构建标识 | `om-20261103-v8488` |

当前 `reason` 是生产失败或结构门禁记录，不能将其直接当作人名、噪音或无效马来语的语言学裁决。

| 原始失败原因类别 | 数量 |
|---|---:|
| 缺少构词公式 | 202 |
| 缺少 senses | 31 |
| 义项搭配不足两组 | 13 |
| 词头不匹配 | 2 |
| timeout | 3 |
| `NoneType` 迭代异常 | 1 |
| **合计** | **252** |

原始隔离记录为 285 条，其中 33 条已救回精编，剩余 252 条；本轮累计 `salvaged_count=52` 还包括此前未入队候选，二者统计范围不同。

### 7.2 全部分片分布及隔离词形

下表列出全部 252 词；各词精确 `reason` 保留在上述 JSON 对应词形键下。所有分片的 `source_only` 均为 0。

| 分片 | enriched | missing_source | 隔离词形 |
|---|---:|---:|---|
| a | 608 | 9 | `aey`, `alby`, `amara`, `amaya`, `aod`, `aslng`, `atcu`, `auw`, `ava` |
| b | 1,428 | 19 | `bao`, `barillo`, `barr`, `bart`, `beium`, `beom`, `beriaku`, `bette`, `bhi`, `biia`, `blandon`, `blart`, `blu`, `boieh`, `bozer`, `bratt`, `britt`, `bruner`, `burt` |
| c | 504 | 11 | `candie`, `carlo`, `cdo`, `cecause`, `chaani`, `chffffff`, `chuta`, `cj`, `cobb`, `cora`, `corben` |
| d | 981 | 14 | `daiam`, `daxam`, `del`, `dexter`, `dhani`, `dibby`, `dihadapan`, `donny`, `doo`, `drac`, `drago`, `dre`, `dudiey`, `duen` |
| e | 219 | 4 | `eema`, `eiling`, `eni`, `evey` |
| f | 227 | 7 | `feng`, `ffffff`, `fiiem`, `fiti`, `fitzie`, `flass`, `foon` |
| g | 418 | 18 | `gabe`, `galt`, `ganga`, `gaura`, `geet`, `geon`, `ghantt`, `gina`, `godrivecrazily`, `goin`, `goken`, `golde`, `goten`, `gotya`, `guardia`, `guddu`, `gunter`, `gushin` |
| h | 457 | 11 | `hachi`, `haule`, `heo`, `homer`, `hu`, `huaguo`, `huai`, `huo`, `hwa`, `hyo`, `hyun` |
| i | 220 | 8 | `iagi`, `iakukan`, `iike`, `il`, `imlay`, `ishu`, `ivo`, `iz` |
| j | 358 | 9 | `jaikant`, `jc`, `jhilmil`, `jian`, `jiro`, `joo`, `ju`, `juan`, `jyn` |
| k | 1,179 | 14 | `kaal`, `kaew`, `kaiou`, `kaira`, `kane`, `kaniel`, `kashi`, `katou`, `kendra`, `khempal`, `komal`, `kray`, `krum`, `kurono` |
| l | 525 | 15 | `lanning`, `lbu`, `leafman`, `leito`, `liam`, `linc`, `liv`, `lkut`, `lngat`, `lon`, `longway`, `lp`, `ltu`, `luarbiasa`, `lіоn` |
| m | 2,220 | 11 | `maati`, `mannu`, `marv`, `maseo`, `matty`, `mein`, `migi`, `mine`, `minton`, `myeong`, `myung` |
| n | 235 | 8 | `naw`, `ned`, `ngou`, `nhong`, `nn`, `nui`, `nuna`, `nzt` |
| o | 129 | 3 | `omalu`, `outis`, `owi` |
| p | 1,579 | 7 | `parbat`, `periu`, `platt`, `pleung`, `poe`, `poiis`, `puddin` |
| q | 14 | 3 | `quan`, `que`, `quot` |
| r | 459 | 15 | `rango`, `raza`, `reb`, `redman`, `reggie`, `renu`, `ric`, `riva`, `rocco`, `rogosh`, `roth`, `ruka`, `russ`, `ryeong`, `ryu` |
| s | 1,372 | 24 | `sanju`, `sansa`, `sarkar`, `saroo`, `scpd`, `seita`, `ser`, `serento`, `sha`, `shado`, `shao`, `shi`, `shu`, `simu`, `sinn`, `siyama`, `smek`, `snart`, `sola`, `sox`, `spencer`, `stensiand`, `subbu`, `syd` |
| t | 1,043 | 15 | `takiya`, `tars`, `teiah`, `tej`, `tess`, `tessa`, `theone`, `thinman`, `tidakl`, `tig`, `tintin`, `tobin`, `toom`, `tran`, `tripp` |
| u | 142 | 2 | `unh`, `uu` |
| v | 97 | 6 | `vail`, `val`, `ve`, `vee`, `viraj`, `vu` |
| w | 201 | 6 | `waller`, `wasn`, `watari`, `whats`, `winn`, `wouldn` |
| x | 9 | 2 | `xiang`, `xin` |
| y | 79 | 4 | `yeon`, `yorla`, `yuanjia`, `yuki` |
| z | 43 | 5 | `zaya`, `zeng`, `zhen`, `zhong`, `zuba` |
| other | 2 | 2 | `ª`, `émilien` |
| **合计** | **14,748** | **252** | **15,000 个候选词全部留存** |

词形按原始键保留，未将 `lіоn` 中的非 ASCII 字符替换为外观相近的拉丁字母。

## 八、自动化测试与 CDP 证据

### 8.1 pytest：实际通过

运行环境：

```text
Python 3.13.15
pytest 9.2.0
```

统一核验脚本调用：

```python
pytest.main([
    "-p", "no:cacheprovider",
    "tests/test_stage3_trilingual_quality_gates.py",
    "-v", "-s"
])
```

Python 以 `-B` 运行，数据读取使用已扫描的内存快照。

| 测试 | 结果 |
|---|---|
| `test_jawi_integrity` | PASS |
| `test_story_and_collocations` | PASS |
| `test_whatsapp_messages` | PASS |
| `test_provenance_and_status` | PASS |
| `test_three_state_conservation` | PASS |
| `test_search_index_sync` | PASS |
| `test_trilingual_coverage` | PASS |

```text
7 passed in 2.98s
pytest.main returncode = 0
```

现有断言仍未覆盖：

- 分片、索引和候选池逐词 ID 一致性；
- `DBP 原文` 标签与实际引文文本的关系；
- `spoken_shortcuts` 原始容器类型及完整必填字段；
- 隔离清单与分片 missing_source 的集合相等关系——现有测试仅分别检查数量，本轮独立脚本已补查集合。

所以 **pytest 通过与本报告发现问题并不矛盾**。

### 8.2 CDP：代码改进确认，全量验收未成立

当前脚本覆盖：

| 类别 | 样词 |
|---|---|
| `official` | `asli`、`memasak`、`tajam` |
| `root_derived` | `anakku` |
| `corpus_usage` | `water`、`milan`、`head` |
| `missing_source` | `jaikant` |

本次代码复核确认：

- 三种精编来源标签已使用硬断言；
- 英文释义、英文搭配、英文消息缺失会抛错；
- 气泡或搭配数量不足会抛错；
- missing_source 会检查待补提示；
- 结尾已改为 `process.exit(exitCode)`，断言失败不再强制返回 0。

仍有证据缺口：

1. 脚本仅覆盖 **8 词、四类状态**，没有全库遍历。
2. 读取了页面 `title`，但未断言它等于目标词；选词失败时可能检查到旧页面。
3. 搭配数量是全页总数，未逐义项检查。
4. 未检查全部八维、正式场景英文以及当前构建标识。
5. 本轮没有重新运行该写截图及浏览器配置的脚本。只读沙箱不允许其正常写入；现有 CDP 端口 `9462` 连接被拒绝。

本次确认 `21`—`28` 对应的八张截图文件存在且非空，但文件存在不能独立证明本轮运行成功或全部断言通过。用户提供的历史 returncode 0，本报告不冒认成独立重跑结果。

工作台 `http://127.0.0.1:8766/` 及 `/data/manifest.json` 均返回 HTTP 200，线上 manifest 为 `om-20261103-v8488`。这只证明服务与构建可读取，不能替代浏览器交互验收。

**CDP 裁定：测试代码修复部分通过；八词历史证据存在；全量浏览器门禁未通过验收。**

## 九、文档与归档复核

`START.md` 与 `docs/PROJECT_HANDOFF.md` 顶部均已更新为：

```text
14,748 enriched + 0 source_only + 252 missing_source
official 7,479 / root_derived 2,328 / corpus_usage 4,941
om-20261103-v8488
```

当前数据和相关修复已提交，审计前后工作区均干净。

文档仍需消除下列冲突：

- `START.md` 第三节仍列旧构建 `om-20261102-v1`，并称成果“已落盘、未提交”。
- 交接文档保留较早资产表和“尚未接入”等现状表述，需要明确标为历史快照。
- 顶部“全量 15,000 候选词八维精编完成”“全部门禁 100% 闭环”的声明超出实际证据，应按本报告修订。

Git 归档通过，不代表这些验收声明成立。

## 十、整体签字前的关闭条件

| 优先级 | 待关闭事项 | 验收条件 |
|---|---|---|
| 高 | 三词位序及分片 ID 错配 | 修正 `head`、`hung`、`stand`，候选池／精编／分片／索引逐词 ID 一致，分片唯一 ID 恢复 15,000 |
| 高 | 编辑改述展示为 DBP 原文 | 区分词条来源与义项引文；原文提供可核对定位，改述明确标识 |
| 高 | 旧白名单入口仍可重写来源 | 移除或禁用旧放行逻辑，使可执行发布入口统一遵循三阶规则 |
| 中 | 八维契约缺口 | 补齐规范容器；解决七词八义项词性缺失，并增加相应断言 |
| 中 | CDP 验收缺口 | 增加目标词头、构建及逐义项断言；按工程要求完成全量验收，或明确调整验收范围 |
| 中 | 文档过度声明及旧状态冲突 | 统一当前状态，明确历史快照，结论与实测范围一致 |

本轮仅执行独立审计，没有修改上述问题。

## 十一、关键证据指纹

| 文件 | SHA-256 |
|---|---|
| `app/static/data/manifest.json` | `cfef83c346df0d187cda47beb32f56ac5e5695f3d463cf6a45c8adff62919e97` |
| `app/static/app.js` | `8b2c7125e4a3d27d4df0b46872ca7b4f755761eaa2e6efb28cd2694a01020738` |
| `tests/test_stage3_trilingual_quality_gates.py` | `b45fdfcbdeee42f873a808d990aecd9b53b262570db07c9881ce32f71f912a35` |
| `tests/verify_trilingual_e2e.mjs` | `7060e344e7c3813d4df4d8432a4edfe99cceba8a504be75802cdf70e95ed1486` |
| `data/audit/quarantine_triage_report.json` | `d6bc6d4c16716d6b12381745802d3362b1356f11fc264fcc7d12661d7e8cf5ab` |

**独立终审签署：三态账本、指定清洗、三语字段覆盖、隔离集合及七项 pytest 通过；ID 一致性、来源诚实性完整闭环、八维契约及全量 CDP 验收尚未通过，暂不签署整体全绿收官。**