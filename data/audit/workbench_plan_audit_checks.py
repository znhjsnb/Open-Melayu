"""Read-only input audit and isolated legacy-handler probes; no HTTP or database access."""
import ast
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import platform
import statistics

ROOT = Path(__file__).resolve().parents[2]
LEGACY = ROOT.parent / "dict"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def size(value):
    return len(json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def main():
    candidates = load(ROOT / "data/candidate_pool_15k.json")
    normalized = [item["word"].strip().casefold() for item in candidates]
    cache_files = sorted((ROOT / "raw/prpm_cache").glob("*.json"))
    counts = Counter()
    definition_words = set()
    jawi_words = set()
    cache_examples = {}
    for path in cache_files:
        try:
            record = load(path)
            if not isinstance(record, dict):
                counts["non_object"] += 1
                continue
            word = str(record.get("word", "")).strip().casefold()
            if record.get("error"):
                counts["error"] += 1
            if record.get("found_in_prpm"):
                counts["found_flag_true"] += 1
            definition = any(isinstance(record.get(k), str) and record[k].strip()
                             for k in ("kamus_dewan", "kamus_pelajar"))
            if definition:
                counts["dictionary_field_nonempty"] += 1
            if definition and not record.get("error") and word in normalized:
                definition_words.add(word)
                if record.get("jawi"):
                    jawi_words.add(word)
            cache_examples.setdefault("with_dictionary" if definition else "no_dictionary", path.name)
        except (ValueError, UnicodeError):
            counts["parse_error"] += 1

    singles = {}
    lengths = []
    batches = {}
    for path in sorted((ROOT / "data/enriched").glob("*.json")):
        record = load(path)
        if isinstance(record, list):
            batches[path.name] = record
        else:
            word = record["headword"]["word"].strip().casefold()
            if word in singles:
                raise ValueError(f"duplicate enriched headword: {word}")
            singles[word] = record
            lengths.append(size(record))
    batch_items = [item for batch in batches.values() for item in batch]
    batch_equal = all(singles.get(item["headword"]["word"].casefold()) == item for item in batch_items)
    letters = Counter(word[0] if word and word[0] in "abcdefghijklmnopqrstuvwxyz" else "other"
                      for word in normalized)
    reserved = {"con", "prn", "aux", "nul"} | {f"{p}{i}" for p in ("com", "lpt") for i in range(1, 10)}
    reserved_hits = [word for word in normalized if word.split(".")[0] in reserved]

    # Compile only the legacy method, never import server.py or open its SQLite DB.
    server_path = LEGACY / "app/server.py"
    source = server_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    handler = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "LexiconHandler")
    method = next(n for n in handler.body if isinstance(n, ast.FunctionDef) and n.name == "handle_static")
    reconfigure = next(n for n in tree.body if isinstance(n, ast.Expr)
                       and ast.get_source_segment(source, n).startswith("sys.stdout.reconfigure"))
    try:
        exec(compile(ast.Module(body=[reconfigure], type_ignores=[]), str(server_path), "exec"),
             {"sys": type("NoConsole", (), {"stdout": None})()})
        stdout_probe = "unexpected_success"
    except AttributeError as exc:
        stdout_probe = f"{type(exc).__name__}: {exc}"

    class Probe:
        def __init__(self):
            self.wfile = io.BytesIO()
            self.headers = {}
            self.status = None

        def send_response(self, status):
            self.status = status

        def send_header(self, key, value):
            self.headers[key] = value

        def end_headers(self):
            pass

    scratch = ROOT / ".audit-tmp"
    scratch.mkdir(exist_ok=True)
    # Avoid tempfile's Windows owner-only ACL under the managed sandbox.
    base = scratch / "workbench-handler-fixtures"
    base.mkdir(exist_ok=True)
    if base.is_dir():
        static = base / "static"
        sibling = base / "static_backup"
        static.mkdir(exist_ok=True)
        sibling.mkdir(exist_ok=True)
        (static / "index.html").write_text("<h1>shell</h1>", encoding="utf-8")
        (static / "probe.mjs").write_text("export const ok = true;", encoding="utf-8")
        (sibling / "fixture.txt").write_text("ISOLATED_FIXTURE", encoding="utf-8")
        namespace = {"STATIC_DIR": static}
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(server_path), "exec"), namespace)
        probes = {}
        for request in ("/missing.json", "/probe.mjs", "/../static_backup/fixture.txt", "/%2e%2e/static_backup/fixture.txt"):
            probe = Probe()
            namespace["handle_static"](probe, request)
            probes[request] = {"status": probe.status, "type": probe.headers.get("Content-Type"),
                               "body": probe.wfile.getvalue().decode("utf-8")}

    evidence = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "scope": "Input snapshot and extracted-method fixture probes only; no server/browser/SQLite execution",
        "candidates": {"count": len(candidates), "unique_normalized": len(set(normalized)),
                       "sha256": hashlib.sha256((ROOT / "data/candidate_pool_15k.json").read_bytes()).hexdigest(),
                       "reserved_name_hits": reserved_hits, "shard_distribution": dict(sorted(letters.items())),
                       "root_nonnull": sum(bool(x.get("root_word")) for x in candidates),
                       "colloquial_expansion_nonnull": sum(bool(x.get("colloquial_expansion")) for x in candidates)},
        "local_prpm": {"files": len(cache_files), "counts": dict(counts),
                       "candidate_dictionary_words_without_error": len(definition_words),
                       "of_those_with_jawi": len(jawi_words), "examples": cache_examples,
                       "remaining_without_dictionary_field": len(set(normalized) - definition_words),
                       "note": "Nonempty fields are NOT independent evidence of correct query/headword/sense alignment."},
        "enriched": {"unique_words": len(singles), "batch_files": len(batches),
                     "batch_items": len(batch_items), "batch_items_equal_singles": batch_equal,
                     "compact_bytes": {"min": min(lengths), "mean": round(statistics.mean(lengths), 2),
                                       "max": max(lengths)},
                     "projected_15000_bytes_at_sample_mean": round(statistics.mean(lengths) * 15000),
                     "projection_warning": "20 high-frequency entries are not representative of future 15000 entries"},
        "implementation_present": {path: (ROOT / path).exists() for path in (
            "app/server.py", "app/static/worker.js", "app/static/db.js", "app/static/sw.js",
            "src/export_web_shards.py", "RULES.md", "AGENTS.md")},
        "legacy_server_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        "legacy_no_console_probe": stdout_probe,
        "legacy_handle_static_probes": probes,
    }
    output = ROOT / "data/audit/workbench_plan_audit_evidence.json"
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
