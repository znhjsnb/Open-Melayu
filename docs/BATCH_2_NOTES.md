# Batch 2 词条交付与来源说明

日期：2026-11-01。交付用户指定的 akan、tidak、kita、apa、kamu、itu、untuk、ada、boleh、mereka，顺序不变。总文件 `data/enriched/batch_2.json` 为数组，各 `data/enriched/<word>.json` 为对应单对象。

## 编辑约定

- 保留要求的七个顶层字段与全部嵌套字段，不添加来源键；逐义来源或编辑边界放入 `ms_definition`、`nuances`，详细依据见本页。
- `frequency_rank` 取本地 `raw/opensubtitles_frequency_ms_full.txt` 的行序 11–20，与 `data/pilot_50_candidates.json` 交叉核对；这是字幕语料排名，不是官方综合词频。[语料上游及数据许可](https://github.com/hermitdave/FrequencyWords/blob/master/content/2018/ms/ms_full.txt) 另见 `data/audit/README.md`。
- 全部正式与口语例句、中英文翻译为本批新编编辑内容，未声称逐字取自 Tatoeba、报刊或私人聊天。formal 表示规范书面表达；kamu 的正式场景专门限定为教师对学生，不暗示学生也适合这样称呼教师。
- 42 个义项、20 个场景。并非每个词族项都属于能产派生：重叠、代词附着形式、疑问和强调附着词各有明示；无派生词族可用空数组，基本词用 `∅ + word → word`。

## Jawi、音节与 IPA

用户消息中的问号是传输乱码，不予照抄。优先读取本工程 UTF-8 缓存，未改写原始缓存。

| word | Jawi | syllables | 核验依据 |
| --- | --- | --- | --- |
| akan | اکن | a.kan | Jawi 经下列 DBP 拼写答复确认；本地 Kaikki `[a.kan]` 提供分音依据，非宣称已取得 DBP 单词头音节栏 |
| tidak | تيدق | ti.dak | 缓存 Jawi 原样保留；缓存 `[ti.daʔ]` 是发音标注，按 Rumi 正字法分节 |
| kita | کيت | ki.ta | 缓存 Jawi、syllables 原样保留 |
| apa | اڤ | a.pa | 缓存 Jawi、syllables 原样保留 |
| kamu | کامو | ka.mu | 缓存 Jawi、syllables 原样保留 |
| itu | ايت | i.tu | DBP Daftar Rumi-Jawi，直接显示此词与分节，见下方入口 |
| untuk | اونتوق | un.tuk | 缓存 Jawi 原样保留；`[un.tuʔ]` 的 Rumi 正字法分节 |
| ada | اد | a.da | 本地 Kaikki Jawi；DBP `berada-ada` 的独立重叠成分及 UPM 原始研究表格交叉确认；a.da 按本地 Kaikki 发音分节，非 DBP 单词头分节原文 |
| boleh | بوليه | bo.léh | 缓存 Jawi 原样保留；从缓存定义头 `[bo.léh]` 提取并保留 é |
| mereka | مريک | me.ré.ka | 缓存 Jawi 原样保留；从代词定义头 `[me.ré.ka]` 提取并保留 é |

在线实际取得的依据：

- [DBP 关于 AKAN DIBUKA 的拼写答复](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=akan+1)：答复中包含 `اکن دبوک`，确认 akan 的 اکن；不是从其他词族词强行反推。
- [DBP itu 的 Daftar Rumi-Jawi](https://prpm.dbp.gov.my/cari1?keyword=%D8%A7%D9%8A%D8%AA)：明确对应 itu、i.tu、ايت。不能用带附着词的 itulah 拼写来猜写独立 itu。
- [DBP berada-ada](https://prpm.dbp.gov.my/Cari1?d=226380&keyword=berada-ada)：显示 `براد-اد`；此证据是词族重叠成分，不冒充 ada 独立词头。
- [UPM《Mahawangsa》原始研究，2016，Jadual 2](https://fbmk.upm.edu.my/upload/dokumen/20171114164313MAHAWANGSA_VOL_3_2NOVEMBER_2016.pdf)：表中 ada 对应 اد。为研究交叉佐证，不冒称 DBP 授权的新词典。

IPA 取本地 `raw/kaikki_malay.jsonl` 的未损坏记录。kita、apa、ada、代词 mereka 采用半岛南部常见词尾 /ə/，另在说明保留 /a/ 变体；untuk 采用文读发音的宽式音值 `[ˈʔun.tuʔ]`，省去原标注中可预测的齿化细节，并非宣称所有地方都读该元音（南部亦有 `[ˈʔun.toʔ]`）。tidak 用实际词尾喉塞音；boleh 保留 `[bo.leh]`。这些不是 DBP 官方 IPA。

## 释义与事实边界

- akan：从 [DBP pada waktu itu 的交叉检索](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=pada+waktu+itu) 取得完整 Kamus Dewan 第四版关联词条，并经 [disuntik 交叉结果](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=disuntik) 复核。四个核心义为预期事件、感情或认知对象、文学受益者、文学话题。较长释义用标注 `Olahan berdasarkan...` 的简明改述；短义用小段摘录。固定转折 [akan tetapi](https://prpm.dbp.gov.my/Cari1?d=82736&keyword=akan+tetapi.) 另列且明确属于整体表达。
- itu：核心释义依据 [DBP macam itu 交叉检索的 Kamus Dewan 词条](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=macam+itu)。第二义为该指示词的已知话题指回功能，标为用法改述，没有冒充另一个逐字官方编号义项。
- ada：从 [DBP keberadaan 交叉结果](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=keberadaan) 及 [berada-ada 的交叉词条](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=berada-ada) 补到 Kamus Dewan 第四版八个原义。将存在和已有事情待处理合并，其余涵盖所在、拥有、健在、动作确认、点名应答、柔化提问；较长定义均明示改述。未把 Kaikki 限定为 creole Malay 的进行体义推广为大马规范语法，也不把 ada 一律等同于完成标记 sudah。
- kamu、untuk：所给缓存含 Kamus Dewan 第四版，采用摘录或去除排版断字后分义。untuk 的持续时段义为 Kaikki 编辑补充，指出纯时长使用 selama 更清楚。
- tidak、kita、apa、boleh、mereka：本批已有正式定义来自 **Kamus Pelajar Edisi Kedua**，逐义明确注明，不因用户模板的字段提示而伪称 Kamus Dewan 原文。额外的句法用法和 Kaikki 义项都标为编辑释义。
- kita 的 informal 排除听者义，以及文莱／古语第二人称义只作有标签的识别，不替代大马规范的 kita／kami 区分。亲近场景的单数自称我有 DBP 依据，不以性别作硬性限制。
- apa 保留原完整本地记录的疑问、嵌入、惊讶／复问、是否问句、停顿与少见选择连接用法；原 packet 截断的前八个 gloss 不能替代完整词条。Schema 无 interjection 或 auxiliary 枚举，分别以 particle 或 verb 承载并说明。
- boleh 获得义按 Kaikki 标注为 obsolete；现代主动使用的核心仍为能力／许可。
- mereka 的代词词位为基本词；同形动词属于 `meN- (me-) + reka → mereka`，分列三个动词义，并在 morphology、词源同时限定范围。原缓存第三个“野生动物”条目与未重读的元音、来源关系不清，本批不把它合成同一个代词的新义，留待准确词头核验。

## 缩写筛选与词源

- Malaya 规则只是候选表。本批排除英语 isn't／what／for／have／add／that／those，亦不把印尼 nggak／enggak、bisa 的 bsa 等当作大马常用的直接缩写。
- kau 来自 engkau，不是 kamu 的直接缩短；lu、hang 等是各有语域的替代词。diorang 是 dia orang 的压缩，不是 mereka 的字母缩写。depa 仅标北部方言。
- [DBP 北部方言 apa、hampa／hangpa 结果](https://prpm.dbp.gov.my/Cari1?d=150348&keyword=kamu+) 与 [hampa 的复数实例](https://prpm.dbp.gov.my/Cari1?d=226380&keyword=ham) 确认 hampa／hangpa 属第二人称，不能按材料映射成 mereka。
- `-mu` 为代词附着形式，明确它也可见于规范文本；takkan、xde、takde 的 full_form 给出整个组合，避免错误展开成单个 akan／ada。
- 词源依本地 Kaikki，回溯入口为 `https://en.wiktionary.org/wiki/<word>#Malay`。重建形式保留 *；不沿用未独立核验的首见碑文年代。untuk 词源未知、代词 mereka 词源未知；“替代 *sida”不等于“源自 *sida”。boleh 的历史重建带来源与不确定性，不把整段重建当现代构词规则。

第三方文本和数据署名、适用许可见 `data/audit/README.md`，Kaikki／Wiktionary 文本沿其适用的署名与共享许可处理；不把本批使用来源等同于本工程拥有全部来源的排他权。未调用付费外部 API。

## 验证与交付状态

验证记录：`data/audit/batch_2_verification.json`。检查严格 UTF-8、重复键、七维及全部嵌套结构、枚举和类型、词序与义项编号、双场景、中文与阿拉伯文字、缓存 Jawi／音节保真、字幕词频、批次与单词文件一致性，并保存交付文件 SHA-256。

语言内容已作编辑自查，不宣称通过独立词典专家认证；未知词源和混入的野生动物条目如上明示。未修改 Batch 1，未运行下一批或改变合成管线。工程没有本次需要重载的应用服务；本次验收对象为实际落盘 JSON。宿主将 `.git` 设为只读，沿用现有状态说明，不尝试修改分支或提交未确认许可的原始素材。
