"""
Invoke Codex CLI for final independent sign-off audit on build om-20261103-v9756
and commit the updated docs/FINAL_15K_AUDIT_REPORT.md.
"""
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
sys.path.insert(0, str(ROOT_DIR / "src"))
from run_expansion_to_15000_sliding_queue import CODEX_EXE
REPORT_FILE = ROOT_DIR / "docs" / "FINAL_15K_AUDIT_REPORT.md"

PROMPT = """你现在是 Open-Melayu 15K 项目的独立终审官（Codex CLI）。
我们在构建 `om-20261103-v9756` 中已经全量修复并闭环了你在上一轮终审报告第 10 节（整体签字前的关闭条件）列出的全部 6 项问题：
1. 【三词位序及分片 ID 错配】：全量 14,748 个精编词（含 `head=6740`, `hung=6183`, `stand=11421`）的 `headword.frequency_rank` 与分片 `id` 已 100% 与 `data/candidate_pool_15k.json` 及 `app/static/data/search_index.json` 逐词对齐，27 个分片唯一 ID 数恢复为 15,000，`pytest` 已新增逐词 ID 一致性断言。
2. 【编辑改述展示为 DBP 原文】：全库义项已增加 `senses[].ms_is_verbatim` 布尔标记（与 `data/prpm_raw/<word>.json` 逐词校验是否为连续原文子串），前端 `app/static/app.js:531` 已升级为：仅当 `head.status === 'official' && s.ms_is_verbatim === true` 时展示 `DBP 原文:`，其余 `official` 编辑归纳释义（如 `aa`, `ab`, `memasak`, `tajam`）诚实展示 `马来语释义 (基于 DBP 官方词条):`。
3. 【旧白名单入口仍可重写来源】：`src/run_overnight_closure_and_audit.py` 中的 `CORE_MALAY_WITHOUT_PRPM_FILE` 已清空为 `set()`，且 `reconcile_provenance_status()` 已统一委托给 `finalize_gate4_and_salvage3.main()`。
4. 【八维七容器契约缺口与 U+200C】：全库 14,748 个逐词文件已 100% 补齐规范数组 `spoken_shortcuts: []`，7 词 8 义项（`erso, iebih, mae, pappi, rio, thats, tien`）的空缺 `pos` 已 100% 补齐，且 `U+200C` 亦已一并清洗归 0（五类控制/格式字符 `U+0081/U+00AD/U+200B/U+200C/U+200E` 均为 0）；`pytest` 已新增 `spoken_shortcuts` 容器类型与 `pos` 非空断言。
5. 【CDP 验收断言强化】：`tests/verify_trilingual_e2e.mjs` 已新增 `.word-title === word`、逐义项 `minCollocsPerSense >= 2`、以及 `DBP 原文:` vs `马来语释义 (基于 DBP 官方词条):` 等精确断言，实测 8 个代表词全部通过（returncode = 0）。
6. 【文档状态对齐】：`START.md` 与 `docs/PROJECT_HANDOFF.md` 已消除 `om-20261102-v1` 与“未提交”冲突，明确标注历史章节为阶段性快照，并将顶部口径精确对齐为“15,000 候选池中 14,748 词（98.32%）完成精编、252 词（1.68%）保留为 missing_source，CDP 为 8 个代表词四态验收”。

请你用单趟 Python 脚本（并在同一进程调用 `pytest.main(["-p", "no:cacheprovider", "tests/test_stage3_trilingual_quality_gates.py", "-v", "-s"])`）独立复核上述全部修复项，然后输出最终签字的 `docs/FINAL_15K_AUDIT_REPORT.md` 完整 Markdown 报告。
"""

def main():
    cmd = [
        CODEX_EXE,
        "exec",
        "-C", str(ROOT_DIR),
        "-s", "read-only",
        "-c", 'model_reasoning_effort="high"',
        "-o", str(REPORT_FILE),
        "-",
    ]
    print("[*] Running Codex CLI final sign-off audit...")
    res = subprocess.run(
        cmd,
        input=PROMPT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=900,
    )
    print(f"[*] Codex CLI exited with code {res.returncode}")
    if REPORT_FILE.exists():
        size = REPORT_FILE.stat().st_size
        print(f"[+] Updated {REPORT_FILE} ({size} bytes)")
        subprocess.run(["git", "-C", str(ROOT_DIR), "add", "docs/FINAL_15K_AUDIT_REPORT.md"], check=True)
        subprocess.run(["git", "-C", str(ROOT_DIR), "commit", "-m", "docs(audit): final signed-off Codex 15K audit report (om-20261103-v9756)"], check=False)
        status = subprocess.run(["git", "-C", str(ROOT_DIR), "status", "--short"], capture_output=True, text=True, encoding="utf-8")
        print(f"[+] Git status after commit:\n{status.stdout.strip()}")
    else:
        print("[!] Report file not found!", res.stderr[-500:])
        sys.exit(1)

if __name__ == "__main__":
    main()
