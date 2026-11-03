# Open-Melayu 工程入口

本文件适用于整个仓库。Windows PowerShell 读取 Markdown 时使用 `Get-Content -Encoding UTF8`。

开始实质开发或接手前依次阅读：

1. [START.md](START.md)：当前数据版本、实际验收结果与未决阻断。历史里程碑不能替代最新状态。
2. [RULES.md](RULES.md)：本项目目标、八维教学规范、来源诚实与生产约束。
3. [docs/WORKBENCH_IMPLEMENTATION.md](docs/WORKBENCH_IMPLEMENTATION.md)：工作台行为、缓存与浏览器验收边界。
4. [docs/SCHEMA.md](docs/SCHEMA.md)：JSON、三态、来源标签、搜索索引与 27 分片契约。

本工程是 Open-Melayu 15K，默认端口 8766；`dict` / Open-Lexicon 是参考工程，不继承其词数、Schema、数据或写入权限。

- 保持 15,000 个唯一词头与 ID；当前 14,748 enriched + 0 source_only + 252 missing_source。不得把待补项冒充精编词。
- 八维内容默认平铺；搭配位于 `senses[].collocations`。Jawi 局部 RTL，无可靠来源保留 `null`；社交容器兼容别名并存时须相等。
- 区分 DBP 原文、基于官方词条编写、词根推导与语料用法。只有核验过的原文才可设置 `ms_is_verbatim: true`。
- 页面 shell 与词库版本独立；页面修改升级 `SHELL_CACHE` 并同步 `sw.js` 触发更新。离线回退只读当前 shell cache，不全局 `caches.match`。
- 不读取或清理用户学习记录；测试使用独立临时数据与浏览器 profile。不得调用付费外部 API，数据生产模型与调度约束以 RULES 为准。
- 结束前运行受影响检查及本批要求的门禁，更新既有 START 与工作台记录。未运行、受阻、通过须明确区分；浏览器未验收不能写成视觉对齐已通过。

常用门禁：

```sh
node --test tests/frontend.test.mjs tests/frontend.interactions.test.mjs
python tests/test_stage3_trilingual_quality_gates.py
node --test tests/verify_workbench_e2e.mjs
```

环境条件及受限宿主替代运行方式见 README。尊重宿主文件权限；`.git` 只读时报告未提交，不尝试绕过权限。
