# Open-Melayu 15K

[![Headwords: 15,000](https://img.shields.io/badge/Headwords-15%2C000-blue)](#数据与来源诚实)
[![8-Dim Enriched: 14,748](https://img.shields.io/badge/8--Dim_Enriched-14%2C748-success)](docs/SCHEMA.md)
[![Trilingual: MS · ZH · EN](https://img.shields.io/badge/Trilingual-MS%20%C2%B7%20ZH%20%C2%B7%20EN-orange)](#八维词条架构8-dimension-schema)
[![Script: Rumi + Jawi (RTL)](https://img.shields.io/badge/Script-Rumi%20%2B%20Jawi%20%28RTL%29-teal)](docs/SCHEMA.md)
[![License: CC-BY-SA-4.0 | MIT](https://img.shields.io/badge/License-CC--BY--SA--4.0%20%7C%20MIT-purple)](LICENSE)
[![Architecture: Zero-Compute Web Worker + IndexedDB](https://img.shields.io/badge/Architecture-Zero--Compute_Web_Worker%20%2B%20IndexedDB-555)](#词典工作台)

面向马来语学习者的开源马来语—中文—英文认知词典：15,000 个候选词头，14,748 个八维精编词条，Rumi 拉丁字母与 Jawi 爪夷文并存。

仓库：[znhjsnb/Open-Melayu](https://github.com/znhjsnb/Open-Melayu)。[快速启动](#快速启动quick-start) · [字段契约](docs/SCHEMA.md) · [当前状态](START.md) · [工作台验收记录](docs/WORKBENCH_IMPLEMENTATION.md)

## 为什么选择 Open-Melayu 15K？

PRPM 与 DBP《Kamus Dewan》《Kamus Pelajar》提供重要的马来语词典依据。Open-Melayu 在保留来源区分的基础上，增加中英解释、现代构词公式、搭配和社交礼仪，帮助学习者把词义放回实际使用场景。

同一词条并列展示 Berita / Dokumen 正式语体与 WhatsApp / Bahasa Pasar 日常口语，提供口语写法、标准语还原和双人对话。Rumi 与局部 RTL 的 Jawi 同屏呈现；缺少可靠 Jawi 的词条保留空值，不生成伪造拼写。项目是独立编辑的学习资源，并非 DBP 官方词典或其完整镜像。

## 数据与来源诚实

当前数据版本：`om-20261103-v9756`。统计以 [manifest.json](app/static/data/manifest.json) 和全库质量门禁为准。

| 数据状态 | 数量 | 含义 |
| --- | ---: | --- |
| `enriched` | 14,748（98.32%） | 完成八维精编 |
| `source_only` | 0 | 已有来源、尚未精编的兼容状态 |
| `missing_source` | 252（1.68%） | 保留候选词头与位序，来源或内容待补 |
| 合计 | **15,000** | 三态互斥；不宣称 15,000 词全部精编 |

### 四档来源标识（Four-Tier Provenance Honesty）

| 页面标签 | 判断条件 | 来源含义 |
| --- | --- | --- |
| `DBP 原文:` | `headword.status = official` 且 `senses[].ms_is_verbatim = true` | 通过本地 Kamus Dewan / Kamus Pelajar 原文连续子串核验的直接引文 |
| `马来语释义 (基于 DBP 官方词条):` | `official`，但不是已核验直接引文 | 编辑基于官方词条归纳的释义 |
| `马来语释义 (基于 DBP 词根推导):` | `root_derived` | 根据官方词根及构词关系编写 |
| `马来语释义 (字幕高频语料用法):` | `corpus_usage` | 字幕语料用法、借词或专名等编辑释义 |

14,748 个精编词头的来源分布为 `official` **7,479**、`root_derived` **2,328**、`corpus_usage` **4,941**。四档展示标签与三类词头来源是不同层级；中文、英文解释及例句不应被当成 DBP 原文。`missing_source` 保持待补状态，不充当第四类已精编来源。

## 八维词条架构（8-Dimension Schema）

八维由七个主容器承载：基础词头、构词、释义、义项内搭配、双境语料、口语速查、社交礼仪、词源与记忆。以下为从真实 `saya` 词条选取的 JSON 节选，数组仅展示部分内容；完整数据见 [saya.json](data/enriched/saya.json)、[datang.json](data/enriched/datang.json)，类型和约束见 [docs/SCHEMA.md](docs/SCHEMA.md)。

```json
{
  "headword": {"word": "saya", "syllables": "sa.ya", "ipa": "/ˈsajə/", "jawi": "ساي", "frequency_rank": 1, "status": "official"},
  "morphology": {"is_root": true, "root_word": "saya", "affix": null, "affix_type": "none", "formula": "∅ + saya → saya"},
  "senses": [{
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
  }],
  "dual_scenarios": [
    {"scenario": "formal", "ms": "Saya ingin mengucapkan terima kasih kepada semua pihak yang menjayakan program ini.", "zh": "我谨向所有促成本次活动成功举办的各方致谢。", "en": "I would like to thank everyone who helped make this programme a success."},
    {"scenario": "colloquial", "messages": [
      {"speaker": "Hafiz (同事)", "ms_spoken": "Kau dah lunch ke?", "ms_standard": "Awak sudah makan tengah hari ke?", "zh": "你吃午饭了吗？", "en": "Have you had lunch yet?"},
      {"speaker": "Farah (同事)", "ms_spoken": "Belum, saya baru nak keluar ni.", "ms_standard": "Belum, saya baru mahu keluar ini.", "zh": "还没呢，我正准备出去。", "en": "Not yet. I'm just about to head out."}
    ]}
  ],
  "spoken_shortcuts": [{"abbr": "sy", "full_form": "saya", "note": "聊天中常见的省元音写法；本地 Kaikki 记录有此形式。正式书写还原为 saya。"}],
  "cultural_pragmatics": {"register": "standard"},
  "etymology": {"source_language": "Sanskrit, through Malay sahaya", "cognitive_memory_aid": "先记一句 Saya mahu belajar（我想学习）：见老师或初次见面，自称先选 saya。此为使用记忆法，不是词源拆字。"}
}
```

## 词典工作台

工作台沿用 Open-Lexicon 的 Apple 风格布局与阅读交互，适配马来语八维内容。当前浏览器视觉验收的实际进度见[验收记录](docs/WORKBENCH_IMPLEMENTATION.md)，尚不宣称完成 1:1 视觉验收。

- **本地检索**：Web Worker 处理马来词、中文释义、Jawi、`#root:ajar` 词族、Bahasa Pasar 别名及 OSA 拼写纠错。Zero-Compute 指无需后端检索计算服务；浏览器仍负责计算。
- **连续阅读**：`saya` 2 个义项、`dengan` 14 个义项均完整平铺；27 个字母按钮按 14 列、两行布局，附两字母前缀导航、7 类筛选、4 种排序、每批 50 词的双向续载与页码跳转。方向键切词，`/` 聚焦搜索。
- **三种语言模式**：`三语全解 / 中马双语 / Bahasa Melayu` 通过 CSS 控制显示，保留完整数据与 DOM 翻译。
- **aA 排版面板**：5 档字号、4 类字体、3 档疏密、4 种纸张背景；支持深浅主题、恢复默认值、侧栏拖动和沉浸阅读。Jawi 使用局部 RTL、专用字体与零额外字距保护。
- **学习与导出**：3D 翻卡、学习连续天数、收藏、结构化 Markdown 和 Anki TSV 导出；导出保留全部语言，不受当前显示模式影响。朗读依赖系统 Web Speech 语音。
- **离线**：详情按需从 27 个字母分片下载至 IndexedDB；“准备离线词库”验证全部分片和索引持久化，支持暂停/续传。页面 shell 使用 Network-First，网络失败时仅回退当前 shell 缓存；词库请求由独立数据层管理。

## 快速启动（Quick Start）

运行环境：Python 3.9+（服务仅用标准库）；自动化前端测试使用 Node.js 22+。

```sh
git clone https://github.com/znhjsnb/Open-Melayu.git
cd Open-Melayu
python app/server.py
```

打开 **http://127.0.0.1:8766**。本地服务提供 `/api/health`、`/api/stats`，响应带 `Cache-Control: no-cache`。

也可使用纯静态服务：

```sh
python -m http.server 8766 --directory app/static
```

纯静态模式没有 `/api/*`，查词由浏览器完成。部署需包含整个 `app/static/`（含 `data/`），当前 Service Worker 使用根路径 `/sw.js`，应部署在站点根目录；线上 Service Worker 需要 HTTPS，本地回环地址可用 HTTP。首次离线使用前，先在线访问并完成“准备离线词库”；离线朗读还取决于设备语音包。

### 验证

```sh
node --test tests/frontend.test.mjs tests/frontend.interactions.test.mjs
python tests/test_stage3_trilingual_quality_gates.py
node --test tests/verify_workbench_e2e.mjs
```

第三项需要可用 Chromium；通过 `CHROME_PATH` 指定浏览器路径，并先启动 8766 服务。受限宿主若遇到 Node 测试子进程 `spawn EPERM`，可使用支持该选项的 Node 版本，在 PowerShell 设置 `$env:NODE_OPTIONS='--test-isolation=none'` 后运行相同命令。单元测试和数据门禁通过不等于浏览器视觉验收通过。

## 目录与开发接入

```text
open-melayu/
├── app/server.py                  # 本地静态服务、健康检查及统计
├── app/static/                    # HTML/CSS/JS、Worker、IndexedDB、Service Worker
│   └── data/                      # manifest、search_index、shards/a..z + other
├── data/enriched/                 # 14,748 个独立精编 JSON
├── data/prpm_raw/                 # 来源核验材料，保留原始归属
├── data/candidate_pool_15k.json    # 候选池与位序
├── src/                           # 数据生产、核验与同步工具
├── tests/                         # 前端、数据及浏览器门禁
├── docs/SCHEMA.md                 # 字段、三态、索引与分片契约
├── docs/WORKBENCH_IMPLEMENTATION.md
├── START.md                       # 当前状态与实际验证记录
├── RULES.md                       # 本工程规则
├── AGENTS.md                      # 代理入口
└── LICENSE                        # 数据/文档 CC-BY-SA 4.0；代码 MIT
```

读取单词数据无需数据库或 API 密钥：

```python
import json
from pathlib import Path

entry = json.loads(Path("data/enriched/saya.json").read_text(encoding="utf-8"))
for sense in entry["senses"]:
    print(sense["pos"], sense["zh_definition"], sense["en_definition"])
```

贡献前先读 [AGENTS.md](AGENTS.md)、[RULES.md](RULES.md) 与 [Schema](docs/SCHEMA.md)。保留来源诚实、三态守恒及词头/位序一致性，不以补齐数量为由虚构定义、Jawi 或词源。数据变更须同步候选池相关状态、分片、索引与版本，并运行质量门禁。

## 许可证与归属

项目自有词库数据与文档采用 **CC-BY-SA 4.0**，软件与脚本采用 **MIT**，具体范围与文本见 [LICENSE](LICENSE)。引用 PRPM、DBP 或其他第三方材料时保留其来源与原权利归属；项目许可不改变第三方材料的权利。再分发请注明 Open-Melayu、具体版本、适用许可与修改情况。
