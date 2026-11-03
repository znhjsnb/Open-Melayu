# Open-Melayu 15K 工作台移植验收记录

## 2026-11-03 Release 导出与自动发布（最新）

- 新增 `src/export_databases.py`：纯 Python 标准库，从静态 manifest、索引与 27 片读取完整数据；先校验版本、三态、来源数量、唯一词头、1–15,000 ID 与索引，再导出。5 个专名的 `headword.word` 保留原始大写，按规范化词头比对，不改源数据。支持 `--all`、`--sqlite`、`--anki`、`--jsonl`、`--web`、`--zip`；单格式可附加压缩，单独 `--zip` 重建全部，完成前不替换旧产物。
- SQLite 包含 `words`、`senses` 和 `melayu_fts` FTS5（unicode61）；`raw_json` 与 JSONL 保留所有字段、null、来源与待补状态。Anki 仅收录 enriched，每行两字段、无表头，内容转义后生成 HTML，Jawi 局部 RTL；三语、全部义项/搭配、Berita/WhatsApp 双境及多轮消息、构词、口语、礼仪、词源与记忆平铺保留。
- `python src/export_databases.py --all` 实际耗时 18.4 秒；四个 ZIP 为 SQLite **39,789,363 bytes**、Anki **24,007,712 bytes**、JSONL **24,433,480 bytes**、静态站 **25,931,180 bytes**。全部位于 `data/exports/`，已增加忽略规则并在 README 写明下载、重建、Anki 导入和 HTTP 部署方法。
- `python tests/verify_release_exports.py` **PASS**：SQLite / JSONL 各 **15,000** 词，SQLite **28,017** 个义项，Anki **14,748** 行；所有 SQLite 投影、raw_json 与 JSONL 逐词对照分片，FTS5 词项/前缀/Jawi/英马释义查询、完整性与外键检查通过。三态保持 **14,748 + 0 + 252**。三个数据 ZIP 解压载荷 SHA-256 与原产物一致，四包 CRC 检查通过。
- 静态包 **37 个文件 / 27 片** 的路径与源文件字节全部一致；另解压至工程 `.tmp/release-http-*`，用独立回环随机端口提供纯静态 HTTP，首页及全部 37 条文件路由 HTTP 200 且字节一致，随后关闭服务并删除该临时目录。**这不是浏览器视觉/Worker/离线验收**。
- 新增导出测试 **9/9 PASS**：覆盖状态筛选、三语/Jawi/来源、HTML 注入与 TSV 控制字符、完整 JSON、SQL null/义项/FTS5、原子失败与重跑、参数选择、27 片与 manifest/索引损坏拒绝、专名大写保留，以及完全没有 `data/enriched` 的隔离静态夹具。测试目录仅使用工程 `.tmp/export-tests-*` 的合成数据与继承权限，不修改 ACL，不读取学习记录。本宿主 Python 3.13 的 `TemporaryDirectory` 私有目录无法重开，已改用普通唯一临时目录并核对删除范围；失败尝试留下的受限空目录未更改权限或强行清理。
- 新增 GitHub Actions：`ubuntu-latest`、Python 3.11，标签 `v*` 推送或手动指定已有标签，先检出并核验标签，再跑导出测试、构建和独立产物校验，由 `softprops/action-gh-release@v2` 上传指定四包；缺失附件即失败。工作流 YAML/触发器/参数/附件配置检查 PASS。**本机实跑环境为 Python 3.13.15 / SQLite 3.50.4，Ubuntu / Python 3.11 和 GitHub 实际上传未运行**。
- 本批再次运行前端 Node 门禁（`NODE_OPTIONS=--test-isolation=none`）：**36/36 PASS**；Stage 3 全库门禁：**全部 PASS**。工作台 E2E 两项均因 Chrome 在 CDP 启动前退出（`4294930433`）失败，未到页面断言；未取得浏览器视觉或 Anki 客户端导入验收。词条、静态文件、DATA_VERSION 与 SHELL_CACHE 均未修改；`.git` 只读，未提交、推送或远程发布。

## 2026-11-03 公开仓库准备与缓存修复（此前批次）

