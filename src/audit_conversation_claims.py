"""Read-only snapshot/check of the English project's claims in the audit handoff.

Copies only its static app and two tests into this workspace before running Node,
because those tests write a report. Never changes the source project.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def fingerprint(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args, cwd):
    result = subprocess.run(args, cwd=cwd, capture_output=True, encoding="utf-8", errors="replace", timeout=120)
    return {"args": args, "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT.parent / "dict")
    args = parser.parse_args()
    source = args.source.resolve()
    mirror = ROOT / ".audit-tmp" / "dict-check"
    mirror.mkdir(parents=True, exist_ok=True)
    (mirror / "tests").mkdir(exist_ok=True)
    shutil.copytree(source / "app" / "static", mirror / "app" / "static", dirs_exist_ok=True)
    for name in ["frontend.test.mjs", "frontend.interactions.test.mjs"]:
        shutil.copyfile(source / "tests" / name, mirror / "tests" / name)
    pairs = [(p, mirror / p.relative_to(source)) for p in (source / "app" / "static").rglob("*") if p.is_file()]
    pairs += [(source / "tests" / name, mirror / "tests" / name) for name in ["frontend.test.mjs", "frontend.interactions.test.mjs"]]
    hashes = {str(p.relative_to(source)).replace("\\", "/"): fingerprint(p) for p, _ in pairs}
    assert all(fingerprint(p) == fingerprint(q) for p, q in pairs), "Mirror differs from source"
    dataset = source / "app" / "static" / "data"
    index = json.loads((dataset / "search_index.json").read_text(encoding="utf-8"))
    shards = sorted((dataset / "shards").glob("*.json"))
    words = []
    senses = 0
    for path in shards:
        entries = json.loads(path.read_text(encoding="utf-8"))
        words.extend(entries)
        senses += sum(len(e.get("senses", [])) for e in entries.values())
    tests = ["node", "--test", "tests/frontend.test.mjs", "tests/frontend.interactions.test.mjs"]
    checks = [command(tests, mirror)]
    if checks[0]["exit_code"] and "EPERM" in (checks[0]["stdout"] + checks[0]["stderr"]):
        checks.append(command(["node", "--test", "--experimental-test-isolation=none", *tests[2:]], mirror))
    assert all(fingerprint(p) == hashes[str(p.relative_to(source)).replace("\\", "/")] for p, _ in pairs), "Source changed during verification"
    evidence = {
        "source": str(source), "isolation": "Byte-identical copy of static app and unmodified tests in current workspace; test output writes only to mirror",
        "node": command(["node", "--version"], mirror),
        "git_status": command(["git", "--no-optional-locks", "status", "--short", "--branch"], source),
        "git_head": command(["git", "rev-parse", "HEAD"], source),
        "git_origin_main_tracking": command(["git", "rev-parse", "origin/main"], source),
        "asset_counts": {"index_entries": len(index), "shards": len(shards), "headwords": len(words), "distinct_headwords": len(set(words)), "senses": senses},
        "source_sha256": hashes, "node_test_runs": checks,
    }
    output = ROOT / "data" / "audit" / "conversation_checks.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence["asset_counts"]))
    for check in checks:
        print(" ".join(check["args"]), "exit:", check["exit_code"])
        print("\n".join(check["stdout"].splitlines()[-12:]))
    print("Evidence:", output)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
