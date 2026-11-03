# Open-Melayu 15K 独立终审报告

- 审计日期：2026-11-03（Asia/Singapore）
- 定向复核完成时间：09:53:52（UTC+08:00）
- 审计角色：Codex CLI 独立终审
- 发布构建：`om-20261103-v9756`
- 当前提交：`4541e6749ea0884b49463cb64dfc654211674187`
- 上轮全库审计基线：`27d9fd531194419ef345e398cabca87e40c1a2d1`
- 报告目标：`docs/FINAL_15K_AUDIT_REPORT.md`
- 交付方式：本会话文件系统只读，完整报告输出于本回复，未覆盖磁盘文件。

## 一、最终裁定

**终审通过，批准 Open-Melayu 15K 按本报告确认的范围收官。上一轮第十节列出的六项关闭条件均已满足，无剩余阻断项。**

本次结论由两部分证据组成：

1. 沿用上一轮已经通过、且相关数据和测试未变化的全库检查及七项 pytest 结果。
2. 本轮独立完成指定文件审查、隔离行为验证、失败反例验证、浏览器证据核验及当前 HTTP 发布内容核对。

最终交付规模为 **15,000 个候选词，其中 14,748 个完成三语八维精编，252 个明确保留为 `missing_source`**。该结论不将待补词计为已精编，也不将八个代表词的浏览器验收扩大为 15,000 词浏览器全量验收。

## 二、复核范围与基线延续依据

### 2.1 本次定向复核文件

| 文件 | 核查内容 |
|---|---|
| `src/run_overnight_closure_and_audit.py` | 委托分类后的 manifest 路径与汇总返回 |
| `app/static/app.js` | 来源状态与严格布尔值联合判断 |
| `tests/verify_trilingual_e2e.mjs` | 构建绑定、英文非空、逐义项标签及失败行为 |
| `data/audit/cdp_trilingual_e2e_evidence.json` | 时间、构建、返回码、八词结果及截图记录 |
| `START.md` | 当前账本、引文匹配口径与验收范围 |
| `docs/PROJECT_HANDOFF.md` | 当前交付声明、匹配口径与证据引用 |

另定点读取实际 manifest、`data.js`、七个精编样词及相关来源分类代码，核对八张证据截图。

**未重新遍历 29,760 个 JSON 文件，未重跑全库 pytest，未执行生产分类、数据重建或发布。**

### 2.2 数据未变化的独立核验

三个数据目录在上轮基线与当前 HEAD 中的 Git 树对象完全一致：

| 目录 | 两次提交相同的 Git 树对象 |
|---|---|
| `data/enriched` | `76730361d07f10eb12abde0d35ba10fe4688bf6a` |
| `data/prpm_raw` | `be5c29cf695b781d90e4d75539f331c8baadea99` |
| `app/static/data/shards` | `57446bc170812230f029abf4f527a0949fff9520` |

上述目录及 manifest、`data.js`、搜索索引、第三阶段 pytest 文件，相对上轮基线均无 Git 内容差异。审计前后工作区干净，HEAD 未变化。

因此，相关全库审计结果继续有效，无需重复扫描。

## 三、全库资产与三态账本

本节沿用上一轮实际全库核验结果。

### 3.1 全库检查规模

| 数据资产 | JSON 文件数 |
|---|---:|
| 独立精编文件 | 14,748 |
| PRPM 缓存 | 14,977 |
| 静态分片 | 27 |
| 候选池、索引、manifest 及辅助证据 | 8 |
| **合计** | **29,760** |

上一轮累计读取 **199,642,839 字节**，JSON 解析错误及重复键均为 0。

### 3.2 三态守恒

| 状态 | manifest | 分片 | 搜索索引 |
|---|---:|---:|---:|
| `enriched` | 14,748 | 14,748 | 14,748 |
| `source_only` | 0 | 0 | 0 |
| `missing_source` | 252 | 252 | 252 |
| **合计** | **15,000** | **15,000** | **15,000** |

```text
14,748 enriched + 0 source_only + 252 missing_source = 15,000
```

- 精编覆盖率：**98.32%**。
- 明确保留待补：**1.68%**。
- 历史 `batch_*.json` 重复镜像：**0**。
- 252 个最终待补词与隔离分诊记录逐词一致，均具有非空原因。
- 分诊报告累计救回 52 词；原始 285 个隔离词中，33 个已进入精编库。
- `still_unrecovered_type_a` 为空。

**裁定：通过，延续有效。**

## 四、逐词 ID、结构与三语覆盖

本节沿用上一轮实际全库核验结果。

### 4.1 位序与唯一性

