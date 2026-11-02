"""Offline reproductions for the distributed crawler plan audit; no network calls."""
from __future__ import annotations

import collections
import contextlib
import hashlib
import io
import json
import ntpath
from pathlib import Path
import subprocess
import sys
import uuid
import unicodedata
import urllib.error
from unittest.mock import patch
from datetime import datetime, timezone

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "src/vultr_cloud_init.sh"
source = SCRIPT.read_text(encoding="utf-8")
worker = source.split("cat << 'PYEOF' > \"$WORKDIR/worker.py\"\n", 1)[1].split("\nPYEOF", 1)[0]
compile(worker, "embedded_worker.py", "exec")
result = {
    "observed_at_utc": datetime.now(timezone.utc).isoformat(),
    "scope": "Offline mocks, local inputs, Git Bash; not an Ubuntu or live VPS benchmark",
    "script_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    "input_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT / "docs/PLAN_DISTRIBUTED_CRAWLER_AND_CODEX.md", ROOT / "src/batch_synthesizer.py", ROOT / "src/prpm_continuous_crawler.py", ROOT / "data/candidate_pool_15k.json"]},
    "script_crlf_count": SCRIPT.read_bytes().count(b"\r\n"),
    "worker_compiles": True,
}


class Response:
    def __init__(self, html):
        self.html = html.encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.html


def run_worker(base, words, response=None, failure=None, existing=None):
    base.mkdir()
    out = base / "out"
    out.mkdir()
    wordlist = base / "words.txt"
    wordlist.write_text("\n".join(words), encoding="utf-8")
    for name, content in (existing or {}).items():
        (out / name).write_text(content, encoding="utf-8")
    args = ["worker.py", "1", "5", str(out), str(wordlist)]
    kwargs = {"side_effect": failure} if failure else {"return_value": Response(response or "")}
    with patch.object(sys, "argv", args), patch("urllib.request.urlopen", **kwargs) as request, patch("time.sleep") as sleep, contextlib.redirect_stdout(io.StringIO()):
        ns = {}
        exec(compile(worker, "embedded_worker.py", "exec"), ns)
    return {
        "requests": request.call_count,
        "completed": ns["completed"],
        "found_count_variable": ns["found_count"],
        "sleep_calls": [call.args[0] for call in sleep.call_args_list],
        "status": (out / "status.txt").read_text(encoding="utf-8"),
        "files": {p.name: p.read_text(encoding="utf-8") for p in out.glob("*.json")},
    }


