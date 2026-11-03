# Open-Melayu 15K 独立终审复核报告

- 审计日期：2026-11-03（Asia/Singapore）
- 审计构建：`om-20261103-v9756`
- 审计提交：`27d9fd531194419ef345e398cabca87e40c1a2d1`
- 全量核验时间：09:44:03—09:44:27（UTC+08:00）
- 审计角色：Codex CLI 独立终审
- 报告目标：`docs/FINAL_15K_AUDIT_REPORT.md`
- 交付方式：当前沙箱只读，本报告完整输出于回复，未覆盖磁盘上的旧报告。

## 一、最终裁定

**全库三态、逐词 ID、七主容器、非空词性、指定字符清洗及三语字段覆盖通过；指定 pytest 实际运行结果为 7 passed，返回码 0。**

**暂不签署“六项问题全部闭环”的无保留收官结论。** 本轮确认以下剩余问题：

1. 旧入口虽然已经清空白名单并委托严格分类脚本，但委托结束后读取了错误的 manifest 路径，正常执行将因此中断。
2. CDP 的 `official` 标签断言接受两种标签中的任意一种，不能识别“原文”与“编辑释义”互换；上一轮要求的构建断言仍未加入。
3. 前端未实现修复说明声称的严格条件 `head.status === 'official' && s.ms_is_verbatim === true`，当前使用真值判断和默认分支。
4. `ms_is_verbatim` 全库符合现行脚本的归一化匹配规则，但该规则不能表述为全部满足未经归一化的原文连续子串匹配。

浏览器历史成功记录已经核对，本轮没有独立重跑浏览器，因此不将历史返回码作为本轮浏览器实测结果。

## 二、核验方法与证据边界

本轮使用一个 Python 进程完成单趟全库扫描，读取：

| 数据资产 | 数量 |
|---|---:|
| 独立精编文件 | 14,748 |
| PRPM 缓存文件 | 14,977 |
| 静态分片 | 27 |
| 候选池、索引、manifest、词根映射、隔离资料及辅助证据 | 8 |
| **合计 JSON 文件** | **29,760** |

累计读取 **199,642,839 字节**；未发现 JSON 解析错误或重复键。

随后在同一进程中执行：

```python
pytest.main([
    "-p", "no:cacheprovider",
    "tests/test_stage3_trilingual_quality_gates.py",
    "-v", "-s"
])
```

pytest 复用已经读取的内存快照，未修改测试文件或测试断言。读取适配器记录为：

| 快照复用操作 | 次数 |
|---|---:|
| `open` | 68,833 |
| `Path.read_text` | 14,750 |
| `json.load` | 68,831 |
| 目录枚举 | 5 |

这些计数包含相互嵌套的操作，不能相加为独立文件数。

扫描结束时，快照文件大小、修改时间及三个数据目录成员集合均未变化；HEAD 未变化，审计前后 `git status --short` 均为空。随后仅对相关源码和五处专名大小写差异进行了定点复核，没有第二次全库扫描。

本报告确认本地缓存、数据结构、发布内容和测试行为。字段齐备及缓存匹配不构成全部释义、构词和历史故事的独立语言学认证。

## 三、全库资产与三态账本

### 3.1 三态守恒

| 状态 | manifest | 分片实测 | 搜索索引 |
|---|---:|---:|---:|
| `enriched` | 14,748 | 14,748 | 14,748 |
| `source_only` | 0 | 0 | 0 |
| `missing_source` | 252 | 252 | 252 |
| **合计** | **15,000** | **15,000** | **15,000** |

```text
14,748 enriched + 0 source_only + 252 missing_source = 15,000
```

精编覆盖率为 **98.32%**，保留为 `missing_source` 的比例为 **1.68%**。历史 `batch_*.json` 镜像为 **0**。

候选池、搜索索引与分片词形键集合一致；精编文件集合与分片中的 `enriched` 集合一致。

### 3.2 分片分布

全部分片的 `source_only` 均为 0。