候选池、搜索索引及分片覆盖同一组 15,000 个词形，唯一 rank／ID 完整覆盖 **1—15,000**。

| 核查项目 | 不一致或重复数量 |
|---|---:|
| 分片 ID 与候选池 rank | 0 |
| 搜索索引 ID 与候选池 rank | 0 |
| 精编 `frequency_rank` 与候选池 rank | 0 |
| 跨分片重复词形 | 0 |
| 索引状态与精编标记不一致 | 0 |

原 ID 缺陷已经修复：

| 词形 | 候选池、精编、分片及索引一致值 |
|---|---:|
| `head` | 6,740 |
| `hung` | 6,183 |
| `stand` | 11,421 |

### 4.2 七主容器

14,748 个精编词全部具备正确类型的七主容器：

```text
headword              object
morphology            object
senses                array
dual_scenarios        array
spoken_shortcuts      array
cultural_pragmatics   object
etymology             object
```

搭配按义项保存在 `senses[].collocations`，构成独立教学维度；七主容器承载八维内容。

### 4.3 字段与教学结构

| 检查项 | 总量 | 不合格 |
|---|---:|---:|
| 义项 `pos` 非空 | 28,017 | 0 |
| 义项马、中、英释义非空 | 28,017 | 0 |
| 每义项至少两组不同马来语搭配 | 28,017 | 0 |
| 搭配马、中、英字段非空 | 56,933 | 0 |
| 正式场景马、中、英字段非空 | 14,748 | 0 |
| WhatsApp 至少两条消息、两名不同说话人 | 14,748 | 0 |
| 消息身份、马来语及中英字段非空 | 29,981 | 0 |
| 历史故事满足既定长度检查 | 14,748 | 0 |
| 记忆口诀非空 | 14,748 | 0 |

**裁定：通过，延续有效。**

## 五、字符清洗、来源分级与引文口径

### 5.1 字符与 Jawi

上一轮确认，精编内容及发布分片中的以下字符全部为 0：

```text
U+0081  U+00AD  U+200B  U+200C  U+200E
```

词头及词根 Jawi 的空白字符串、纯问号值均为 0。

- `headword.jawi = null`：5,696 词。
- `morphology.root_jawi = null`：6,168 词。

有依据保留未知值符合工程规则，不计作伪造。

### 5.2 来源分级

| 来源状态 | 词数 |
|---|---:|
| `official` | 7,479 |
| `root_derived` | 2,328 |
| `corpus_usage` | 4,941 |
| **合计** | **14,748** |

上一轮已核验直接 DBP 缓存证据、词根证据及相关构词标记。旧入口白名单保持为空。

### 5.3 `ms_is_verbatim` 的准确含义

| 来源与标记 | 义项数 |
|---|---:|
| `official`，true | 1,814 |
| `official`，false | 12,505 |
| `root_derived`，false | 4,781 |
| `corpus_usage`，false | 8,917 |
| **合计** | **28,017** |

采用的匹配口径为：**清洗指定控制／格式字符、折叠空白、去除首尾空白并转为小写后，检查马来语释义是否满足连续子串匹配**；现行生成逻辑另要求归一化释义长度至少为 6。

该口径不等于未经处理、大小写敏感的逐字符原文匹配。上一轮指出的 450 个 true 义项属于这一区别，本次通过明确归一化口径关闭文档歧义，无需修改相关数据。

`START.md` 已明确清洗、空白与小写规则及 1,814／12,505 的区分；交接文档已改用归一化连续子串匹配表述，并引用本终审报告。

**裁定：来源分级及匹配口径通过。**

## 六、发布入口与前端条件定向验证

### 6.1 manifest 路径

实际代码已改为：

```python
manifest_path = ROOT_DIR / "app" / "static" / "data" / "manifest.json"
manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
```

本轮提取实际 `reconcile_provenance_status()` 函数，在内存中隔离执行；仅替代会改写生产数据的严格分类调用，保留真实 manifest 读取及返回逻辑。

验证结果：

```json
{
  "total_enriched": 14748,
  "official_count": 7479,
  "root_derived_count": 2328,
  "corpus_usage_count": 4941,
  "updated_files": 0
}
```

委托调用发生一次，随后汇总读取成功。生产分类脚本未被实际执行。

**裁定：路径错误关闭。**

### 6.2 前端严格判断

实际标签表达式已使用：

```javascript
head.status === 'official' && s.ms_is_verbatim === true
```

本轮从真实源码提取表达式执行，共通过 **10 组条件检查**，包括：

