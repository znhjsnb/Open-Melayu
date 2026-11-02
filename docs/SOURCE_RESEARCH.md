# Open-Melayu 独立一手来源研究

核验日期：2026-11-01。供主线程综合；未改变模型、未调用收费 API、未读取或重算本地词库、未修改代码或提交 Git。下列 **11 项资源本研究均未在本地实测**；主线程提供的测量结果另行标注。“已核实”仅指在线 README、许可、目录或注明的远端样例。作者声明数量不是本项目测量值；页面/API 可访问也不等于数据可以重新发布。

## 应先纠正的口径

- `entries-ms.parquet` 属于 Kaikki 词典条目；`wordnet-ms.parquet` 才属于 Wordnet。两者不是同一批“Wordnet 节点”。主线程已确认 Wordnet 是 **lemma–synset 对应表，role 只有 lemma**，不能称为已包含上下位关系的网络；见第 2 项。
- Wiktionary 文本、Commons 音频、Tatoeba 句子与音频应分别记录许可；不能给所有素材统一套 MIT。Kaikki HF README 所称必须同时遵守两种文本许可，与 Wikimedia 官方允许选择其一的说明不一致，见第 1 项。
- 可优先试接：Wordnet Bahasa MIT 数据、malaytextr 词形映射、Malaya MIT 规则、带署名与许可的 Wiktionary/Tatoeba/Commons 内容。抓取型 peribahasa 与 malay-dataset 语料尚不能列为“确认可重发”；Mozilla 当前下载页也有额外限制。

## 1. HF：miserableface/kaikki-melayu-entries

