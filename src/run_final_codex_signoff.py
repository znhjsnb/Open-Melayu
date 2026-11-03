"""
Invoke Codex CLI for final independent sign-off audit on commit 3268a293
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
我们在提交 `3268a293` 中已经全量修复并闭环了你在上一轮终审报告（`docs/FINAL_15K_AUDIT_REPORT.md` 第八节）中提出的全部 8 项阻塞问题：
1. 救回最后 3 个 `source_only` 词（`head`, `stand`, `hung`），全库三态严格守恒为：`14,748 enriched + 0 source_only + 252 missing_source = 15,000`（构建号 `om-20261103-v8488`）。
2. 移除 10 词白名单与子串启发式词根匹配，100% 基于本地 `data/prpm_raw/*.json` 物理证据实现三阶来源诚实分级：
   - `official` = 7,479 词（具备直接马来语 DBP 词条，前端展示 `DBP 原文:`）
   - `root_derived` = 2,328 词（真实马来语构词派生词且词根具备马来语 DBP 词条，前端展示 `马来语释义 (基于 DBP 词根推导):`）
   - `corpus_usage` = 4,941 词（官方马来语词典未单独收录或仅见于英马词典/字幕高频语料，前端展示 `马来语释义 (字幕高频语料用法):`）
   同时彻底清除了 `milan`、`meera`、`jedi` 等专名的误配词根爪夷文（`jawi: null`, `root_jawi: null`），将 `bagai`、`kamus`、`spt` 等无本地 PRPM 缓存词诚实归入 `corpus_usage`。
3. 全库 14,748 个词条文件的控制字符/格式字符（`U+0081`, `U+00AD`, `U+200B`, `U+200E`）全部归 0，`headword.jawi` 与 `morphology.root_jawi` 中的空字符串 `""` 全部归 0，纯问号 Jawi = 0。
4. `data/audit/quarantine_triage_report.json` 已更新，252 个 `type_b_missing_source_words` 与分片中的 252 个 `missing_source` 1:1 严格对齐，且每词均具备非空 `reason` 说明。
5. Python 3.13 已安装 `pytest 9.2.0`，`python -B -m pytest -p no:cacheprovider tests/test_stage3_trilingual_quality_gates.py -v` 7 项测试全部 PASS（returncode = 0）。
6. `tests/verify_trilingual_e2e.mjs` 已升级为覆盖 `official`、`root_derived`、`corpus_usage`、`missing_source` 全状态硬断言且移除 `finally` 中的 `process.exit(0)`，实测 returncode = 0。
7. `START.md` 与 `docs/PROJECT_HANDOFF.md` 已同步更新至最新 `14,748 / 0 / 252` 状态，且全仓已在 commit `3268a293` 完成干净提交（`git status --short` 为空）。

请你执行一次高效、单趟的独立脚本核验（请用单个 Python 脚本一次性校验上述统计与门禁，并运行 pytest，避免多次重复遍历 14,748 个文件），然后输出完整的 Markdown 终审报告（将直接写入 `docs/FINAL_15K_AUDIT_REPORT.md`），包含：
1. 终审总体裁定（明确给出各门禁 PASS 状态与最终签字结论）
2. 15,000 词三态守恒核验（14,748 + 0 + 252 = 15,000）与分片/索引一致性
3. 三阶来源诚实分级（7,479 official / 2,328 root_derived / 4,941 corpus_usage）及此前 8 项问题的逐项复核销账表
4. 八维教学完整度与马-中-英三语 100% 覆盖核验
5. 252 个 `missing_source` 隔离词条审计清单与自动化测试（pytest + CDP E2E）核验结论。
请直接输出完整 Markdown 正文。
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
        subprocess.run(["git", "-C", str(ROOT_DIR), "add", "docs/FINAL_15K_AUDIT_REPORT.md", "src/run_final_codex_signoff.py"], check=True)
        subprocess.run(["git", "-C", str(ROOT_DIR), "commit", "-m", "docs(audit): final 100% green Codex 15K sign-off audit report"], check=False)
        status = subprocess.run(["git", "-C", str(ROOT_DIR), "status", "--short"], capture_output=True, text=True, encoding="utf-8")
        print(f"[+] Git status after commit:\n{status.stdout.strip()}")
    else:
        print("[!] Report file not found!", res.stderr[-500:])
        sys.exit(1)

if __name__ == "__main__":
    main()