| 输入 | 结果 |
|---|---|
| `official` + 布尔 true | `DBP 原文:` |
| `official` + 布尔 false | 官方词条编辑释义标签 |
| `official` + 字符串 `"true"`／`"false"` | 官方词条编辑释义标签 |
| `official` + 1／null／undefined | 官方词条编辑释义标签 |
| 未知状态 + true | 不显示 `DBP 原文:` |
| `root_derived` + true | 词根推导标签 |
| `corpus_usage` + true | 字幕语料标签 |

**裁定：严格状态与布尔联合判断通过。**

## 七、CDP 测试与归档证据复核

### 7.1 构建绑定

测试从本地 manifest 读取预期构建，并分别比较：

```javascript
buildInfo.manifestBuildId === expectedBuildId
buildInfo.dataJsVersion === expectedBuildId
```

当前预期值及证据值均为：

```text
om-20261103-v9756
```

本轮分别将线上 manifest 构建号和 `data.js` 版本替换为错误值，两个反例均被实际断言拒绝。

### 7.2 八词验收证据

证据文件记录：

```text
verified_at = 2026-11-03T01:50:18.555Z
本地时间    = 2026-11-03 09:50:18.555 +08:00
sample_count = 8
returncode   = 0
```

| 样词 | 预期来源／状态 | 标签数 | 实际标签或提示 | 每义项最少搭配 |
|---|---|---:|---|---:|
| `asli` | `official` | 1 | 全为 `DBP 原文:` | 2 |
| `memasak` | `official` | 1 | 全为官方词条编辑释义标签 | 2 |
| `tajam` | `official` | 1 | 全为官方词条编辑释义标签 | 2 |
| `anakku` | `root_derived` | 2 | 全为词根推导标签 | 2 |
| `water` | `corpus_usage` | 5 | 全为字幕语料标签 | 2 |
| `milan` | `corpus_usage` | 1 | 全为字幕语料标签 | 2 |
| `head` | `corpus_usage` | 2 | 全为字幕语料标签 | 2 |
| `jaikant` | `missing_source` | 0 | 待补来源说明非空 | 不适用 |

七个精编样词的 **13 个标签**全部符合预期，数量与对应词条义项数一致；样词来源状态与本地精编数据一致。

七词正式英文记录均非空，且逐词等于本地正式场景的 `en` 字段。

### 7.3 断言反例验证

本轮复用实际测试源码中的断言块，完成 **17 个失败反例**：

- `asli`、`memasak`、`tajam` 标签互换：3 个。
- 多义词末尾义项标签错误：3 个。
- 正式英文、义项英文、搭配英文、场景英文为空：4 个。
- 词头错误、搭配不足、气泡不足、标签集合为空：4 个。
- `missing_source` 提示缺失：1 个。
- 两个线上构建标识分别错误：2 个。

**17 个反例全部被拒绝，八条原始证据全部通过。**

Python 修改文件 AST 解析通过；`node --check tests/verify_trilingual_e2e.mjs` 返回码为 0。

### 7.4 截图与证据边界

八张截图均存在，PNG 文件头正确，实际文件大小与证据记录完全一致：

```text
asli       115,818 bytes
memasak    128,989 bytes
tajam      111,954 bytes
anakku     127,140 bytes
water      144,603 bytes
milan      149,615 bytes
head       121,910 bytes
jaikant     88,705 bytes
```

本轮审查并验证的是已归档的最新 CDP 实测证据，**没有重新启动 Chromium 或重跑会写入截图的完整脚本**。

当前 `formalEn` 采集依赖首个 `.bubble-en` 的布局顺序。本轮通过与七词正式场景英文逐项等值比较，确认当前记录准确；不据此宣称该选择器能够独立检测任意正式区块删除或布局改排。

**裁定：本次约定的八词代表性验收通过。**

## 八、pytest 基线与当前发布内容

### 8.1 七项 pytest

测试文件及相关数据保持不变，沿用上一轮实际结果：

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

本轮未重复运行上述全库测试。

### 8.2 当前 HTTP 内容

本轮独立请求 `http://127.0.0.1:8766`：

| 路径 | HTTP 状态 | 与本地文件逐字节一致 |
|---|---:|---|
| `/data/manifest.json` | 200 | 是 |
| `/data.js` | 200 | 是 |
| `/app.js` | 200 | 是 |

当前实际服务已提供本轮核查的严格标签代码，manifest 与 `data.js` 均对应 `om-20261103-v9756`。

## 九、文档与 Git 状态

当前文档的精编规模、待补数量、三态账本、来源分布、构建号及八词浏览器验收范围一致。