**公开可取；文本有开放许可。** 已读取[固定版本 README](https://huggingface.co/datasets/miserableface/kaikki-melayu-entries/blob/c8a4ca496502e76c5de947fdf8eb18e2966844c3/README.md)与[HF 元数据 API](https://huggingface.co/api/datasets/miserableface/kaikki-melayu-entries)。

- 卡片声明共 55,997 行，Malay 17,485、Indonesian 38,512；来源为 English Wiktionary 经 wiktextract/Kaikki 再轻加工为 Parquet。声明抽取日 **2026-10-27**、enwiktionary dump **2026-10-01**；卡片 `kaikki.org snapshot:` 一栏留空，未提供不可变上游快照。HF 修订 `c8a4ca496502e76c5de947fdf8eb18e2966844c3`。
- [马来语文件](https://huggingface.co/datasets/miserableface/kaikki-melayu-entries/resolve/c8a4ca496502e76c5de947fdf8eb18e2966844c3/entries-ms.parquet)：按 `lang=ms` 处理；不要混入印尼语文件。字段包括 `word/pos/ipa/glosses/tags/topics/forms/audio_urls/etymology_text/wikt_url/source`。`glosses` 将各义项英文释义汇集为列表；卡片未列独立 `examples` 字段，因此不能视为完整保留原始 sense 结构的版本。
- `entry_id` 声明由 `sha1(word\tpos)` 截取 16 位十六进制生成。**推论**：跨语言合并时这个设计不能单独保证唯一，须保留 `lang`；是否实际碰撞留给主线程实测。
- 许可元数据为 **CC BY-SA 4.0**，正文另写 CC BY-SA 4.0/GFDL 双许可并称两者都须遵守。应以[Wikimedia 官方条款第 7 节](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content)为准：重用者可遵守其中一种或两种；采用 CC BY-SA 路线时保留来源/署名、许可、修改说明并处理衍生文本的相同方式共享要求。外引材料、音频仍需另外核权。
- **主线程实测（主线程传入，非本研究重算）**：17,485 行、15,619 原词头 / 15,515 规范化词头；全部与本地 Kaikki 相同，无例句列且 `wikt_url` 全空。因此该 Parquet 不能视为新增覆盖；分发署名不可依靠空回链，应回溯原始 Wiktionary 页面与修订证据。主线程已处理上游后处理警告和不同 edition 区别，此处不重复。

## 2. HF：miserableface/melayu-wordnet 与 Wordnet Bahasa 上游

**公开可取；数据 MIT 已由上游确认。** [固定版本 HF README](https://huggingface.co/datasets/miserableface/melayu-wordnet/blob/060b8b1b04493fc0191b62c3d2e95b8d1aaf7c49/README.md)、[HF API](https://huggingface.co/api/datasets/miserableface/melayu-wordnet)、[上游目录](https://github.com/omwn/omw-data/tree/main/wns/msa)、[上游许可证](https://github.com/omwn/omw-data/blob/main/wns/msa/LICENSE)。

- HF 卡声明共 224,578 行，Malay 105,028、Indonesian 119,550；来自 OMW 打包的 Wordnet Bahasa，抽取日 **2026-10-28**。这是上传者的抽取日期声明，不是 Wordnet 创建日期或可验证的上游发布版本；卡片未固定 OMW commit。HF 修订 `060b8b1b04493fc0191b62c3d2e95b8d1aaf7c49`。
- [马来语 Parquet](https://huggingface.co/datasets/miserableface/melayu-wordnet/resolve/060b8b1b04493fc0191b62c3d2e95b8d1aaf7c49/wordnet-ms.parquet)字段为 `synset, word, lang, role, value`。卡片定义 `word` 只在 lemma 行填词形，其余为空；`role` 可为 lemma/definition/example/related/hypernym/hyponym/other，`value` 为释义、例句或指针载荷。**枚举这些 role 不证明每一类实际存在。**
- 已查看[上游 TSV 文件头与样例](https://raw.githubusercontent.com/omwn/omw-data/main/wns/msa/wn-data-zsm.tab)：`00001740-a\tzsm:lemma\tberdaya` 表示“词形 berdaya 被挂到此 synset”；同一 synset 会有多个 lemma 行，同一词形也可能对应多个 synset。`zsm:lemma` 不能当作释义或关系边。
- [上游 README](https://github.com/omwn/omw-data/blob/main/wns/msa/README)明确 `synset` 使用 **Princeton WordNet 3.0 的 offset-pos**。保留前导零、POS 与版本；不要把这个字符串直接当 CILI 的 ILI 标识，接 CILI 需另找映射。README 还解释较原始四列数据的 B/I/M 语言标签及 Y/O 等质量标记；不能把该四列格式误套到已标准化的 `wn-data-zsm.tab` 三列格式。
- 上游 LICENSE 明确把数据纳入 MIT，分发时保留版权与许可；引用 Noor、Sapuan、Bond（2011）及 OMW。英文 lemma 不在此 HF 包内，中文释义也不是该卡片承诺的字段。
- **主线程实测（主线程传入，非本研究重算）**：105,028 行、33,932 原词 / 33,903 规范化词、36,911 synset，role 只有 lemma。应据此称为词语–synset 对应表；卡片列出的 definition/example/hypernym 等只是通用 schema，不能当成本地已有内容。`word` 与 `value` 是否逐行相同仍由主线程确认。

## 3. Peribahasa：Wiktionary/Kaikki 的小规模开放种子

**文本开放；覆盖有限。** [Wiktionary Malay proverbs 分类](https://en.wiktionary.org/wiki/Category:Malay_proverbs)、[Kaikki proverb 页](https://kaikki.org/dictionary/Malay/pos-proverb/index.html)、[专项 JSONL](https://kaikki.org/dictionary/Malay/pos-proverb/kaikki.org-dictionary-Malay-by-pos-proverb.jsonl)。

本次直接读取 Kaikki HTML 显示 **39 个 proverb senses**，页面声明抽取于 **2026-10-30**、dump 为 **2026-10-01**；这是在线显示值，不是下载后计数，也不是 39 个独立成语的保证。提取专项 JSONL，保留词头、义项、标签与回链；或从完整 raw 中筛 `lang_code=ms`、`pos=proverb`。按第 1 项文本许可处理。可作种子，不能据此称已有完备成语专库；与现有 Kaikki 数据可能重复，增量待实测。

## 4. Peribahasa：Malaysia AI 抓取文件，仅列候选

**公开可取，重发许可未确认。** 维护者的[抓取说明](https://github.com/malaysia-ai/malaysian-dataset/blob/master/crawl/senaraiperibahasa.com/README.md)指向 [senaraiperibahasa.com.jsonl](https://huggingface.co/datasets/malaysia-ai/dedup-text-dataset/resolve/main/senaraiperibahasa.com.jsonl)；[数据卡](https://huggingface.co/datasets/malaysia-ai/dedup-text-dataset/blob/main/README.md)说明由志愿者爬取网站并去重，但未标明开放许可证。

已读取远端开头样例：其行内容为含标题、例句及含义的 **JSON 字符串网页文本**，并非整理好的 `proverb/meaning/example` 记录。若后续取得权利依据，再逐行解码、恢复表格关系并保留原网页证据。另一[维护者入口](https://github.com/malaysia-ai/malaysian-dataset/blob/master/crawl/maksudperibahasa/README.md)指向 [crawl-maksudperibahasa](https://huggingface.co/datasets/aisyahhrazak/crawl-maksudperibahasa)；HF API 可见 JSONL 文件，但无 README/数据卡许可。维护者发布抓取物只能证明获取途径，不能替被抓网站授予内容重发权。

## 5. Kata dasar：malaytextr 作者官方仓库的实际文件

**仓库 MIT；非 DBP 官方完整词根清单。** [作者仓库](https://github.com/zahiernasrudin/malaytextr)、[DESCRIPTION](https://github.com/zahiernasrudin/malaytextr/blob/master/DESCRIPTION)、[MIT](https://github.com/zahiernasrudin/malaytextr/blob/master/LICENSE.md)。

实际数据为 [data/malayrootwords.rda](https://github.com/zahiernasrudin/malaytextr/blob/master/data/malayrootwords.rda)，不是仓库根目录 CSV。README 展示 **4,310 行、两列 `Col Word` / `Root Word`**，如 `pengadilan → adil`；这是作者文档值，尚未解包重数。[准备脚本](https://github.com/zahiernasrudin/malaytextr/blob/master/data-raw/malayrootwords.R)读作者本机 CSV，原 CSV 并未随该路径公开，不能声称来源链或重建过程完整。README 提到开发版于 2023-03-09 增词，这也不等于本地文件日期。

提取方法：后续用 R `load()` 读 `.rda`，或安装包后 `data("malayrootwords", package="malaytextr")`，按两列导出 UTF-8。其内容是词形→词根候选映射，不自带词缀拆分步骤或教学公式。另有 [data/normalized.rda](https://github.com/zahiernasrudin/malaytextr/blob/master/data/normalized.rda)，README 展示 153 行缩写规范化映射，可作小种子；数量、准确率与上游采集依据均待本地核验。

## 6. Malay normalize/slang：Malaya 规则代码

**代码与内嵌规则 MIT；优先于许可不清的抓取语料。** [官方规则文件](https://github.com/malaysia-ai/malaya/blob/master/malaya/text/rules.py)、[normalizer 实现](https://github.com/malaysia-ai/malaya/blob/master/malaya/normalizer/rules.py)、[MIT](https://github.com/malaysia-ai/malaya/blob/master/LICENSE)、[官方用法文档](https://malaya.readthedocs.io/en/stable/load-normalizer.html)。

已在 `rules_normalizer` 中核到 `tak→tidak`、`xde→tidak ada`、`diorang→mereka`、`dkt→dekat`、`sbb→sebab`。可提取显式映射，保留原词形和语域；有歧义时不强制单一替换。当前源码入口为 `malaya.normalizer.rules.load()`；[旧入口源码](https://github.com/malaysia-ai/malaya/blob/master/malaya/normalize.py)已将 `malaya.normalize.normalizer()` 标为 deprecated。只核读了代码，未安装、执行 normalizer 或下载模型；MIT 代码不能自动覆盖其外部模型与语料的许可。

## 7. Malay normalize：malay-dataset 后继仓库

**公开训练样例；许可/使用条件不足以确认开放重发。** 原 huseinzol05/malay-dataset 现对应 [malaysia-ai/malaysian-dataset](https://github.com/malaysia-ai/malaysian-dataset)。[实际 normalized.json](https://github.com/malaysia-ai/malaysian-dataset/blob/master/normalization/normalize/normalized.json)在线开头是 `[原句,规范化句]` 数组对，混合缩写、日期、时间、金额和数字转换，不能直接当俚语词典。

另有 [Twitter normalization README](https://github.com/malaysia-ai/malaysian-dataset/blob/master/normalization/twitter/README.md)，说明用 Malaya 词典规则规范化 Twitter，给出[外部下载 URL](https://f000.backblazeb2.com/file/malay-dataset/normalization/twitter/normalized.json)；**该外部对象未实测**。实际提取应区分合成规范化对与社交媒体原句，标记机器处理来源。[当前根 README](https://github.com/malaysia-ai/malaysian-dataset/blob/master/README.rst)要求分发前先联系，并设 Non-commercial Usage 说明；没有支持把全库统一认定为 CC BY 4.0。不能沿用旧 fork 的宽泛许可描述，亦不能沿用 Malaya 代码的 MIT。

## 8. MS–EN / MS–ZH 例句：Tatoeba 官方导出

**文本可按许可重用；三语覆盖尚未统计。** [下载与字段说明](https://tatoeba.org/en/downloads)、[马来语目录](https://downloads.tatoeba.org/exports/per_language/zsm/)。**Tatoeba 此处代码是 `zsm`，普通话是 `cmn`，英语是 `eng`，不能直接用 `ms` / `zh` 拼路径。**

已核到目录文件（显示更新于 2026-10-31）：[zsm 详细句子](https://downloads.tatoeba.org/exports/per_language/zsm/zsm_sentences_detailed.tsv.bz2)、[zsm-eng 关系](https://downloads.tatoeba.org/exports/per_language/zsm/zsm-eng_links.tsv.bz2)、[zsm-cmn 关系](https://downloads.tatoeba.org/exports/per_language/zsm/zsm-cmn_links.tsv.bz2)。配合 eng/cmn 句子导出，以 sentence ID 连接；只把直接关系称为直接翻译，通过英语绕接中文应另标“间接对齐”。同一 zsm ID 同时存在两种直接关系才可候选三语组，质量与数量待实测。

官方导出通常为 **CC BY 2.0 FR**，部分另有 CC0 导出；保留句子 ID、作者、回链、许可及修改说明。音频另看 `sentences_with_audio` 的逐条许可，空许可不可外用；句子文本许可不覆盖录音。未下载或计算语料覆盖率。

## 9. 单词真人发音：Wikimedia Commons

**媒体逐文件开放许可；可以核到具体样例。** [Malay pronunciation 分类](https://commons.wikimedia.org/wiki/Category:Malay_pronunciation)、[kucing 文件页](https://commons.wikimedia.org/wiki/File:Ms-MY-kucing.ogg)。已调用[该文件 imageinfo API](https://commons.wikimedia.org/w/api.php?action=query&titles=File%3AMs-MY-kucing.ogg&prop=imageinfo&iiprop=url%7Cextmetadata&format=json)：作者 **PeaceSearcher**、录制日期 **2021-05-29**、说明为马来西亚 Bangi 男声、许可 **CC BY-SA 4.0**。没有试听，不能据此保证发音质量。

提取方法：按[categorymembers API](https://www.mediawiki.org/wiki/API:Categorymembers)枚举分类及必要子分类，处理续页；再按 [imageinfo](https://www.mediawiki.org/wiki/API:Imageinfo)取 `url|extmetadata`，保存 `Artist/LicenseShortName/LicenseUrl/AttributionRequired`、文件页与版本证据。可从 Kaikki `audio_urls` 反查 Commons。不能只存 CDN 链接或把某个样例许可推广到全分类；词头对应与方言适用性仍待实测。

## 10. Mozilla Common Voice 马来语语音

**标 CC0，但当前分发入口有额外限制；不纳入可直接重发音频。** [官方 Common Voice 27.0 Malay 数据页](https://mozilladatacollective.com/datasets/cmu617r0400jjo1072jneryvg)（旧 datacollective.mozillafoundation.org 现重定向至该站）。

数据页标 **CC0-1.0**、`cv-corpus-27.0-2026-09-11`、发布日 **2026-09-17**、MP3 归档。官方声称 2,362 clips / 4.05 小时，其中 validated 仅 0.22 小时；这些都是数据卡值，未下载复核。其 **Forbidden Usage 同时禁止识别说话人、重新托管或分享数据集**，不能只根据 CC0 标签承诺任意重发；本次不接受下载条款或下载归档。

后续若明确取得适合本项目的使用条件，可从官方页面取得版本归档，依据随包元数据将 MP3 与转录对齐，并优先评估 validated 子集，具体字段待实测。它是朗读句子/ASR 资源，不能直接视为按词头切好的词典发音库。当前重发限制与应用内音频供应范围的关系尚未澄清。

## 交接边界

DBP 非官方 HF 镜像、FrequencyWords 许可、Kaikki 后处理警告与 edition 区别由主线程已核，本报告不重复调查，也不把 DBP 网页视为可重发数据。主线程提供的本地事实只在上方明确标注处引用；其余数量仍是发布者文档或在线页面声明。

仍未验证：本地文件是否等于所列 HF 修订；上游确切 OMW commit/Kaikki 不可变快照；词根映射质量、Tatoeba 直接三语覆盖及音频覆盖。本研究未执行这些检查。接入时宜逐条保留 `source_url/source_revision/retrieved_at/license/attribution`，把许可未确认的候选与可分发数据分开记录。

## 11. 补充：Malay Lexicon Project 2（MLP2）构词研究数据

**作者发布，数据许可明确为 CC BY 4.0；可用于构词候选及版本化评测参考。** [官方论文页](https://link.springer.com/article/10.3758/s13421-022-01337-8)确认作者为 Mirrah Maziyah Mohamed、Melvin J. Yap、Qian Wen Chee、Debra Jared；2022-06-15 在线发表，正式卷期为 2023 年。作者的 [Mendeley Data v2](https://data.mendeley.com/datasets/9sw6vyfw29/2) 发布于 **2023-08-25**，DOI **10.17632/9sw6vyfw29.2**，明确标注 CC BY 4.0。近 10,000 词是其扩充的原 MLP 规模描述，并非新增近万词或本地实测数量。

- **真实文件入口已核实**：[v2 文件清单 API](https://data.mendeley.com/public-api/datasets/9sw6vyfw29/files?folder_id=root&version=2)列出 [MLP2_Engupdated2.csv 更新版直链](https://data.mendeley.com/public-files/datasets/9sw6vyfw29/files/1f9ca0b4-795c-48bd-ba95-79f902c3e179/file_downloaded)、[MLP2_Eng.csv 原版直链](https://data.mendeley.com/public-files/datasets/9sw6vyfw29/files/928b3472-8a04-45c4-8662-fbfc27b6ded1/file_downloaded)、[readme_MLP2_updated.txt](https://data.mendeley.com/public-files/datasets/9sw6vyfw29/files/58f69b0a-e923-49ea-99ed-aa9048137d02/file_downloaded)。更新版 CSV 的 HEAD 返回 200，大小 4,000,254 字节；**未下载 CSV 或整库**，只读元数据及约 5 KB README。网页虽称更新“Available on OSF”，本次已在 Mendeley 实际清单找到更新文件，无须依赖尚未确认的 OSF 地址。
- **适用性**：README 明列 `Word / Root word`、前后缀数量与身份、前缀 morpheme / allomorph 身份、词根家族规模及词缀生产力等字段。建议优先评估它作为词根、词缀与表层异形的候选依据，并建立保留该版本来源的分解对照基准；若用于训练，评测须另留独立样本。具体拼接规则、覆盖率、标注准确性及逐词审定流程本次未验证，不能直接称作已验收的构词金标准。
- **许可与提取边界**：[仓库许可元数据](https://data.mendeley.com/public-api/datasets/9sw6vyfw29)明确允许署名条件下分享、修改；保留作者、数据 DOI、CC BY 4.0 链接及修改说明，对另标第三方权利的内容分别核查。后续可按更新版 CSV 与 README 映射上述字段，再人工核查构词候选；实验反应时不能直接当学习难度。文件实际行数、字段完整性及与本项目词头交集均 **本地未实测**。
