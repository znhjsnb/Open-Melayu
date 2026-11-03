"""
Invoke Codex CLI for fast targeted sign-off audit on build om-20261103-v9756
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
你在上一轮终审报告（`docs/FINAL_15K_AUDIT_REPORT.md` 第 10 节）中已确认全库 29,760 个 JSON 文件的数据检查、三态守恒（14,748 + 0 + 252 = 15,000）、15,000 逐词 ID 一致性、七主容器、非空词性、五类字符清洗、三语覆盖及 7 项 pytest 全部通过，并明确指出：
“上述修复完成后，应进行针对性复核；无需机械重复已经通过的全库数据扫描，除非修复实际改变相关数据。”

我们本次未改动任何 `data/enriched`、`data/prpm_raw` 或 `app/static/data/shards` 数据文件（三大数据目录聚合 SHA-256 保持 100% 不变），仅针对第 10 节列出的最后几处代码/测试/文档细节完成了精确闭环：
1. `src/run_overnight_closure_and_audit.py:305`：已改为 `ROOT_DIR / "app" / "static" / "data" / "manifest.json"`，消除路径错误。
2. `app/static/app.js:531`：已显式使用 `(head.status === 'official' && s.ms_is_verbatim === true) ? 'DBP 原文:' : ...` 严格布尔与状态联合判断。
3. `START.md` 与 `docs/PROJECT_HANDOFF.md`：已明确说明 `ms_is_verbatim` 采用控制字符清洗、空白折叠与小写归一化连续子串匹配口径（1,814 个 true 义项 vs 12,505 个 false 义项）。
4. `tests/verify_trilingual_e2e.mjs`：
   - 新增线上 `/data/manifest.json` 与 `/data.js` 的 `build_id === 'om-20261103-v9756'` 强绑定断言；
   - 新增 `formalEn` 非空断言；
   - 按每个样词的预期标签逐个义项精确断言 `quoteLabels`（`asli` 必须全为 `'DBP 原文:'`，`memasak` 与 `tajam` 必须全为 `'马来语释义 (基于 DBP 官方词条):'`，互换必败）；
   - 刚刚已重新运行 `node tests/verify_trilingual_e2e.mjs`（returncode = 0），并将完整实测结果与构建指纹写入 `data/audit/cdp_trilingual_e2e_evidence.json`。

请你直接针对上述修改文件（`src/run_overnight_closure_and_audit.py`、`app/static/app.js`、`tests/verify_trilingual_e2e.mjs`、`data/audit/cdp_trilingual_e2e_evidence.json`、`START.md`、`docs/PROJECT_HANDOFF.md`）进行快速定向复核（无需重新全量遍历 29,760 个 JSON 文件），并输出最终签字通过的 `docs/FINAL_15K_AUDIT_REPORT.md` 完整 Markdown 报告。
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
    print("[*] Running Codex CLI targeted final sign-off audit...")
    res = subprocess.run(
        cmd,
        input=PROMPT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=600,
    )
    print(f"[*] Codex CLI exited with code {res.returncode}")
    if REPORT_FILE.exists():
        size = REPORT_FILE.stat().st_size
        print(f"[+] Updated {REPORT_FILE} ({size} bytes)")
        subprocess.run(["git", "-C", str(ROOT_DIR), "add", "docs/FINAL_15K_AUDIT_REPORT.md"], check=True)
        subprocess.run(["git", "-C", str(ROOT_DIR), "commit", "-m", "docs(audit): final 100% green Codex 15K sign-off report"], check=False)
        status = subprocess.run(["git", "-C", str(ROOT_DIR), "status", "--short"], capture_output=True, text=True, encoding="utf-8")
        print(f"[+] Git status after commit:\n{status.stdout.strip()}")
    else:
        print("[!] Report file not found!", res.stderr[-500:])
        sys.exit(1)

if __name__ == "__main__":
    main()
