# 本地素材审计产物

由 `python src/benchmark_audit.py` 生成；不联网，不改写 `raw/`。输入字节数、SHA-256、下载脚本声明的 URL、运行环境及完整分母见 `audit_metrics.json`。上游 URL 使用浮动分支，不证明本地文件的抓取日期或上游修订。后续若输入哈希变化，必须重跑并更新报告。

| 文件 | 用途 |
| --- | --- |
| `audit_metrics.json` | 全量量化结论，比例同时保存分子、分母、百分数 |
| `frequency_matches.csv` | 保留全部源顺序、词形、频次及各词典/字段命中 |
| `top15000_missing_both.csv` | Top 15,000 中同时缺于 DBP 镜像和 Kaikki 的 5,240 项 |
| `colloquial_candidates.csv` | 51 项封闭候选表的命中、歧义、可能展开及词典命中，不是上下文标注 |
| `kaikki_probes.json` | 10 个指定词形的原始记录切片，供复核构词、语域和例文 |
| `conversation_checks.json` | 补充事实审查：英文工程源文件哈希、资产计数、两种 Node 命令的真实结果，由 `src/audit_conversation_claims.py` 生成 |
| `full_conversation_evidence.json` | 全会话审计：导出缺口、Step≤987 历史返回、候选/缓存重计、来源交集、时窗速率和离线解析复现，由 `src/audit_full_conversation.py` 生成；可选的当前 IP 探测失败不代表历史出口未知 |

词频来源：[Hermit Dave / FrequencyWords](https://github.com/hermitdave/FrequencyWords)，`content/2018/ms/`，基于 OpenSubtitles2018。维护者将数据内容标为 **CC BY-SA 4.0**（代码 MIT 不覆盖数据）；词频 CSV 是添加命中列的派生分析，不应把它当本项目独占的原创词频。

词典切片：[Kaikki Malay](https://kaikki.org/dictionary/Malay/index.html)，基于 English Wiktionary，经 wiktextract 提取。`kaikki_probes.json` 保留原字段及义项 ID；词头原页面可按 `https://en.wiktionary.org/wiki/<URL编码词头>#Malay` 回溯。按 [Wikimedia 重用条款](https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use#7._Licensing_of_Content)保留文本署名及适用许可；采用 CC BY-SA 路线处理这些文本切片，音频引用不等于拥有录音许可，也未随此目录复制录音。原始切片未改写释义；重新组织为按目标词形索引的 JSON。

Parquet 声明来源与补充来源核验见 `docs/SOURCE_RESEARCH.md`。DBP 镜像只用于本地词形交集测量，本目录未重发其完整词表，也未宣称它是 DBP 授权发布物。本工程整体代码/原创内容许可证尚未确定；不得将第三方文本、词频和音频一并默认改为 MIT。