| 分片 | 总数 | enriched | missing_source |
|---|---:|---:|---:|
| a | 617 | 608 | 9 |
| b | 1,447 | 1,428 | 19 |
| c | 515 | 504 | 11 |
| d | 995 | 981 | 14 |
| e | 223 | 219 | 4 |
| f | 234 | 227 | 7 |
| g | 436 | 418 | 18 |
| h | 468 | 457 | 11 |
| i | 228 | 220 | 8 |
| j | 367 | 358 | 9 |
| k | 1,193 | 1,179 | 14 |
| l | 540 | 525 | 15 |
| m | 2,231 | 2,220 | 11 |
| n | 243 | 235 | 8 |
| o | 132 | 129 | 3 |
| p | 1,586 | 1,579 | 7 |
| q | 17 | 14 | 3 |
| r | 474 | 459 | 15 |
| s | 1,396 | 1,372 | 24 |
| t | 1,058 | 1,043 | 15 |
| u | 144 | 142 | 2 |
| v | 103 | 97 | 6 |
| w | 207 | 201 | 6 |
| x | 11 | 9 | 2 |
| y | 83 | 79 | 4 |
| z | 48 | 43 | 5 |
| other | 4 | 2 | 2 |
| **合计** | **15,000** | **14,748** | **252** |

### 3.3 隔离与救回记录

- 原始隔离记录：**285 词**。
- 其中当前已进入精编库：**33 词**。
- 最终保留 `missing_source`：**252 词**。
- 分诊报告累计记录救回：**52 词**，包含原未入队候选及隔离恢复对象。
- `still_unrecovered_type_a`：空。
- 最终 252 词与分片中的 `missing_source` 集合完全一致，全部具有非空原因。
- 分诊报告构建号为 `om-20261103-v9756`。

**裁定：通过。**

## 四、位序及分片 ID 修复

本轮逐词核对候选池 rank、精编文件 `headword.frequency_rank`、分片 `id` 和搜索索引 `id`。

| 核验项目 | 结果 |
|---|---:|
| 候选池唯一词形／rank | 15,000／15,000 |
| rank 范围 | 完整覆盖 1—15,000 |
| 搜索索引唯一 ID | 15,000 |
| 分片唯一 ID | 15,000 |
| 分片 ID 与候选池 rank 不一致 | 0 |
| 索引 ID 与候选池 rank 不一致 | 0 |
| 精编 frequency_rank 与候选池 rank 不一致 | 0 |
| 跨分片重复词形 | 0 |
| 逐词索引状态／精编标记不一致 | 0 |

三处原缺陷均已修复：

| 词形 | 候选池 rank | 精编 frequency_rank | 分片 ID | 索引 ID |
|---|---:|---:|---:|---:|
| head | 6,740 | 6,740 | 6,740 | 6,740 |
| hung | 6,183 | 6,183 | 6,183 | 6,183 |
| stand | 11,421 | 11,421 | 11,421 | 11,421 |

pytest 已增加分片 ID 与候选池 rank 的逐词比较及 15,000 唯一 ID 断言。独立扫描另外覆盖了精编位序和索引 ID。

额外的大小写敏感词头检查发现 `Harvard`、`Nicole`、`Ukraine`、`Watson`、`Yan` 五处专名采用首字母大写，而文件及检索键采用小写；这不属于本次 ID 错配。

**第 1 项修复：通过并关闭。**

## 五、来源分级与义项引文标记

### 5.1 三阶来源

| 来源状态 | 词数 | 本轮核对依据 |
|---|---:|---|
| `official` | 7,479 | 本词 PRPM 缓存具有非空马来语 DBP 定义字段 |
| `root_derived` | 2,328 | 标注词根具有上述缓存证据，且具有构词标记 |
| `corpus_usage` | 4,941 | 使用语料来源标签 |
| **合计** | **14,748** | 与 manifest 一致 |

未发现 `official` 缺少上述直接缓存证据，或 `root_derived` 缺少上述词根证据、构词标记及已有词根映射冲突。

### 5.2 `ms_is_verbatim` 全量结果

全部 **28,017 个义项**均具有真正的布尔值标记。