- 新增 README、LICENSE、AGENTS 与 SCHEMA。统计保持 15,000 = 14,748 enriched + 0 source_only + 252 missing_source；四档展示标签与三类精编来源分开解释。许可证沿用参考工程的分范围许可结构，保留原 MIT 版权并补充本项目署名与第三方材料归属。
- `SHELL_CACHE` 升为 `open-melayu-shell-v5`；SW 为同源页面资源与导航使用 Network-First，成功响应更新当前缓存，网络失败只从当前 shell 缓存回退。数据与 API 请求不接管；缓存写入失败不影响在线响应，HTTP 错误保留原响应。
- `app/server.py` 统一发送 `Cache-Control: no-cache`。本轮启动 8766，健康/统计正常；HTML、CSS、app.js、data.js、sw.js 与磁盘逐字节一致，均确认响应头。没有据此宣称已有用户浏览器已完成 SW 更新。
- 新增 3 个 SW 行为测试，覆盖旧缓存下的网络优先、离线精确资源/导航回退、当前缓存隔离、数据/API/跨源/非 GET 绕过、存储不可用及 HTTP 503。
- `node --test tests/frontend.test.mjs tests/frontend.interactions.test.mjs` 默认模式仍受宿主 `spawn EPERM` 阻断；`NODE_OPTIONS=--test-isolation=none` 下 **36/36 PASS**，无跳过。
- `python tests/test_stage3_trilingual_quality_gates.py` 全部门禁 **PASS**。将该脚本根目录改为从自身路径定位，另从 `.tmp` 执行 `python ../tests/test_stage3_trilingual_quality_gates.py` 验证可移植性，全部门禁再次 PASS。未修改词条、分片、索引或 DATA_VERSION。
- `node --test tests/verify_workbench_e2e.mjs`（同上 NODE_OPTIONS）两项均因 Chrome 在 CDP 启动前退出（`4294930433`）失败；**未执行页面断言，未取得视觉 1:1 或真实浏览器 SW 验收结果**。
- 删除指定根目录 6 个 `task_codex_*.md`、`generate_workbench.py`、`词典预览工作台.html` 及四张临时截图；补齐忽略规则，私有临时目录无已跟踪文件。文档本地链接与 JSON 示例解析通过。`.git` 只读，未提交或推送。

## 2026-11-03 侧栏四项修补（此前批次）

- 字母/前缀按钮增加 `white-space: nowrap`；字母“全部”采用 `10px` 和 `-0.05em` 字距。
- 前缀按钮仅显示前缀文本，计数保留为 `title="数量 词"`；筛选标签为“全部 / 8维精编 / 词根 / 口语 / Jawi / 原义 / 待补”，保留七个 data-filter。
- 移动返回按钮断言采用 flex 项目块化后的计算值 `flex`。两个桌面 E2E 入口明确设置 1920×1000，补充筛选单行、字母不换行及前缀文本/计数提示检查。
- 页面缓存升至 shell v4，并同步 SW 安装触发注释；数据版本仍为 `om-20261103-v9756`。
- `node --test tests/frontend.test.mjs tests/frontend.interactions.test.mjs` 默认模式因宿主 `spawn EPERM` 未运行断言；设置 `NODE_OPTIONS=--test-isolation=none` 后 **33/33 PASS**，无跳过断言。
- 同一设置运行 `node --test tests/verify_workbench_e2e.mjs`：两个顶层测试均因 Chrome 在 CDP 启动前退出（`4294930433`）而失败，**本轮未取得浏览器几何验收结果**。
- 8766 `/api/health`、`/api/stats` 正常，仍为 15,000 词；HTML/CSS/app.js/data.js/sw.js 的 HTTP 响应与磁盘 SHA-256 一致。未修改词条数据；`.git` 为只读，未提交。

## 此前界面对齐批次

日期：2026-11-03。本轮已完成界面对齐实现和可运行的源码/数据检查；浏览器门禁受 Chrome 启动及实屏访问权限阻断，**不能认定本轮已达到 100% 视觉验收**。端口 8766 已验证服务身份和资源一致性；数据未修改，`.git` 只读，未提交。

## 实现范围

| 护栏 | 实现与证据 |
| --- | --- |
| 数据版本与离线 | 保持 `om-20261103-v9756`，独立 shell v3（同步更新 SW 触发壳升级）；分片请求去重、失败重试、5 片 RAM LRU、IndexedDB 状态反馈；离线准备逐片验证 27 片持久存储，并验证索引缓存，支持暂停/续传和配额失败提示。离线入口位于 sidebar-footer。 |
| 检索 | 导出纯函数；马来语、中文、Jawi、词根、别名、OSA 模糊轨道；7 种筛选（含 source/missing）、4 种确定排序；两字母前缀计数、50 行分页、任意有效 offset、targetWord 定位。 |
| 三语与排版 | 默认三语；CSS 控制双语/马来语显示，保留 DOM 翻译；统一 `open_melayu_typography_v2`，语言、5 档字号、4 字体、3 疏密、4 纸张；主题按钮同步；一键恢复全部默认值。 |
| 八维卡片 | 保留平铺及四档来源标签，增加 status-badge、root_jawi、义项速跳；Jawi 专用字体、RTL 与零额外字距保护。 |
| 连续词流 | 首屏严格 50 行；底部续载、顶部前插及锚点保持；页码跟随可见行、页码跳转；方向键跨批次；hash 与搜索框分离；检索/详情请求过期隔离，覆盖防抖、IME 与首次深链竞态。 |
| 右侧工具 | sticky 工具栏与词头/Jawi/朗读钉选；沉浸阅读/Escape；从模型导出 Markdown/Anki，保留全部语言并转义 HTML、清理 TSV 控制字符；3D 翻卡、无障碍面标记、下滑关闭与每日学习连续天数。 |
| 自动验证 | 新增 `frontend.test.mjs`、`frontend.interactions.test.mjs`，及 `verify_workbench_e2e.mjs`（隔离合成词库浏览器交互 + 8766 真实 Stage 3 抽查）。 |
| 界面对齐 | 完整继承参考站 506 行 CSS，仅在基础变量插入 Jawi 字体，后接八维详情及必要适配。27 个 alphabet-button 默认 14 列两行，前缀位于 search-area 内；filter-pill 采用 aria-pressed；word-row 取消精编徽章、保留 Jawi/词性或位序/省略释义及选中竖条。排版弹窗使用右上角定位、2×2 Ag 字体预览、三档密度、四种纸张色样；语言仅在工具栏，字号仅使用 A−/A+ 五档切换。 |
| 导航与布局 | 900px 统一断点，reading / immersive 与参考 CSS 一致，返回词表同步退出沉浸。词头滚出后隐藏 breadcrumb，显示含 Jawi/朗读的钉选词头。侧栏宽度本工程独立持久化，240–640px，双击/Enter 恢复 340px，方向键微调，Home/End 到边界。 |

