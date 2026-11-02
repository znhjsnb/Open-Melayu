# Batch 1 词条交付与来源说明

日期：2026-11-01。范围仅为用户指定的 10 词及独立 JSON 文件；未运行外部模型、修改爬虫或部署服务。

## 交付约定

- 主文件：`data/enriched/batch_1.json`，按用户顺序保存 10 个对象。`data/enriched/<word>.json` 各保存一个对应对象。
- 严格保留用户给出的七个顶层字段，包括独立的 `spoken_shortcuts`；未删键或额外加入来源字段。
- `frequency_rank` 是 `raw/opensubtitles_frequency_ms_full.txt` 的行序（1–10），并与 `data/pilot_50_candidates.json` 复核。这是字幕词频，不是 DBP 排名，也不是跨文体总体排名。[语料上游](https://github.com/hermitdave/FrequencyWords/blob/master/content/2018/ms/ms_full.txt)。
- 新编例句及中英文翻译属于本批编辑内容；不声称逐字取自 Tatoeba、新闻或真实用户对话。formal 表示规范书面语体；aku 采用文学叙事，kau 采用规范代词附着式，tak 保留在新闻体的口语引语中。不能据正式例句推断这些称呼适合对上司使用。
- `∅` 表示无词缀。kau 和 tak 标记现代缩短关系；不把缩短伪装成加缀。代词附着形式和强调词 -lah 在说明中与派生词缀区分。功能词无可证派生词族时保留空数组。

## Jawi 与音节

对用户消息中的 `???`，优先读取同工程 UTF-8 PRPM 缓存恢复，而非猜写或将乱码落盘：

| word | Jawi | syllables | 依据 |
| --- | --- | --- | --- |
| saya | ساي | sa.ya | `raw/prpm_cache/saya.json` |
| yang | يڠ | yang | `raw/prpm_cache/yang.json` |
| aku | اکو | a.ku | `raw/prpm_cache/aku.json` |
| dia | دي | dia | DBP Daftar Rumi-Jawi 交叉检索，原样标注 `[dia]` |
| awak | اوق | a.wak | Jawi 来自缓存；音节据 `[a.waʔ]` 恢复为 Rumi 分节，非缓存原有 syllables 值 |
| kau | کاو | kau | `raw/prpm_cache/kau.json` |
| ini | اين | i.ni | `raw/prpm_cache/ini.json` |
| di | د | di | 单音节；DBP 的 di bawah 条目显示 Jawi 的 د，Kaikki 亦记录辅音前 د、元音前 دأ |
| tak | تق | tak | Jawi 来自缓存；`[taʔ]` 是发音标注，tak 为单音节拼写分节 |
| dan | دان | dan | 单音节；本地 Kaikki Jawi，并由 DBP 拼写答复交叉确认 |

在线补核入口：[dia 的 Daftar Rumi-Jawi](https://prpm.dbp.gov.my/cari1?keyword=%D8%AF%D9%8A)、[di bawah](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=di+bawah)、[包含 DAN = دان 的 DBP 答复](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=konservasi)。PRPM 主词头直连经 web 工具报错、经 Python 请求超时；补核使用可返回内容的交叉检索结果，未改写原始缓存或将失败伪报为抓取成功。

音标从本地 `raw/kaikki_malay.jsonl` 的未损坏字段恢复。saya、dia 选择半岛南部常见 /ə/ 词尾读法，并在词条说明保留 /a/ 变体；awak、tak 采用实际音值的方括号；kau 用双元音标记 [kau̯]。DBP 的 Rumi/Jawi 拼写和 Kaikki 的 IPA 各有来源，不混称为 DBP 官方 IPA。

## 释义来源与边界

- saya、yang 的功能词和神灵义、awak、kau 的主代词义、tak：依用户所给 DBP 定义及本地 PRPM 缓存摘取、分义或去除例句，不改变核心意义。
- aku、ini 以及 kau 的被动附着义：本次实际证据为 DBP **Kamus Pelajar Edisi Kedua**，词条明确注明，未改标为 Kamus Dewan。
- dia 的核心代词与 itu dia：由 [PRPM 的 itulah 交叉检索](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=itulah) 补核 Kamus Dewan 释义。di 的介词义由 [kata sendi nama 交叉检索](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=kata+sendi+nama) 及 [pada di](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=pada+di) 补核。
- dan：采用 [DBP Khidmat Nasihat 关于 dan / serta 的答复](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=ikut+serta) 中已核实的释义。**没有取得该词 Kamus Dewan 独立词头的逐字原文**，词条内已标清；不能把本批所有 `ms_definition` 宣称为同一部词典的官方逐字引文。
- yang 的 sayang 缩短呼语义、di 的字母 D 名称义：仅见所给 Kaikki，`ms_definition` 明标 `Takrif editorial berdasarkan Kaikki`。Schema 没有逐义来源字段，故用字段文字及 nuances 保存边界。
- 关系标记 yang、神灵义 yang、sayang 缩短呼语是不同来源的同形形式；介词 di 与英语字母名 di 也不共享词源。tak 的敲击声名词不从 tidak 派生。未把缺乏佐证的 dayang 缩短形式扩为新的正式义项。
- dan 的词源未获证据，填写 `Uncertain`；origin/source_language 在用户结构中是自由字符串，不是受限枚举。不以基础词身份反推继承词源。yang 的 ia + -ng、dia 的 di + ia 等保留来源分析和不确定性，不宣传为能产现代构词规则。
- Malaya 规则为候选映射，不是拼写权威；未照搬 him/his、you/your、ana 等跨词义或跨语域替换。diorang、korang 在说明中明示复数；kat → di 限定为地点语境。

用法补核：[awak 与 kamu 的同辈/年龄差异](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=awak)、[kau- 与 ku 的连写](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=kependekan)、[di 与 di- 的分写/连写](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=tn)、[tak 可用于对话](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=kau)。跨族群礼貌指导为综合编辑建议，不是把年龄、性别或族群当作可自动使用亲密代词的许可。

## 验证

验证结果见 `data/audit/batch_1_verification.json`。本批执行一次针对实际产物的字段、类型、枚举、Unicode、词频与双文件一致性检查，并对例句及词源边界作编辑复核。结构通过不代表所有语言学问题得到独立专家认证。尚存的证据缺口是 dan 的词源及独立 Kamus Dewan 词头原文；均已在词条中明示。
