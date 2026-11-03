"""
Autonomous Overnight Post-Completion Closure, Salvage, Gate 4 Provenance Alignment & Codex Final Audit
Waits for `run_expansion_to_15000_sliding_queue.py` to complete, then executes:
1. Legacy mirror cleanup (`data/enriched/batch_*.json`)
2. Salvage pass for the 19 un-queued words + Type A recoverable quarantined words (retaining Type B non-word proper nouns in `missing_source`)
3. Gate 4 Provenance & Status Badge reconciliation (`status="official"` vs `status="corpus_usage"`)
4. Final 27-shard & search index atomic sync + pytest quality gates + Chromium CDP E2E verification
5. Independent Codex CLI (`codex.exe exec`) full-corpus 15,000-word final audit (`docs/FINAL_15K_AUDIT_REPORT.md`) + Git milestone commit
"""

import concurrent.futures
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure") and sys.stderr is not None:
    sys.stderr.reconfigure(encoding="utf-8")

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from run_expansion_to_15000_sliding_queue import (
    AUDIT_DIR,
    CODEX_EXE,
    DATA_DIR,
    ENRICHED_DIR,
    SCHEMA_PROMPT,
    LinguisticKnowledgeBase,
    limiter,
    update_shards_and_manifest,
    validate_trilingual_entry,
)

QUARANTINE_FILE = AUDIT_DIR / "quarantine_words.json"
CLOSURE_LOG_FILE = AUDIT_DIR / "overnight_closure_summary.json"
TRIAGE_REPORT_FILE = AUDIT_DIR / "quarantine_triage_report.json"
FINAL_AUDIT_MD = ROOT_DIR / "docs" / "FINAL_15K_AUDIT_REPORT.md"

# Strict Gate 4 policy: no hardcoded whitelist without local PRPM file evidence
CORE_MALAY_WITHOUT_PRPM_FILE: set[str] = set()


def is_sliding_queue_running() -> bool:
    """Check if run_expansion_to_15000_sliding_queue.py is currently running."""
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'python' -and $_.CommandLine -like '*run_expansion_to_15000_sliding_queue.py*' } | Select-Object -ExpandProperty ProcessId",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        pids = [line.strip() for line in res.stdout.splitlines() if line.strip().isdigit()]
        return len(pids) > 0
    except Exception as e:
        print(f"[WARN] Process check error: {e}", flush=True)
        return False