| 状态及标记 | 义项数 |
|---|---:|
| official，true | 1,814 |
| official，false | 12,505 |
| root_derived，false | 4,781 |
| corpus_usage，false | 8,917 |
| **合计** | **28,017** |

全库标记与现行生成规则一致。1,814 个 true 义项均能在对应 DBP 字段的某个字符串片段中找到归一化连续匹配，没有发现仅靠跨字段拼接才成立的匹配。

需要明确：现行规则会清理指定字符、归一空白并转成小写。**其中 450 个 true 义项不能以未经归一化的 `ms_definition` 在原始字符串中直接找到大小写敏感连续子串。** 这不等于已经发现 450 条语义错误，但不能据此宣称全部是严格逐字符原文匹配。

原报告中的示例现状如下：

| 词形 | 当前标记 | 应显示标签 |
|---|---|---|
| aa | false | 马来语释义 (基于 DBP 官方词条): |
| ab | false | 马来语释义 (基于 DBP 官方词条): |
| memasak | false | 马来语释义 (基于 DBP 官方词条): |
| tajam | false | 马来语释义 (基于 DBP 官方词条): |
| asli | true | DBP 原文: |

### 5.3 前端实际条件

`app/static/app.js:531` 实际采用：

```javascript
head.status === 'corpus_usage' ? corpusLabel
: head.status === 'root_derived' ? rootLabel
: s.ms_is_verbatim ? verbatimLabel
: editorialLabel
```

这与修复说明声称的严格条件存在差异：

```javascript
head.status === 'official' && s.ms_is_verbatim === true
```

从实际源码提取表达式执行的结果为：

| 输入 | 实际标签 |
|---|---|
| official + 布尔 true | DBP 原文: |
| official + 布尔 false | 马来语释义 (基于 DBP 官方词条): |
| official + 字符串 `"false"` | DBP 原文: |
| 未知状态 + 布尔 true | DBP 原文: |

当前精编库的状态和布尔类型均通过核验，因此未在当前有效精编数据中发现后两种输入；但“仅当 official 且严格等于 true”的实现声明尚不成立。

**第 2 项修复：当前数据的归一化标记及指定反例通过；严格条件与原文匹配口径仍需关闭。**

## 六、旧白名单入口复核

以下改动属实：

- `src/run_overnight_closure_and_audit.py:49` 为：

```python
CORE_MALAY_WITHOUT_PRPM_FILE: set[str] = set()
```

- `reconcile_provenance_status()` 已委托 `finalize_gate4_and_salvage3.main()`。
- 该函数内未保留旧的直接状态赋值逻辑。

但委托函数存在确定的路径错误：

```python
# src/run_overnight_closure_and_audit.py:305
manifest = json.loads(
    (DATA_DIR / "manifest.json").read_text(encoding="utf-8")
)
```

这里导入的 `DATA_DIR` 定义为：

```python
# src/run_expansion_to_15000_sliding_queue.py:37
DATA_DIR = ROOT_DIR / "data"
```

本轮文件存在性核对：

| 路径 | 存在 |
|---|---|
| `data/manifest.json` | 否 |
| `app/static/data/manifest.json` | 是 |

因此，若严格分类脚本正常返回，委托函数随后会读取不存在的文件并抛出 `FileNotFoundError`。本轮没有执行会写入生产数据和重新发布的 `main()`；上述结论来自调用链与真实路径核对。

**第 3 项修复：白名单放行问题已移除；入口因新增路径错误尚未完整通过。**

## 七、七容器、词性、字符清洗及三语覆盖

### 7.1 七主容器

全部 14,748 个精编文件具备正确类型的：

```text
headword              object
morphology            object
senses                array
dual_scenarios        array
spoken_shortcuts      array
cultural_pragmatics   object
etymology             object
```

上述容器及 provenance 在逐词文件与对应发布分片之间一致。

### 7.2 原七词八义项

| 词形 | 义项 | 当前 pos |
|---|---|---|
| erso | 1 | noun |
| iebih | 1 | adverb |
| mae | 1 | noun |
| pappi | 1 | noun |
| rio | 1 | noun |
| thats | 1、2 | phrase、phrase |
| tien | 1 | noun |

