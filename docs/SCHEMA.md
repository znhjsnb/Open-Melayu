# Open-Melayu 15K 数据契约

当前发布为 `om-20261103-v9756`，`manifest.format_version = 2`。本页描述现存 JSON，不要求把历史兼容字段强行迁移成新格式。完整样本：[saya](../data/enriched/saya.json)、[datang](../data/enriched/datang.json)。

## 文件层级与身份

| 文件 | 形态与用途 |
| --- | --- |
| `data/candidate_pool_15k.json` | 候选池；15,000 个词头的位序依据 |
| `data/enriched/<word>.json` | 单个精编对象；14,748 个文件；不允许 legacy `batch_*.json` 镜像混入 |
| `data/prpm_raw/<word>.json` | PRPM 来源核验材料；不等同于精编成品 |
| `app/static/data/manifest.json` | 构建 ID、三态数量、来源分布与格式版本 |
| `app/static/data/search_index.json` | 15,000 个轻量索引对象组成的数组 |
| `app/static/data/shards/<key>.json` | 以规范词头为键、完整详情为值的对象；共 27 片 |

索引、候选池和分片的词头与位序 ID 必须逐词一致，ID 为唯一的 1–15,000，不是 JavaScript 数组下标。词头规范化为去首尾空白、小写。分片键按规范词头首字符分配：ASCII `a`–`z` 各一片，其余归 `other`。仅按首字符分片，不按 Jawi 或中文分片。

精编源对象以以下七个主容器为核心；发布到分片后补充 `id: number`、`word: string`、`is_enriched: boolean`、`data_state: string` 等运行字段。源文件未必包含这些外层字段，消费者不能据此误判其精编内容缺失。

## 八维、七主容器

| 维度 | 容器 | 类型与约束 |
| --- | --- | --- |
| 1 基础词头 | `headword` | object：`word: string`、`syllables: string/null`、`ipa: string/null`、`jawi: string/null`、`frequency_rank: number`、`status: string` |
| 2 构词 | `morphology` | object：`is_root?: boolean`、`root_word?: string/null`、`root_jawi?: string/null`、`affix: string/null`、`affix_type: string`、`formula: string`、`pattern_note?: string`、`word_family?: array` |
| 3 释义 | `senses` | 非空 array；每义项独立编号与词性，保留马中英释义和来源标记 |
| 4 搭配 | `senses[].collocations` | array，每义项至少 2 组不同搭配；每组 `{ms: string, zh: string, en: string}` |
| 5 双境语料 | `dual_scenarios` | array；当前精编以正式场景在前、口语场景在后 |
| 6 口语速查 | `spoken_shortcuts` | array；可为空 `[]`，不虚构不存在的缩略语；条目 `{abbr, full_form, note}` 均为 string |
| 7 社交礼仪 | `cultural_pragmatics` | object：`register`、`politeness_note`、`usage_etiquette` 等文字字段 |
| 8 词源与记忆 | `etymology` | object：`historical_story: string`、`cognitive_memory_aid: string`，可含 `origin`、`source_language`、`root_origin` |

`morphology.word_family[]` 常用 `{word, affix, gloss}`。Jawi 缺乏依据时用 `null`，不得用空字符串、纯问号或伪造字形；已知词根的 Jawi 存 `root_jawi`。词源叙事与教学记忆法须明确区分。

`?` 表示字段可能缺失。现存精编文件中 8 个未提供布尔 `is_root`、4 个未提供字符串 `root_word`；消费者应兼容这些缺失，不据此推造词根。当前索引的 `r` 是检索层实际使用的词根投影。

`sociolinguistic_register` 是 `cultural_pragmatics` 的兼容对象别名；两键并存时深度相等，消费者优先读取后者。它不是字符串形式的 `register` 字段。

### 义项

```json
{
  "id": 1,
  "pos": "pronoun",
  "ms_definition": "ganti nama diri pertama (lebih halus drpd aku), hamba",
  "ms_is_verbatim": true,
  "zh_definition": "我；第一人称单数代词，表达礼貌、中性距离，可作主语、宾语或后置领属语。",
  "en_definition": "I; me; my when placed after a noun. A polite, neutral first-person singular pronoun.",
  "collocations": [
    {"ms": "nama saya", "zh": "我的名字", "en": "my name"},
    {"ms": "rumah saya", "zh": "我的家；我的房子", "en": "my home; my house"}
  ]
}
```

上述为 `saya.senses[0]` 节选；`nuances?: string` 承载语境与使用边界，部分兼容数据使用 `nuance_note` / `nuance`。`pos` 和三语定义非空。`ms_is_verbatim` 为布尔值，仅严格 `true` 且词头来源为 official 时显示 DBP 原文；缺失标记不得默认当成引文。

### 双境与口语消息