- `START.md` 明确早期第一至第五节为历史阶段快照。
- 交接文档明确第 2—7 节为历史快照，当前收官状态以顶部与第 8.6 节为准。
- 归一化引文匹配与未经处理的逐字符匹配已经区分。
- CDP 新证据具有明确文件入口。
- 审计前后工作区干净，HEAD 均为 `4541e6749ea0884b49463cb64dfc654211674187`。
- 本轮未修改生产数据、未提交、未重新发布。

**裁定：文档对齐通过。**

## 十、上一轮关闭条件逐项裁定

| 上轮事项 | 本轮证据 | 最终状态 |
|---|---|---|
| 委托入口 manifest 路径错误 | 实际函数隔离执行，真实 manifest 汇总读取成功 | **已关闭** |
| 前端严格来源条件未兑现 | 实际表达式含严格联合条件，10 组检查通过 | **已关闭** |
| 引文匹配声明与实现口径不一致 | 文档明确归一化口径，本报告保留准确边界 | **已关闭** |
| official 标签断言过宽 | 按预期值检查全部标签，标签互换反例被拒绝 | **已关闭** |
| CDP 缺构建绑定及复测证据 | 双构建比较、八词新证据、返回码及截图记录齐备 | **已关闭** |
| 文档结论超出证据范围 | 明确全库基线、定向验证与八词浏览器证据的区别 | **已关闭** |

本轮未发现需要重新全量扫描或阻止当前构建收官的问题。

## 十一、关键指纹与最终签署

### 11.1 本轮实测文件 SHA-256

| 文件 | SHA-256 |
|---|---|
| `src/run_overnight_closure_and_audit.py` | `243dc99fc7c58b9d78bdce6df67cec487c4aabf790f942870b5602783b284784` |
| `app/static/app.js` | `249ce7527b0440624f309affafeb44bcc953566449d0f07b5660d4a739e14924` |
| `tests/verify_trilingual_e2e.mjs` | `f9edbfc229959a2605e204b202fd672dd7b122edb9a7b6d211e1ac2fe9dcd3e1` |
| `data/audit/cdp_trilingual_e2e_evidence.json` | `0de78fc85abba3f153ef080fda499e41f8b55940adc5e08e6d940aa5042be98a` |
| `START.md` | `7ab8d0a30afc8fad81bc0f6a800543d48bc021b53557e4f33f1f3e01a00c6f2c` |
| `docs/PROJECT_HANDOFF.md` | `bc8b26679728f94d1a446ce591f441de288a10881d48be22ccc08a6aa2df477a` |
| `app/static/data/manifest.json` | `f2e643c9bba35ce96a9d5f408ddf7ff5b91988627d0840f35eacd73ad0335f21` |
| `app/static/data.js` | `c5b13a40fa2b864f3503f3b09eaa7c6f41d986846dd0e39baf04635eb3bb712a` |
| `tests/test_stage3_trilingual_quality_gates.py` | `f201d90cdfa5a779be5aca60884e694690b56d57fc78ca466164be2c52ff3bd8` |
| `data/audit/quarantine_triage_report.json` | `16618e608ab92db2f610e18fc5d6305da9e98150c528f423ab2046295621d34f` |

### 11.2 延续的全库数据聚合 SHA-256

以下为上一轮计算值；本轮通过相同 Git 树对象及干净工作区确认数据延续，未重新遍历计算。

聚合方式：按文件名排序，对 UTF-8 编码的 `文件名 + NUL + 文件SHA256 + 换行` 依次更新 SHA-256。

| 目录 | 聚合 SHA-256 |
|---|---|
| `data/enriched` | `12f4034bf55668b53c12c2e407077e6ca270607044bc87846da70b0476b7347a` |
| `data/prpm_raw` | `304156683077a2625ea0e81e66391ff267a24fc26b20248d1b802ba51f3e884c` |
| `app/static/data/shards` | `97acf9aa8e7284c52c7f17dfd01153b446b7b1dbe814e5ba9c0e291d88fb5f0b` |

### 11.3 最终签署

**独立终审官：Codex CLI**

**签署结论：通过。**

确认上一轮全库数据、三态守恒、逐词 ID、七主容器、非空词性、指定字符清洗、三语覆盖及七项 pytest 结论继续有效；确认本轮发布入口、严格引文判断、匹配口径文档、精确标签断言、构建绑定及八词 CDP 证据已完成定向闭环。

**批准构建 `om-20261103-v9756` 以“15,000 候选词、14,748 精编词、252 明确保留待补词”的准确口径完成工程收官。** 本签署确认工程数据与约定验收结果，不扩大为全部教学内容的独立语言学认证。