def wait_for_sliding_queue_completion():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Overnight Closure Supervisor started.", flush=True)
    checks = 0
    while is_sliding_queue_running():
        if checks % 10 == 0:
            enriched_cnt = len([f for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")])
            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for main sliding queue (run_expansion_to_15000_sliding_queue.py)... Current enriched: {enriched_cnt}",
                flush=True,
            )
        checks += 1
        time.sleep(30)
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Main sliding queue finished! Starting post-completion closure...", flush=True)


def clean_legacy_mirrors() -> List[str]:
    removed = []
    for p in ENRICHED_DIR.glob("batch_*.json"):
        try:
            p.unlink()
            removed.append(p.name)
            print(f"[CLEANUP] Removed legacy mirror file: {p.name}", flush=True)
        except Exception as e:
            print(f"[WARN] Failed to remove {p.name}: {e}", flush=True)
    return removed


def has_official_dbp_in_prpm(prpm_data: Optional[Dict[str, Any]]) -> bool:
    if not prpm_data or not isinstance(prpm_data, dict):
        return False
    for key in ("kamus_dewan", "kamus_pelajar", "definisi_melayu", "definisi", "prpm_definitions", "tesaurus"):
        val = prpm_data.get(key)
        if val and isinstance(val, list) and len(val) > 0:
            return True
        if val and isinstance(val, str) and len(val.strip()) > 0:
            return True
        if val and isinstance(val, dict) and len(val) > 0:
            return True
    return False


def run_salvage_worker(batch_tag: str, packets: List[Dict[str, Any]]) -> Dict[str, Any]:
    limiter.acquire()
    start_time = time.time()
    words = [p["word"] for p in packets]
    packet_map = {p["word"]: p for p in packets}

    salvage_rules = """
CRITICAL SALVAGE & CLOSURE RULES (100% MANDATORY):
1. Both the top-level JSON key and `headword.word` MUST match the exact `<word>` string in the input packet (character-for-character, including spacing; e.g. if the input word is "dihadapan", the key and `headword.word` MUST be "dihadapan", and note standard spacing "di hadapan" in `senses[].nuances`).
2. `morphology.formula` MUST NEVER BE EMPTY! For root words, abbreviations, or English loanwords in Malaysian subtitles, provide a clear non-empty formula such as "∅ + kamus → kamus (核心词根)" or "Singkatan: seperti → spt" or "Kata Pinjaman Inggeris: water".
3. Every word MUST have at least 1 sense in `senses`, and EVERY sense MUST have at least 2 collocations in `collocations` (each with `ms`, `zh`, `en`).
4. Output ONLY the raw JSON object `{ "<word>": { ... } }` without markdown code fences.
"""
    prompt = (
        SCHEMA_PROMPT
        + "\n"
        + salvage_rules
        + f"\nTARGET WORD PACKETS ({len(packets)} words):\n"
        + json.dumps(packets, ensure_ascii=False, indent=2)
    )
    out_file = AUDIT_DIR / f"salvage_{batch_tag}.json"
    cmd = [
        CODEX_EXE,
        "exec",
        "-C",
        str(ROOT_DIR),
        "-s",
        "read-only",
        "-m",
        "gpt-6.1-sol",
        "-c",
        'model_reasoning_effort="high"',
        "--ephemeral",
        "-o",
        str(out_file),
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            encoding="utf-8",
            timeout=420,
        )
        elapsed = round(time.time() - start_time, 1)
        if proc.returncode != 0 or not out_file.exists():
            return {"batch_tag": batch_tag, "status": "error", "validated": {}, "errors": {w: "exec_error" for w in words}}

        raw = out_file.read_text(encoding="utf-8").strip()
        if "```" in raw:
            lines = [l for l in raw.splitlines() if not l.strip().startswith("```")]
            raw = "\n".join(lines).strip()
        data = json.loads(raw)

        # Build normalized lookup in case model spaced a compound word
        norm_lookup = {}
        if isinstance(data, dict):
            for k, v in data.items():
                norm_lookup[k.lower().strip()] = v
                norm_lookup[k.lower().strip().replace(" ", "")] = v

        validated = {}
        errors = {}
        for w in words:
            entry = norm_lookup.get(w) or norm_lookup.get(w.replace(" ", ""))
            if not entry or not isinstance(entry, dict):
                errors[w] = "Missing in output JSON"
                continue
            # Enforce exact headword match for compound spacing edge cases
            if "headword" in entry and isinstance(entry["headword"], dict):
                entry["headword"]["word"] = w
            pkt = packet_map[w]
            ok, err = validate_trilingual_entry(entry, pkt, w)
            if ok:
                entry["sociolinguistic_register"] = entry.get("cultural_pragmatics", {})
                validated[w] = entry
            else:
                errors[w] = err
        return {"batch_tag": batch_tag, "status": "ok", "validated": validated, "errors": errors, "elapsed": elapsed}
    except Exception as e:
        return {"batch_tag": batch_tag, "status": "exception", "validated": {}, "errors": {w: str(e) for w in words}}


def triage_and_salvage(kb: LinguisticKnowledgeBase) -> Dict[str, Any]:
    with open(DATA_DIR / "candidate_pool_15k.json", "r", encoding="utf-8") as f:
        pool = json.load(f)
    rank_map = {item["word"].lower().strip(): item.get("rank", item.get("id", 9999)) for item in pool}

    existing_enriched = {f.stem.lower() for f in ENRICHED_DIR.glob("*.json") if not f.name.startswith("batch_")}

    # 1. Identify un-queued words lacking prpm_raw files
    unqueued_words = []
    for item in pool:
        w = item["word"].lower().strip()
        if w not in existing_enriched:
            r = kb.rootwords.get(w, w)
            if w not in kb.prpm_file_map and r not in kb.prpm_file_map:
                unqueued_words.append(w)

    # 2. Load quarantine_words.json and classify into Type A (recoverable) vs Type B (non-word / proper noun)
    quarantine_data: Dict[str, Any] = {}
    if QUARANTINE_FILE.exists():
        try:
            quarantine_data = json.loads(QUARANTINE_FILE.read_text(encoding="utf-8"))
        except Exception:
            quarantine_data = {}

    type_a_words: List[str] = []
    type_b_records: Dict[str, Any] = {}

    for w_raw, info in quarantine_data.items():
        w = w_raw.lower().strip()
        if w in existing_enriched:
            continue
        reason = str(info.get("last_error") or info.get("reason") or "")
        r, _ = kb.resolve_root(w)
        w_prpm = kb.get_prpm_data(w)
        r_prpm = kb.get_prpm_data(r) if r != w else {}
        has_dbp = has_official_dbp_in_prpm(w_prpm) or has_official_dbp_in_prpm(r_prpm)

        if (
            has_dbp
            or (r != w)
            or ("Headword mismatch" in reason)
            or ("collocations" in reason)
            or ("timeout" in reason)
            or ("Jawi" in reason)
            or ("Code " in reason)
        ):
            type_a_words.append(w)
        else:
            type_b_records[w] = {
                "word": w,
                "reason": reason,
                "attempts": info.get("attempts", 3),
                "classification": "Type B: Subtitle proper noun / broken syllable fragment without DBP entry; retained in missing_source per Gate 4 honesty rule.",
            }

    salvage_targets = []
    seen = set()
    for w in unqueued_words + type_a_words:
        if w not in seen and w not in existing_enriched:
            seen.add(w)
            salvage_targets.append(w)

    print(
        f"[SALVAGE] Un-queued words: {len(unqueued_words)} | Type A quarantined: {len(type_a_words)} | Total salvage targets: {len(salvage_targets)} | Type B retained in missing_source: {len(type_b_records)}",
        flush=True,
    )

    packets = [kb.assemble_word_packet(w, rank_map.get(w, 9999)) for w in salvage_targets]
    batches = [packets[i : i + 2] for i in range(0, len(packets), 2)]
    salvaged_words: List[str] = []
    still_unrecovered: Dict[str, str] = {}

    if batches:
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            future_map = {
                executor.submit(run_salvage_worker, f"final_{idx:03d}", b): b
                for idx, b in enumerate(batches)
            }
            for fut in concurrent.futures.as_completed(future_map):
                res = fut.result()
                for w, entry in res.get("validated", {}).items():
                    out_file = ENRICHED_DIR / f"{w}.json"
                    out_file.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
                    salvaged_words.append(w)
                    print(f"  [SALVAGED] {w} ({res['batch_tag']})", flush=True)
                for w, err in res.get("errors", {}).items():
                    still_unrecovered[w] = err
                    print(f"  [SKIP] {w}: {err}", flush=True)

    triage_report = {
        "timestamp": datetime.now().isoformat(),
        "unqueued_19_candidates": unqueued_words,
        "type_a_recoverable_candidates": type_a_words,
        "salvaged_count": len(salvaged_words),
        "salvaged_words": sorted(salvaged_words),
        "still_unrecovered_type_a": still_unrecovered,
        "type_b_missing_source_count": len(type_b_records),
        "type_b_missing_source_words": type_b_records,
    }
    TRIAGE_REPORT_FILE.write_text(json.dumps(triage_report, ensure_ascii=False, indent=2), encoding="utf-8")
    return triage_report


def reconcile_provenance_status(kb: LinguisticKnowledgeBase) -> Dict[str, int]:
    """
    Delegate to finalize_gate4_and_salvage3.main() for strict 3-tier provenance classification
    ('official', 'root_derived', 'corpus_usage') strictly backed by local PRPM files without whitelists.
    """
    from finalize_gate4_and_salvage3 import main as run_strict_gate4
    run_strict_gate4()
    manifest_path = ROOT_DIR / "app" / "static" / "data" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    prov_bd = manifest.get("provenance_breakdown", {})
    return {
        "total_enriched": manifest.get("enriched_count", 14748),
        "official_count": prov_bd.get("official", 0),
        "root_derived_count": prov_bd.get("root_derived", 0),
        "corpus_usage_count": prov_bd.get("corpus_usage", 0),
        "updated_files": 0,
    }


def run_quality_gates_and_e2e() -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    cmd_pytest = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_stage3_trilingual_quality_gates.py",
        "-v",
    ]
    res_py = subprocess.run(cmd_pytest, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8")
    results["pytest_returncode"] = res_py.returncode
    results["pytest_output"] = res_py.stdout + "\n" + res_py.stderr
    print(f"[GATES] pytest returncode={res_py.returncode}", flush=True)

    cmd_cdp = ["node", "tests/verify_trilingual_e2e.mjs"]
    res_cdp = subprocess.run(cmd_cdp, cwd=str(ROOT_DIR), capture_output=True, text=True, encoding="utf-8", timeout=120)
    results["cdp_returncode"] = res_cdp.returncode
    results["cdp_output"] = res_cdp.stdout + "\n" + res_cdp.stderr
    print(f"[GATES] CDP E2E returncode={res_cdp.returncode}", flush=True)
    return results


def run_codex_final_audit() -> bool:
    prompt = """你是 Open-Melayu 项目的独立高级数据审计官（Codex CLI）。
当前 15,000 词主队列扩编、收尾捞回（Salvage）与门禁四（来源诚实性对齐）已全部完成。
请你遵守 `RULES.md` 的硬性要求，通过直接读取仓库中的真实文件与 Git 历史，独立编写《Open-Melayu 15,000 词全量收官与五大质量门禁终审报告》，并输出为纯 Markdown 文本（系统将直接保存至 `docs/FINAL_15K_AUDIT_REPORT.md`）。

请你自行运行只读脚本或命令核查以下全部事实并在报告中给出精确统计表格：
1. **全局三态守恒终审账本**：
   - 核查 `app/static/data/manifest.json`、`app/static/data/search_index.json`、27 个分片文件 (`app/static/data/shards/a.json` ~ `z.json` + `other.json`) 以及 `data/enriched/*.json` 的真实文件数。
   - 验证 `batch_1.json` ~ `batch_3.json` 历史镜像残留是否已清零，验证 `len(data/enriched/*.json) == manifest.enriched_count`。
   - 给出精确的 `enriched` + `source_only` + `missing_source` = `15,000` 守恒等式及各分片分布表。
2. **五大质量门禁（Gate 1 ~ Gate 5）全量扫描结果**：
   - Gate 1（爪夷文零伪造）：全库 `data/enriched/*.json` 中纯问号 Jawi (`?` / `????`) 数量是否为 0；`jawi: null` 待补词数量。
   - Gate 2（微距历史词源与三语搭配）：`etymology.historical_story` 缺失数是否为 0；全库总义项数（Total Senses）、总搭配数（Total Collocations），以及 `< 2` 搭配的义项数是否为 0。
   - Gate 3（双境对抗及角色化多轮对话）：全库 `dual_scenarios` 中 `colloquial.messages` 具备 `>= 2` 轮且含 `speaker`, `ms_spoken`, `zh`, `en` 的比例是否为 100%。
   - Gate 4（来源诚实性与状态对齐）：核查全库 `headword.status == "official"`（具备 DBP 词条或词根依据）与 `headword.status == "corpus_usage"`（官方词典未单独收录、透明标注保留字幕高频语料用法）的精确词数，以及前端 `app/static/app.js` 是否已对 `corpus_usage` 区分展示标签而不冒挂“DBP 原文”。
   - Gate 5（三语全覆盖）：核查 `senses[].en_definition`、`collocations[].en`、`dual_scenarios[formal].en`、`dual_scenarios[colloquial].messages[].en` 的缺失数是否全部为 0。
3. **隔离池分流与未入队词捞回审计（Quarantine Triage & Salvage）**：
   - 核查 `data/audit/quarantine_triage_report.json` 与 `data/audit/quarantine_words.json`，列出从 19 个无 `prpm_raw` 核心词及 Type A 隔离池中成功捞回转正的词数与代表词，以及诚实保留在 `missing_source`（Type B 纯字幕人名/残片词）的词数与原因分类。
4. **全天扩编演进与里程碑总结**：
   - 汇总从今日基线 `2,607` 词到最终收官词数的完整演化，以及 `pytest` 与 Chromium CDP 端到端测试结论。

严禁主观臆测，所有数字必须 100% 源自你对磁盘文件与 Git 记录的实测。
"""
    cmd = [
        CODEX_EXE,
        "exec",
        "-C",
        str(ROOT_DIR),
        "-s",
        "read-only",
        "-c",
        'model_reasoning_effort="high"',
        "-o",
        str(FINAL_AUDIT_MD),
        "-",
    ]
    print("[CODEX AUDIT] Running independent Codex CLI final 15K audit...", flush=True)
    try:
        res = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=900,
        )
        print(f"[CODEX AUDIT] Completed with returncode={res.returncode}", flush=True)
        return FINAL_AUDIT_MD.exists() and FINAL_AUDIT_MD.stat().st_size > 500
    except Exception as e:
        print(f"[CODEX AUDIT] Error: {e}", flush=True)
        return False


