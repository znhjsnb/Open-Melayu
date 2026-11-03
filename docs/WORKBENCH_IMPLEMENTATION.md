# Open-Melayu 15K 工作台移植验收记录

日期：2026-11-03。代码实现已完成；据宿主回报，Node/Python、三语代表词与真实 Chrome 工作台 E2E 验证均已通过，浏览器验收端口为 8766。未执行 git commit、git reset 或修改词库数据。

## 实现范围

| 护栏 | 实现与证据 |
| --- | --- |
| 数据版本与离线 | 保持 `om-20261103-v9756`，独立 shell v2；分片请求去重、失败重试、5 片 RAM LRU、IndexedDB 状态反馈；离线准备逐片验证 27 片持久存储，并验证索引缓存，支持暂停/续传和配额失败提示。损坏索引会重新下载。 |
| 检索 | 导出纯函数；马来语、中文、Jawi、词根、别名、OSA 模糊轨道；7 种筛选（含 source/missing）、4 种确定排序；两字母前缀计数、50 行分页、任意有效 offset、targetWord 定位。 |
| 三语与排版 | 默认三语；CSS 控制双语/马来语显示，保留 DOM 翻译；统一 `open_melayu_typography_v2`，语言、5 档字号、4 字体、3 疏密、4 纸张；主题按钮同步；一键恢复全部默认值。 |
| 八维卡片 | 保留平铺及四档来源标签，增加 status-badge、root_jawi、义项速跳；Jawi 专用字体、RTL 与零额外字距保护。 |
| 连续词流 | 首屏严格 50 行；底部续载、顶部前插及锚点保持；页码跟随可见行、页码跳转；方向键跨批次；hash 与搜索框分离；检索/详情请求过期隔离，覆盖防抖、IME 与首次深链竞态。 |
| 右侧工具 | sticky 工具栏与词头/Jawi/朗读钉选；沉浸阅读/Escape；从模型导出 Markdown/Anki，保留全部语言并转义 HTML、清理 TSV 控制字符；3D 翻卡、无障碍面标记、下滑关闭与每日学习连续天数。 |
| 自动验证 | 新增 `frontend.test.mjs`、`frontend.interactions.test.mjs`，及 `verify_workbench_e2e.mjs`（隔离合成词库浏览器交互 + 8766 真实 Stage 3 抽查）。 |

## 已执行结果

以下四项为宿主已运行并回报的结果，本次修订未重新执行这些测试：

- `node --test --test-isolation=none tests/frontend.test.mjs tests/frontend.interactions.test.mjs`：**30/30 PASS**。关闭的只是测试文件进程隔离，未跳过测试或断言。
- `python -m pytest tests/test_stage3_trilingual_quality_gates.py`：**7/7 PASS**。
- `node tests/verify_trilingual_e2e.mjs`：**8/8 代表词及截图 PASS**，端口 **8766**。
- `node --test --test-isolation=none tests/verify_workbench_e2e.mjs`：**13/13 真实 Chrome E2E 测试 PASS**，端口 **8766**。

此前已执行的补充检查：

- `git diff --check`、前端模块与浏览器脚本语法检查：通过。
- 8766 `/api/health` 与 `/api/stats` 已实查：15,000 总词，14,748 enriched，0 source_only，252 missing_source，build 为 `om-20261103-v9756`。静态资源通过 HTTP 与磁盘字节核对。

Node 交互测试运行实际 app.js 控制器，替换 DOM、Worker、存储与计时接口；布局坐标为合成值。它们覆盖控制器契约及 CSS 规则，不能代替 Chrome 实际排版、滚动、字体连字或原生对话框验收。DB 测试使用独立异步存储夹具，不访问用户学习记录。

## 浏览器验收说明

此前沙箱内启动 Chrome 曾受 `spawn EPERM` 及 Mojo/Crashpad 通道权限限制；宿主现已完成上述三语和工作台浏览器验收，原“浏览器验收待完成”状态已解除。

Jawi 字距断言接受 `0px` 和 `normal`：Chromium 的 `getComputedStyle(el).letterSpacing` 会将零字距序列化为 `normal`，与现有 `wordSpacing` 检查保持一致；`legible` 模式下 `.entry` 的非零像素字距仍不被接受为 Jawi 零字距。

当前内容验收以 `test_stage3_trilingual_quality_gates.py` 和 `verify_trilingual_e2e.mjs` 的 Stage 3 契约为准。保留旧 CDP 脚本，没有为追求绿灯改回旧数据或弱化其断言。新增工作台 E2E 额外检查实际首屏 50 行、三语 DOM/CSS、Jawi、流式加载、排版、导出、闪卡和离线等行为。

旧 `node tests/cdp_e2e_full.mjs` 仍保留 Stage 1 的 `anggap → source_only` 等数据断言，不能作为当前 Stage 3 的内容真值；本次宿主通过记录不包含该旧脚本。