- 正式项：`scenario: "formal"`，`context: string`、`ms: string`、`zh: string`、`en: string`。
- 口语项：`scenario: "colloquial"`，通常含 `context`、`ms_spoken`、`ms_standard`、`zh`、`en`、`spoken_features: string[]`；必须有至少两条 `messages`。
- `messages[]`：`speaker: string`（含人物身份/关系）、`ms_spoken: string`、`ms_standard: string`、`zh: string`、`en: string`。正式还原与口语原句分开保存，不覆盖原句。

## 数据状态与来源层级

三态属于分片运行字段 `data_state`，与 `headword.status` 的来源类别不同：

| `data_state` | 索引 `st` | `is_enriched` / 索引 `e` | 当前数量 |
| --- | --- | --- | ---: |
| `enriched` | `e` | true / 1 | 14,748 |
| `source_only` | `s` | false / 0 | 0 |
| `missing_source` | `m` | false / 0 | 252 |

总量恒为 15,000；`source_only`、`missing_source` 不承诺满足完整八维契约。不可为了补齐数量生成假官方定义或 Jawi。

精编来源 `headword.status` 为 `official`（7,479）、`root_derived`（2,328）、`corpus_usage`（4,941）。附加 `provenance` 对象常含 `has_official_dbp: boolean`、`has_official_root_dbp: boolean`、`source_type: string`、`attribution: string`。实际证据仍须对照 PRPM 原始记录，而非仅信任布尔标记。

| 展示标签 | 必要条件 |
| --- | --- |
| `DBP 原文:` | `official` 且 `ms_is_verbatim === true`；定义是对应官方原文的归一化连续子串 |
| `马来语释义 (基于 DBP 官方词条):` | `official`，非已核验直接引文 |
| `马来语释义 (基于 DBP 词根推导):` | `root_derived`，具备官方词根与构词证据 |
| `马来语释义 (字幕高频语料用法):` | `corpus_usage`，不伪称官方直接收录 |

引文核验清洗控制字符、合并空白并转小写，不允许任意改写后仍标记原文。禁止 `U+0081/U+00AD/U+200B/U+200C/U+200E` 等既定门禁字符进入精编内容。

## 搜索索引

```json
{"id":1,"w":"saya","j":"ساي","p":"/ˈsajə/","r":"saya","a":"","s":["我；第一人称单数代词，表达礼貌、中性距离，可作主语、宾语或后置领属语。","是；在传统或郑重语境中应答呼唤、表示应承。"],"e":1,"st":"e"}
```

| 键 | 类型 | 用途 |
| --- | --- | --- |
| `id` | number | 候选池位序与默认排序 |
| `w` | string | Rumi 词头，详情查找键 |
| `j` | string | Jawi 检索文本；索引无资料可用空字符串 |
| `p` | string | IPA，允许空字符串 |
| `r` | string | 词根检索与 `#root:`，无资料可为空 |
| `a` | string | 口语别名检索文本，可为空；不是数组 |
| `s` | string[] | 中文释义摘要；不是完整 senses 对象数组 |
| `e` | 0 / 1 | 精编快捷标记 |
| `st` | `e` / `s` / `m` | 三态快捷标记 |

索引是轻量检索投影，可能只含部分义项摘要，不能取代完整详情。Worker 的中文、Jawi、词根与别名检索读取这些字段；没有完整英文释义全文检索索引。OSA 提供有限编辑距离的拼写候选，不是语义向量搜索。

## 发布分片与缓存

每片为 `{"saya": {"id": 1, "word": "saya", ...}}` 形式的字典，详情含上述容器。`a.json` 至 `z.json` 与 `other.json` 合计 27 片，必须与索引、候选池逐词守恒。

`manifest.json` 含 `build_id`、`built_at`、`total_words`、`enriched_count`、`source_only_count`、`missing_source_count`、`provenance_breakdown`、`conservation_check`、`format_version`。`build_id` 必须与 `app/static/data.js` 中 `DATA_VERSION` 一致。修改数据后统一发布分片与索引，不单独更改版本掩盖差异。

浏览器将分片保存在 IndexedDB，RAM LRU 最多保留 5 片；搜索索引使用按 DATA_VERSION 命名的 Cache API 缓存。页面 shell 单独使用 `SHELL_CACHE = open-melayu-shell-v5`，Network-First、网络失败仅回退同名缓存；`/data/` 请求不由 Service Worker 接管。数据版本和页面缓存版本独立升级。

验收命令及浏览器限制见 [README](../README.md) 与 [工作台记录](WORKBENCH_IMPLEMENTATION.md)。三态、来源核验、Jawi、逐义项搭配、双人消息、三语覆盖及索引一致性由 `tests/test_stage3_trilingual_quality_gates.py` 检查。