全库 **28,017 个义项**的 `pos` 均为非空字符串。此结果确认结构缺失已修复，不扩大为全部词性已经完成独立语言学认证。

### 7.3 字符与 Jawi

| 检查项 | 精编内容 | 分片内容 |
|---|---:|---:|
| U+0081 | 0 | 0 |
| U+00AD | 0 | 0 |
| U+200B | 0 | 0 |
| U+200C | 0 | 0 |
| U+200E | 0 | 0 |

两类 Jawi 的空白字符串及纯问号值均为 0。

- `headword.jawi = null`：**5,696 词**。
- `morphology.root_jawi = null`：**6,168 词**。

保留 null 不作为伪造或缺陷计数。

### 7.4 教学结构与三语字段

| 检查项 | 总量 | 不合格 |
|---|---:|---:|
| 义项马、中、英释义非空 | 28,017 | 0 |
| 每义项至少两组不同马来语搭配 | 28,017 | 0 |
| 搭配马、中、英字段非空 | 56,933 | 0 |
| 正式场景马、中、英字段非空 | 14,748 | 0 |
| WhatsApp 至少两条消息、至少两名不同说话人 | 14,748 | 0 |
| 消息 speaker、ms_spoken、zh、en 非空 | 29,981 | 0 |
| 历史故事满足本轮长度检查 | 14,748 | 0 |
| 记忆口诀非空 | 14,748 | 0 |

pytest 中新增的 `spoken_shortcuts` 数组类型及 `pos` 非空断言均实际通过。

**第 4 项修复：通过并关闭。**

## 八、pytest 与 CDP 验收

### 8.1 pytest 实际结果

运行环境：Python **3.13.15**，pytest **9.2.0**。

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
7 passed in 1.26s
pytest.main returncode = 0
```

### 8.2 CDP 已确认的改进

`tests/verify_trilingual_e2e.mjs` 已具备：

- `.word-title` 与目标词的相等断言。
- 每义项 `minCollocsPerSense >= 2` 断言。
- root_derived、corpus_usage 的精确来源标签断言。
- missing_source 提示检查。
- 失败时设置非零退出码。

测试样词为：

```text
asli, memasak, tajam, anakku,
water, milan, head, jaikant
```

范围为 **8 个代表词、覆盖四种状态**。

### 8.3 尚未关闭的断言缺口

第 136 行对 official 的检查为：

```javascript
if (
  expectedStatus === 'official' &&
  data.quoteLabel !== 'DBP 原文:' &&
  data.quoteLabel !== '马来语释义 (基于 DBP 官方词条):'
) {
  throw new Error(...);
}
```

该断言只检查标签属于允许集合，没有检查具体义项应当显示哪一种。

本轮从真实脚本提取断言块，在其他字段满足条件的情况下对 `memasak` 输入两种标签，结果为：

| 输入标签 | 断言结果 |
|---|---|
| DBP 原文: | 接受 |
| 马来语释义 (基于 DBP 官方词条): | 接受 |

而 `memasak` 当前标记为 false，应使用第二种标签。因此，该断言不能捕获原文与编辑释义互换。

此外：

- 尚无当前构建号断言。
- `formalEn` 被读取但没有非空断言。
- 来源标签仅取第一个 `.quote-label`，未逐义项核对。

### 8.4 历史记录与本轮运行边界

`overnight_closure_summary.json` 记录当前构建的 `cdp_returncode = 0`；八张对应截图均存在且非空。

本轮：

- `http://127.0.0.1:8766/data/manifest.json` 返回 **HTTP 200**，内容与本地 manifest 一致。
- `/api/health` 返回 **404**，本报告不将其记为健康接口通过。
- CDP 端口 `9462` 查询超时。
- 未重跑会写入截图及浏览器配置的 CDP 脚本。

用户本轮已将验收范围明确为八个代表词，因此不再要求为本次关闭进行 15,000 词浏览器遍历；但代表词验收仍须具备准确断言及可核对的运行证据。

**第 5 项修复：词头和逐义项搭配断言通过；标签精确性、构建断言及本轮独立浏览器实测尚未通过。**

## 九、文档与 Git 状态

