"""Read-only evidence collection; never starts crawlers or model workers.

Writes only data/audit/full_conversation_evidence.json. Optional historical log
is restricted to step_index <= 987; no credentials or tool arguments exported.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import unicodedata

ROOT = Path(__file__).resolve().parents[1]


def norm(value):
    return unicodedata.normalize("NFC", value).strip().casefold()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rate(n, d):
    return {"n": n, "d": d, "pct": round(100 * n / d, 6) if d else None}


def collect(history=None, probe_ip=False):
    inputs = ["docs/FULL_CONVERSATION_FOR_AUDIT.md", "src/prpm_continuous_crawler.py",
              "src/prpm_client.py", "src/batch_synthesizer.py", "src/status_dashboard.py",
              "src/build_candidate_pool.py", "docs/PLAN_DISTRIBUTED_CRAWLER_AND_CODEX.md",
              "raw/dbp_malay_words_v2.json", "raw/kaikki_malay.jsonl",
              "raw/opensubtitles_frequency_ms_full.txt", "data/candidate_pool_15k.json",
              "data/crawler_progress.json"]
    out = {"observed_at_utc": datetime.now(timezone.utc).isoformat(),
           "input_sha256": {p: digest(ROOT / p) for p in inputs}}
    text = (ROOT / inputs[0]).read_text(encoding="utf-8")
    heads = list(re.finditer(r"^## Step (\d+) \| ([^(\n]+)\(([^\n]+)\)$", text, re.M))
    ids = [int(m[1]) for m in heads]
    out["transcript_export"] = {
        "declared_steps": 988, "heading_count": len(heads),
        "unique_step_ids": len(set(ids)), "min": min(ids), "max": max(ids),
        "duplicate_step_ids": {str(k): v for k, v in Counter(ids).items() if v > 1},
        "explicit_truncation_markers": re.findall(r"<truncated [^>]+>", text),
        "tool_placeholder_count": text.count("*(Tool Calls:"),
        "narrative_index": [{"step": int(m[1]), "role": m[2].strip(),
                             "time": m[3], "line": text[:m.start()].count("\n") + 1}
                            for i, m in enumerate(heads)
                            if "*(Tool Calls:" not in text[m.end():heads[i+1].start() if i+1 < len(heads) else len(text)]]}
    dbp_raw = json.loads((ROOT / "raw/dbp_malay_words_v2.json").read_text(encoding="utf-8"))
    dbp = {norm(x) for x in dbp_raw}
    records = [json.loads(x) for x in (ROOT / "raw/kaikki_malay.jsonl").read_text(encoding="utf-8").splitlines() if x.strip()]
    kaikki = {norm(x["word"]) for x in records}
    frequencies = [(w, int(c)) for line in (ROOT / "raw/opensubtitles_frequency_ms_full.txt").read_text(encoding="utf-8").splitlines()
                   if line.strip() for w, c in [line.rsplit(maxsplit=1)]]
    intersection, union = dbp & kaikki, dbp | kaikki
    out["sources"] = {"dbp_raw_strings": len(dbp_raw), "dbp_normalized": len(dbp),
                      "kaikki_records": len(records), "kaikki_normalized": len(kaikki),
                      "kaikki_senses": sum(len(x.get("senses", [])) for x in records),
                      "frequency_rows": len(frequencies), "intersection": len(dbp & kaikki),
                      "dbp_only": len(dbp - kaikki), "kaikki_only": len(kaikki - dbp),
                      "union": len(dbp | kaikki), "coverage": {}}
    for n in [1000, 3000, 5000, 15000]:
        words = [norm(w) for w, _ in frequencies[:n]]
        out["sources"]["coverage"][str(n)] = {
            "dbp": rate(sum(w in dbp for w in words), n),
            "kaikki": rate(sum(w in kaikki for w in words), n),
            "both": rate(sum(w in intersection for w in words), n),
            "union": rate(sum(w in union for w in words), n),
            "neither": rate(sum(w not in union for w in words), n),
            "subtitle_frequency_mass_share": rate(sum(c for _, c in frequencies[:n]), sum(c for _, c in frequencies))}
    pool = json.loads((ROOT / "data/candidate_pool_15k.json").read_text(encoding="utf-8"))
    out["candidate_pool"] = {
        "type": type(pool).__name__, "count": len(pool),
        "unique_words": len({x["word"] for x in pool}),
        "fields": dict(Counter(k for x in pool for k in x)),
        "ranks_contiguous_1_to_15000": [x["rank"] for x in pool] == list(range(1, 15001)),
        "matches_frequency_prefix": [(x["word"], x["frequency_count"]) for x in pool] == frequencies[:15000],
        "flags": {k: sum(bool(x.get(k)) for x in pool) for k in ["in_dbp", "in_kaikki", "has_tatoeba", "ipa", "root_word", "colloquial_expansion"]},
        "first_20_words": [x["word"] for x in pool[:20]],
        "windows_reserved": [x["word"] for x in pool if x["word"].split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(1, 10)], *[f"LPT{i}" for i in range(1, 10)]}]}
    cache_files = sorted((ROOT / "raw/prpm_cache").glob("*.json"))
    before = {p.name: digest(p) for p in cache_files}
    counts, examples, cache = Counter(), defaultdict(list), {}
    for p in cache_files:
        try:
            item = json.loads(p.read_text(encoding="utf-8"))
            assert isinstance(item, dict)
        except (ValueError, AssertionError):
            counts["invalid_json"] += 1
            continue
        cache[item.get("word", p.stem)] = item
        counts["parsed"] += 1
        status = "error" if item.get("error") else "found_flag" if item.get("found_in_prpm") else "not_found_flag"
        counts[status] += 1
        if len(examples[status]) < 12:
            examples[status].append(p.name)
        for k in ["syllables", "jawi", "kamus_dewan", "kamus_pelajar", "raw_definitions"]:
            if item.get(k):
                counts[k] += 1
        if item.get("kamus_dewan") or item.get("kamus_pelajar"):
            counts["any_dictionary_field"] += 1
        if all(item.get(k) for k in ["syllables", "jawi"]) and (item.get("kamus_dewan") or item.get("kamus_pelajar")):
            counts["syllables_jawi_any_dictionary"] += 1
    after_files = sorted((ROOT / "raw/prpm_cache").glob("*.json"))
    out["cache"] = {"json_files": len(cache_files), "directory_entries": len(list((ROOT / "raw/prpm_cache").iterdir())),
                    "counts": dict(counts), "examples": dict(examples),
                    "field_rates_over_all_json": {k: rate(counts[k], len(cache_files)) for k in ["found_flag", "syllables", "jawi", "kamus_dewan", "kamus_pelajar", "any_dictionary_field", "syllables_jawi_any_dictionary"]},
                    "snapshot_stable_during_read": before == {p.name: digest(p) for p in after_files},
                    "file_sha256": before}
    pilot = json.loads((ROOT / "data/pilot_50_candidates.json").read_text(encoding="utf-8"))
    out["pilot_cache"] = {"n": len(pilot), **{k: sum(bool(cache.get(x["word"], {}).get(k)) for x in pilot) for k in ["found_in_prpm", "syllables", "jawi", "kamus_dewan", "kamus_pelajar"]},
                          "no_dictionary_words": [x["word"] for x in pilot if not any(cache.get(x["word"], {}).get(k) for k in ["kamus_dewan", "kamus_pelajar"])]}
    progress = json.loads((ROOT / "data/crawler_progress.json").read_text(encoding="utf-8"))
    out["progress"] = {"stored": progress,
                       "attempted_words_per_hour": 3600 * progress["crawled_this_session"] / progress["elapsed_seconds"],
                       "found_flags_per_hour": 3600 * progress["found_this_session"] / progress["elapsed_seconds"]}
    out["batch_assets"] = {}
    for i in [1, 2]:
        batch = json.loads((ROOT / f"data/enriched/batch_{i}.json").read_text(encoding="utf-8"))
        out["batch_assets"][str(i)] = {"entries": len(batch), "senses": sum(len(x["senses"]) for x in batch),
            "scenarios": sum(len(x["dual_scenarios"]) for x in batch),
            "individual_files_identical": all(x == json.loads((ROOT / f'data/enriched/{x["headword"]["word"]}.json').read_text(encoding="utf-8")) for x in batch)}
    out["concurrent_scheduler_exists"] = (ROOT / "src/concurrent_synthesizer.py").exists()
    out["calculations"] = {"single_request_11_3s_plus_jitter_1_05s": 3600 / 12.35,
        "hypothetical_7s_plus_11_3s_plus_1_05s": 3600 / 19.35,
        "hypothetical_7s_plus_11_3s_without_jitter": 3600 / 18.3,
        "ideal_25_workers_11_3s_plus_0_55s": 25 * 3600 / 11.85,
        "batch1_10_words_693s": 10 * 3600 / 693,
        "batch1_linear_20_workers_unmeasured": 20 * 10 * 3600 / 693,
        "hours_15k_at_3600": 15000 / 3600}
    if history and history.exists():
        rows = [json.loads(x) for x in history.read_text(encoding="utf-8").splitlines() if x.strip()]
        scoped = [x for x in rows if x.get("step_index", 999999) <= 987]
        selected = {}
        for s in [747, 797, 812, 832, 834, 838, 839, 846, 848, 853, 883, 984, 986, 987]:
            selected[str(s)] = [{"type": x.get("type"), "created_at": x.get("created_at"),
                                 "content": x.get("content", "")} for x in scoped if x.get("step_index") == s]
        out["history"] = {"path": str(history), "sha256_at_read": digest(history),
                          "scope_max_step": 987, "rows_in_scope": len(scoped),
                          "unique_step_ids": len({x.get("step_index") for x in scoped}),
                          "type_counts": dict(Counter(x.get("type") for x in scoped)),
                          "selected_evidence": selected}
        checkpoint = next((x.get("content", "") for x in scoped if x.get("step_index") == 797), "")
        match = re.search(r'\{\s*"total_candidates".*?\}', checkpoint, re.S)
        if match:
            historical_progress = json.loads(match[0])
            out["history"]["step_797_checkpoint"] = {
                "stored": historical_progress,
                "attempted_words_per_hour": 3600 * historical_progress["crawled_this_session"] / historical_progress["elapsed_seconds"],
                "found_flags_per_hour": 3600 * historical_progress["found_this_session"] / historical_progress["elapsed_seconds"]}
    # Compile only the parser function: no module-level paths, writes or network.
    from bs4 import BeautifulSoup
    import urllib.parse
    tree = ast.parse((ROOT / "src/prpm_continuous_crawler.py").read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "fetch_prpm_word")
    scope = {"re": re, "urllib": urllib, "BeautifulSoup": BeautifulSoup}
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<isolated-parser>", "exec"), scope)
    parser_cases = {}
    for name, html in {
        "unrelated_tab": '<div class="tab-pane">Tiada maklumat dijumpai</div>',
        "unicode_phonetic_and_span_jawi": '<div class="tab-pane">[a.wa\u0294] <span class="cadr">\u0627\u0648\u0642</span> Definisi : X (Kamus Dewan)</div>',
        "two_dictionaries_one_pane": '<div class="tab-pane">Definisi : X (Kamus Dewan) Definisi : Y (Kamus Pelajar)</div>',
    }.items():
        scope["make_request"] = lambda *args, **kwargs: html
        parser_cases[name] = scope["fetch_prpm_word"]("awak")
    assert parser_cases["unrelated_tab"]["found_in_prpm"] is True
    assert parser_cases["unicode_phonetic_and_span_jawi"]["syllables"] is None
    assert parser_cases["unicode_phonetic_and_span_jawi"]["jawi"] is None
    assert parser_cases["two_dictionaries_one_pane"]["kamus_pelajar"] is None
    out["offline_parser_reproductions"] = parser_cases
    if probe_ip:
        proc = subprocess.run(["curl.exe", "--connect-timeout", "5", "--max-time", "15", "--silent", "--show-error", "https://api.ipify.org"],
                              capture_output=True, text=True, timeout=20)
        out["current_ip_probe"] = {"command": "curl.exe --connect-timeout 5 --max-time 15 --silent --show-error https://api.ipify.org",
                                   "exit_code": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
                                   "meaning": "Current sandbox only; does not determine historical PRPM egress"}
    return out


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path)
    parser.add_argument("--probe-ip", action="store_true")
    args = parser.parse_args()
    evidence = collect(args.history, args.probe_ip)
    target = ROOT / "data/audit/full_conversation_evidence.json"
    target.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(target))
