# Batch 3 词条交付与来源说明

日期：2026-11-01。本批顺序为 dengan、anda、tahu、ke、kami、ya、dari、dalam、sini、semua。交付 `data/enriched/batch_3.json` 数组与十个同名 JSON 单对象，共 57 义项、20 场景；七维字段保持用户指定结构。

## 编辑与数据约定

- `frequency_rank` 按本地 `raw/opensubtitles_frequency_ms_full.txt` 行序取 21–30，并与 `data/pilot_50_candidates.json` 核对。这是字幕语料排名，不是 DBP 官方综合词频。
- 场景、中文／英文释义与译文为本批编辑内容；未声称逐字引自新闻、Tatoeba 或私人聊天。正式场景表示规范马来语，口语场景注明人物关系与省音。
- `ms_definition` 中 DBP 短释义保留来源名称；较长释义压缩时明确用 `Olahan berdasarkan…`，Kaikki 补充义用 `Huraian editorial berdasarkan Kaikki…`。不用编辑改述冒充逐字 Kamus Dewan 原文；ke 的方向义实际取自 Kamus Pelajar。
- 十个主词位都是现代基本词，公式为 `∅ + word → word`。词族中的代词附着、重叠和词汇组合均有标签；没有可靠派生时允许空词族。anda、semua 的 `loanword` 指词源，二者都是规范可用词。
- Schema 不提供 interjection／determiner／kata bilangan：感叹／呼告与疑问用 particle，semua 的名词前限定功能用 adjective，句中总括功能用 adverb，并在相应义项注明映射。它们不是声称 DBP 给出了这些英语标签。

## Jawi、音节和 IPA

用户消息的问号已损坏，实际从本工程 UTF-8 缓存恢复；原始素材未改写。

| word | Jawi | syllables | 依据 |
| --- | --- | --- | --- |
| dengan | دڠن | de.ngan | 本地 PRPM 两字段原样保留，并见在线词条 |
| anda | اندا | an.da | 本地 PRPM 原样保留，选用代词定义，避免误取首个 anda musang |
| tahu | تاهو | ta.hu | 本地 PRPM 原样保留 |
| ke | ک | ke | Jawi 来自本地 Kaikki 介词记录；单音节为编辑分节，未取得独立 DBP 介词 Jawi 栏 |
| kami | کامي | ka.mi | 本地 PRPM 原样保留 |
| ya | ياء | ya | 缓存 Jawi 原样保留，并在线确认；单音节为编辑分节 |
| dari | دري | da.ri | 本地 PRPM 原样保留 |
| dalam | دالم | da.lam | 在线 DBP 词条明确显示；原缓存抓取失败不等于 DBP 未收录 |
| sini | سيني | si.ni | 本地 PRPM 原样保留 |
| semua | سموا | se.mua | 本地 PRPM 原样保留，不按另一套音节分析擅改 |

IPA 依据本地 `raw/kaikki_malay.jsonl`，不是 DBP 官方 IPA。ke 采用 /kə/，去除原记录在单音节上的重音标记；字母名 ké 的 /ke/ 另在义项说明。anda 采用宽式 /ˈanda/，起首可有 [ʔ]。semua 采用半岛常见 /səˈmuə/，保留文读 /səmua/ 变体说明；正字分节仍用 PRPM 的 se.mua。ya 取 [ja]，口语亦有 [jə]。未把 Kaikki 的 dalam 方言 [dalẽ] 当成全马统一读音。

## 本批补查的一手来源