## 已执行结果

本轮实际执行结果（此前版本的宿主通过回报不替代本轮验收）：

- `node --test tests/frontend.test.mjs tests/frontend.interactions.test.mjs`（`NODE_OPTIONS=--test-isolation=none`）：**33/33 PASS**。默认测试文件子进程受宿主 `spawn EPERM` 限制；关闭文件进程隔离，未跳过任何断言。
- `python tests/test_stage3_trilingual_quality_gates.py`：**全部门禁 PASS**（Jawi、八维结构、对话、来源分级、15K 三态/ID、索引一致性及三语覆盖）。
- `node tests/verify_trilingual_e2e.mjs`：**FAIL，未到页面断言**；Chrome 在 CDP 启动前退出，退出码 `4294930433`。
- `node --test tests/verify_workbench_e2e.mjs`（同上 NODE_OPTIONS）：**FAIL，两个顶层测试均未到页面断言**；同一 Chrome 启动阻断。

本轮补充检查：

- HTML 标签闭合及 68 个 ID 唯一性、参考 CSS 基础完整性、前端模块与浏览器脚本语法检查、`git diff --check`：通过。
- 8766 `/api/health` 与 `/api/stats` 已实查：15,000 总词，14,748 enriched，0 source_only，252 missing_source，build 为 `om-20261103-v9756`。HTML、CSS、app.js、data.js、sw.js 通过 HTTP 与磁盘 SHA-256 逐字节核对；这不能证明用户已有浏览器缓存已更新。

Node 交互测试运行实际 app.js 控制器，替换 DOM、Worker、存储与计时接口；布局坐标为合成值。它们覆盖控制器契约及 CSS 规则，不能代替 Chrome 实际排版、滚动、字体连字或原生对话框验收。DB 测试使用独立异步存储夹具，不访问用户学习记录。

## 浏览器验收说明

本轮 Chromium 在 CDP 启动前退出，未能执行浏览器断言。尝试通过 computer-use 读取现有 Open-Melayu Chrome 窗口时，自动审批返回 `Computer Use was not approved to use Google Chrome`；浏览器访问宿主也报告 unavailable。未绕过权限、修改 ACL 或降低浏览器安全选项。

浏览器测试新增桌面 `#back` 隐藏、排版面板 `left > 500`、27 个字母按钮两行、离线入口位于 footer，以及 390px 移动端返回/面板边界和减少动效翻卡检查。三语 E2E 改用公共 harness 创建本工程 `.tmp/browser-*` 的独立临时 profile，不再清空用户数据库或在工程外写 profile；保留八个代表词和全部来源/翻译断言。Chrome 启动失败现在即时报告，避免无效等待。

Jawi 字距断言接受 `0px` 和 `normal`：Chromium 的 `getComputedStyle(el).letterSpacing` 会将零字距序列化为 `normal`，与现有 `wordSpacing` 检查保持一致；`legible` 模式下 `.entry` 的非零像素字距仍不被接受为 Jawi 零字距。

当前内容验收以 `test_stage3_trilingual_quality_gates.py` 和 `verify_trilingual_e2e.mjs` 的 Stage 3 契约为准。保留旧 CDP 脚本，没有为追求绿灯改回旧数据或弱化其断言。新增工作台 E2E 额外检查实际首屏 50 行、三语 DOM/CSS、Jawi、流式加载、排版、导出、闪卡和离线等行为。

旧 `node tests/cdp_e2e_full.mjs` 仍保留 Stage 1 的 `anggap → source_only` 等数据断言，不能作为当前 Stage 3 的内容真值；本次宿主通过记录不包含该旧脚本。