`START.md` 与 `docs/PROJECT_HANDOFF.md` 顶部均已对齐：

- 构建：`om-20261103-v9756`。
- 14,748 词完成精编，占 98.32%。
- 252 词保留 `missing_source`，占 1.68%。
- 来源分布：7,479／2,328／4,941。
- CDP 范围：8 个代表词，覆盖四态。

`START.md` 已明确早期章节为历史阶段快照；交接文档也明确第 2—7 节为历史快照。

交接文档第 347 行仍保留“已落盘、未提交”，但位于已明确标识的历史章节内，不再与顶部当前状态构成直接冲突。历史构建号同理。

**第 6 项修复：历史与当前状态的区分通过。** 顶部有关严格引文判定及门禁全部通过的声明，应根据本报告剩余发现同步调整。

审计前后 Git 工作区均干净，HEAD 保持不变。本轮未修改文件、未提交、未重新发布。

## 十、最终签字前的剩余关闭条件

| 优先级 | 事项 | 最小关闭条件 |
|---|---|---|
| 高 | 委托入口读取错误 manifest 路径 | 改用实际发布 manifest 路径或既有 `MANIFEST_FILE`，并验证委托返回后的汇总读取 |
| 中 | 前端严格来源条件未兑现 | 明确检查 `head.status === 'official' && s.ms_is_verbatim === true` |
| 中 | 原文匹配声明与实现口径不一致 | 明确采用的大小写、空白归一规则；若坚持逐字符原文标准，重新处理 450 个不满足原始连续子串条件的 true 义项 |
| 中 | CDP official 标签断言过宽 | 按目标义项的预期标签逐项相等比较，使标签互换必定失败 |
| 中 | CDP 缺构建绑定及本轮复测 | 加入当前构建号断言，并完成八个代表词验收；记录返回码和构建号 |
| 低 | 文档结论超出本轮证据 | 保留正确统计，按本报告区分数据检查、测试覆盖和浏览器实测 |

上述修复完成后，应进行针对性复核；无需机械重复已经通过的全库数据扫描，除非修复实际改变相关数据。

## 十一、关键指纹与签署

### 11.1 文件 SHA-256

| 文件 | SHA-256 |
|---|---|
| `app/static/data/manifest.json` | `f2e643c9bba35ce96a9d5f408ddf7ff5b91988627d0840f35eacd73ad0335f21` |
| `app/static/app.js` | `094db24ed52dbfcac1a312ed33fb1bb25cafb0dcf2b931c8bfb601936d68a6f4` |
| `tests/test_stage3_trilingual_quality_gates.py` | `f201d90cdfa5a779be5aca60884e694690b56d57fc78ca466164be2c52ff3bd8` |
| `tests/verify_trilingual_e2e.mjs` | `7efa4325bc4d2bff0055ccb3e3be9da499e9867507ad4a99c9ee4538020c0d20` |
| `data/audit/quarantine_triage_report.json` | `16618e608ab92db2f610e18fc5d6305da9e98150c528f423ab2046295621d34f` |

### 11.2 数据目录聚合 SHA-256

计算方式：按文件名排序，依次对 UTF-8 编码的 `文件名 + NUL + 文件SHA256 + 换行` 更新 SHA-256。

| 目录 | 聚合 SHA-256 |
|---|---|
| `data/enriched` | `12f4034bf55668b53c12c2e407077e6ca270607044bc87846da70b0476b7347a` |
| `data/prpm_raw` | `304156683077a2625ea0e81e66391ff267a24fc26b20248d1b802ba51f3e884c` |
| `app/static/data/shards` | `97acf9aa8e7284c52c7f17dfd01153b446b7b1dbe814e5ba9c0e291d88fb5f0b` |

**独立终审签署：批准本报告确认的全库统计、三态守恒、逐词 ID 一致性、七容器及词性修复、指定字符清洗、三语字段覆盖和七项 pytest 结果。因发布入口路径错误、严格引文条件与匹配口径差异，以及 CDP 精确断言和复测证据缺口，暂不批准“六项全部闭环、整体全绿收官”的无保留签字。**