- [DBP dengan 词条](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=dengan)：在线结果与本地缓存的 de.ngan、دڠن 及主要介词义相符。古典朋友／奴仆／我三义直接依据本地独立同形词定义。
- [DBP ya 词条](https://prpm.dbp.gov.my/Cari1?d=72508&keyword=ya)：页面对多个 ya 同形词均显示 ياء；不因本地 Kaikki 写作 يا 就改写 PRPM。大写职衔缩略语 YA = Yang Arif 与普通 ya 分开说明。
- [DBP dalam 词条](https://prpm.dbp.gov.my/Cari1?d=132444&keyword=dalam)：检索结果显示 da.lam、دالم 及 Kamus Dewan／Kamus Pelajar 的深、内部、范围、时间等义。直接打开部分 PRPM 地址遇超时，但官方域名的索引结果成功返回；未宣称直连全部页面成功。
- [DBP ke 的 Kamus Pelajar 交叉词条](https://prpm.dbp.gov.my/Cari1?d=73980&keyword=imbuhan)：方向介词义与词缀 ke- 同列，已区分独立介词、序数／名词前缀；不把整个 ke 词头设成派生词。
- [DBP ke 用法答复](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=ke)：地点、方向与时间用法，以及 ke dalam 的空间表达。
- [DBP ke／kepada、dari／daripada 的答复](https://prpm.dbp.gov.my/Cari1?d=175768&keyword=borang+II)：人的来源、材质、比较通常用 daripada；从时间地点方向出发用 dari，并有 dari sudut 的角度用法。
- [DBP dalam／di dalam 用法答复](https://kndbp.dbp.gov.my/soalanlazim/nb_soalan_lazim.aspx?ctl00_contentPlaceHolder_dgCarianBaruChangePage=2078_20)：抽象范围用 dalam，明确物理空间中的位置用 di dalam。

检索所得资料只作为所述字段的依据；例如 DBP kaf 答复中的序数 `ک-9` 不冒充独立介词 ke 的 Jawi 词头证据。

## 易混点、词源和缩写筛选

- dengan：分清陪伴、工具、方式、冲突、原因、适配、结果、对象、口语 pada 等义；Kaikki 连接与附带条件功能单独注明编辑来源。古典名词／代词同形义不当成现代常用表达，词源不强行合并。
- anda：主词位选现代受众代词；不能因 raw packet 的首条是 anda musang 就写成麝香囊为主定义。该罕见名词仅限定于组合。现代代词的印尼语来源依本地 Kaikki，未独立核定创制人及日期，不复述其具体年代。
- tahu：保留知晓、认识、会做、关心、觉察、经历、理所当然等 DBP 义及独立鸟名；鸟名旧学名只按原文标识，不宣称已核对现行鸟类分类。mengetahui／pengetahuan 是特殊构形，不推导不存在的 *menahui；beritahu 为词汇组合。印尼语豆腐义不混入大马 tahu 核心。
- ke：方向与时间介词、口语问句／选择功能、异音字母名 ké 分开。ka 只标部分地区的疑问形式，不说它是方向介词缩写。词头 IPA、Jawi、基本构词取主介词，不覆盖字母名所有元数据。
- kami：明确排除听者；旧文单数作者自称另列。kitorang 通常是口语 kita orang 的压缩表达，可对应 kami，不伪称从 kami 字母缩写而来。
- ya：肯定、答应、应声、句尾确认、阿拉伯语呼告、字母名分清。肯定词源各假说未定，不择一写成事实；阿拉伯语来源只归呼告及字母名。不沿用材料里互相冲突的碑文日期。
- dari：较早来源未核实，材料只给历史见证，不补造祖语词根或确定的最早年份。比较句改用 daripada；不会把原例句的口语比较误用当正式规范。
- dalam：特别区分深度形容词、空间方位名词、范围介词和宫廷旧义；dalaman、pedalaman、pendalaman 分别为内部相关、内陆、加深过程，不混同派生规则。
- sini：普通方位义、简短呼唤、少见自称分开。旧式自称在 DBP 标 bp、Kaikki 标 obsolete，保留标签差别，不推荐作现代通用我。cini 只标卖萌聊天写法。
- semua：保留 DBP se.mua，现代不作 se- + mua 伪拆。量词限定、代指整体、谓语总括分义；提醒 kami semua 与 kita semua 的听者范围不同。

原 Malaya 规则只作候选，不把英语 by／with／deep／all／everything 合成马来语缩写；ya 的 yah／yha／yakk 等缺乏足够语境且易混，未收作通用形式。tw、cini 等有歧义或特殊语气者明示限制。未声称提供各缩写的量化使用频率。

Kaikki 词源回溯入口可按 [Wiktionary Malay](https://en.wiktionary.org/wiki/dengan#Malay) 更换词头查看；本批实际依据为本地未损坏的记录，不宣称重新查实所有历史研究。重建形式保留 *，记忆法注明为联想，不伪装成历史派生。原始词频与 Kaikki／Wiktionary 的署名及适用许可沿用 [data/audit/README.md](../data/audit/README.md)；本批不是第三方数据的排他授权声明。

## 验证

运行 `python data/audit/batch_3_checks.py`。结果保存为 `data/audit/batch_3_verification.json`，核对严格 UTF-8、重复键、完整七维及嵌套字段、类型、枚举、词序、义项编号、场景、词频、缓存拼写、单词对象与批次一致性、重点混淆项，并记录 11 个文件的 SHA-256。前两批 22 个交付文件逐一按既有验收哈希核对。

语言已作编辑自查；结构检查不等于独立词典专家认证。本轮未改生产管线、前两批词条、原始缓存或网站；验收对象是实际 JSON 文件，不涉及应用服务重载。`.git` 仍为宿主只读，未提交或改动分支。未调用付费外部 API，也未自动开始下一批。