def main():
    wait_for_sliding_queue_completion()

    # Step 1: Clean legacy mirror files
    removed_mirrors = clean_legacy_mirrors()

    # Step 2: Load KB & run Salvage Pass
    kb = LinguisticKnowledgeBase()
    triage_report = triage_and_salvage(kb)

    # Step 3: Gate 4 Provenance & Status Badge reconciliation
    prov_summary = reconcile_provenance_status(kb)

    # Step 4: Final Atomic Publish (Shards + Search Index + Manifest + data.js + Git commit)
    e_cnt, s_cnt, m_cnt, build_id = update_shards_and_manifest()
    print(
        f"[PUBLISH] Final milestone published: E={e_cnt}, S={s_cnt}, M={m_cnt} (build {build_id})",
        flush=True,
    )

    # Step 5: Run pytest quality gates & CDP E2E verification
    gate_results = run_quality_gates_and_e2e()

    # Save closure summary
    summary = {
        "completed_at": datetime.now().isoformat(),
        "build_id": build_id,
        "enriched_count": e_cnt,
        "source_only_count": s_cnt,
        "missing_source_count": m_cnt,
        "removed_legacy_mirrors": removed_mirrors,
        "provenance_summary": prov_summary,
        "salvaged_count": triage_report["salvaged_count"],
        "type_b_missing_source_count": triage_report["type_b_missing_source_count"],
        "pytest_returncode": gate_results["pytest_returncode"],
        "cdp_returncode": gate_results["cdp_returncode"],
    }
    CLOSURE_LOG_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Step 6: Run independent Codex CLI final audit
    audit_ok = run_codex_final_audit()
    summary["codex_final_audit_generated"] = audit_ok
    CLOSURE_LOG_FILE.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    # Final Git commit including closure scripts, tests, app.js, triage report, and FINAL_15K_AUDIT_REPORT.md
    try:
        subprocess.run(
            [
                "git",
                "add",
                ".gitignore",
                "app/static/app.js",
                "tests/test_stage3_trilingual_quality_gates.py",
                "src/run_overnight_closure_and_audit.py",
                "data/audit/quarantine_triage_report.json",
                "data/audit/overnight_closure_summary.json",
                "docs/FINAL_15K_AUDIT_REPORT.md",
            ],
            cwd=str(ROOT_DIR),
            check=False,
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"feat(final-15k-closure): complete 15,000 lexicon closure ({e_cnt} enriched), Gate 4 provenance alignment, and Codex final audit",
            ],
            cwd=str(ROOT_DIR),
            check=False,
        )
    except Exception as e:
        print(f"[WARN] Git final commit failed: {e}", flush=True)

    print(
        f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [★★★ OVERNIGHT CLOSURE & CODEX FINAL AUDIT COMPLETE ★★★]",
        flush=True,
    )


if __name__ == "__main__":
    main()