scratch = ROOT / ".audit-tmp"
scratch.mkdir(exist_ok=True)
test_directory = scratch / ("plan_audit_" + uuid.uuid4().hex)
test_directory.mkdir()
with contextlib.nullcontext(test_directory) as td:
    temp = Path(td)
    page = "<html><title>Temporarily unavailable</title><body>Maintenance</body></html>"
    result["http_200_maintenance"] = run_worker(temp / "maintenance", ["sample"], response=page)
    assert result["http_200_maintenance"]["found_count_variable"] == 1
    assert not json.loads(result["http_200_maintenance"]["files"]["sample.json"])["found_in_prpm"]
    result["http_503"] = run_worker(temp / "failure", ["sample"], failure=urllib.error.HTTPError("https://offline.invalid", 503, "Unavailable", {}, None))
    assert result["http_503"]["requests"] == 3
    assert "COMPLETED" in result["http_503"]["status"]
    error_file = result["http_503"]["files"]["sample.json"]
    result["restart_error_cache"] = run_worker(temp / "restart", ["sample"], existing={"sample.json": error_file})
    assert result["restart_error_cache"]["requests"] == 0
    result["restart_corrupt_cache"] = run_worker(temp / "corrupt", ["sample"], existing={"sample.json": "{"})
    assert result["restart_corrupt_cache"]["requests"] == 0
    result["unrelated_pane"] = run_worker(temp / "pane", ["sample"], response='<div class="tab-pane">Tiada maklumat dijumpai</div>')
    assert json.loads(result["unrelated_pane"]["files"]["sample.json"])["found_in_prpm"]
    result["phonetic_and_jawi_markup"] = run_worker(temp / "markup", ["awak"], response='<div class="tab-pane">[a.waʔ] <span class="cadr">اوق</span> Definisi : ... (Kamus Dewan Edisi Keempat)</div>')
    markup = json.loads(result["phonetic_and_jawi_markup"]["files"]["awak.json"])
    assert markup["syllables"] is None and markup["jawi"] is None
    result["combined_dictionary_pane"] = run_worker(temp / "combined", ["sample"], response='<div class="tab-pane">Definisi : A (Kamus Dewan) Definisi : B (Kamus Pelajar)</div>')
    combined = json.loads(result["combined_dictionary_pane"]["files"]["sample.json"])
    assert combined["kamus_dewan"] and combined["kamus_pelajar"] is None
    snapshot = ROOT / ".audit-tmp/sample_dia.html"
    if snapshot.exists():
        result["saved_dia_html"] = run_worker(temp / "dia", ["dia"], response=snapshot.read_text(encoding="utf-8"))
        result["saved_dia_html"]["fixture_sha256"] = hashlib.sha256(snapshot.read_bytes()).hexdigest()
    bash = Path("C:/Program Files/Git/bin/bash.exe")
    if bash.exists():
        def shell(text):
            p = subprocess.run([str(bash), "--noprofile", "--norc", "-s"], input=text, text=True, encoding="utf-8", capture_output=True, timeout=15)
            return {"exit_code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()}

        check = subprocess.run([str(bash), "--noprofile", "--norc", "-n"], input=source, text=True, encoding="utf-8", capture_output=True, timeout=15)
        result["bash_syntax"] = {"exit_code": check.returncode, "stderr": check.stderr}
        if check.returncode != 0:
            result["bash_runtime_tests"] = "NOT RUN: Bash unavailable or sandbox blocked its startup; shell conclusions require static reasoning and Ubuntu verification"
            bash = None
    if bash:
        shard_code = source.split("# 3. Identify Shard from Hostname\n", 1)[1].split("# 4. Fetch", 1)[0]
        result["hostnames"] = {}
        for name in ["spider-1", "spider-01", "spider-08", "vultr-guest", "spider-6", "region2-spider-5", "spider-2.example9"]:
            result["hostnames"][name] = shell("set -e\nhostname() { printf '%s\\n' '" + name + "'; }\n" + shard_code + '\nprintf "shard=%s index=%s\\n" "$SHARD_NUM" "$SHARD_INDEX"\n')
        result["apt_update_and_list_set_e"] = shell("set -e\nfalse && echo install\necho CONTINUED_AFTER_UPDATE_FAILURE\n")
        result["tar_cases"] = {}
        for label, filenames in [("normal", ["a.json", "b.json"]), ("empty", []), ("hidden", [".word.json", "a.json"])]:
            directory = temp / ("tar_" + label)
            directory.mkdir()
            for name in filenames:
                (directory / name).write_text("{}", encoding="utf-8")
            code = 'cd "' + directory.as_posix() + '"\ntar -czf shard_1.tar.gz --exclude="*.tar.gz" --exclude="status.txt" *.json\nrc=$?\nprintf "tar_exit=%s\\n" "$rc"\ntar -tzf shard_1.tar.gz\n'
            result["tar_cases"][label] = shell(code)

pool = json.loads((ROOT / "data/candidate_pool_15k.json").read_text(encoding="utf-8"))
words = [item["word"] for item in pool]
groups = collections.defaultdict(list)
for w in words:
    groups[unicodedata.normalize("NFC", w).casefold()].append(w)
result["candidate_pool"] = {
    "count": len(words),
    "unique": len(set(words)),
    "non_lowercase_count": sum(w != w.lower() for w in words),
    "nfc_casefold_collisions": [v for v in groups.values() if len(v) > 1],
    "windows_reserved": [w for w in words if ntpath.isreserved(w + ".json")],
    "leading_dash": [w for w in words if w.startswith("-")],
    "leading_dot": [w for w in words if w.startswith(".")],
}
payload = ROOT / ".audit-tmp/gist_payload.json"
if payload.exists():
    content = json.loads(payload.read_text(encoding="utf-8-sig"))["files"]["candidate_words_15k.txt"]["content"]
    result["local_gist_upload_payload"] = {
        "remote_revision_verified": False,
        "bytes_utf8": len(content.encode("utf-8")),
        "sha256_utf8": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "lines": len(content.splitlines()),
        "matches_local_candidate_word_order": content.splitlines() == words,
    }
counts = collections.Counter()
examples = collections.defaultdict(list)
for file in (ROOT / "raw/prpm_cache").glob("*.json"):
    try:
        item = json.loads(file.read_text(encoding="utf-8"))
        status = "error" if item.get("error") else ("found_flag" if item.get("found_in_prpm") else "not_found_flag")
    except Exception:
        status = "invalid_json"
    counts[status] += 1
    if len(examples[status]) < 5:
        examples[status].append(file.name)
result["local_cache_snapshot"] = {"counts": dict(counts), "examples": dict(examples), "possibly_concurrently_written": True}
result["scheduler_exists"] = (ROOT / "src/concurrent_synthesizer.py").exists()
out = ROOT / "data/audit/plan_audit_evidence.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"evidence": str(out.relative_to(ROOT)), "candidate_pool": result["candidate_pool"], "cache": result["local_cache_snapshot"], "hostnames": result.get("hostnames"), "bash_syntax": result.get("bash_syntax"), "tar_cases": result.get("tar_cases"), "gist_payload": result.get("local_gist_upload_payload")}, ensure_ascii=False, indent=2))
