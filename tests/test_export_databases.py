"""Isolated exporter tests; no learning records or production data are touched."""

from contextlib import closing, contextmanager, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import shutil
import string
import unittest
from unittest.mock import patch
import uuid
import zipfile

SPEC = importlib.util.spec_from_file_location("export_databases", Path(__file__).resolve().parents[1] / "src" / "export_databases.py")
exporter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(exporter)
TEMP_ROOT = Path(__file__).resolve().parents[1] / ".tmp"


@contextmanager
def temporary_directory():
    # Python 3.13's Windows mkdtemp applies private ACLs that this sandbox cannot
    # reopen. Use an ordinary directory with inherited workspace permissions.
    TEMP_ROOT.mkdir(exist_ok=True)
    path = TEMP_ROOT / ("export-tests-" + uuid.uuid4().hex)
    path.mkdir()
    try:
        yield path
    finally:
        if path.resolve().parent != TEMP_ROOT.resolve():
            raise ValueError("Refusing to remove a directory outside the test workspace")
        shutil.rmtree(path)


def entry(word, entry_id, state="enriched"):
    return {
        "id": entry_id, "word": word, "data_state": state, "is_enriched": state == "enriched",
        "headword": {"word": word, "jawi": "ساي" if state == "enriched" else None,
                     "ipa": "/sajə/", "syllables": "sa.ya", "status": "official"},
        "morphology": {"root_word": "saya", "root_jawi": "ساي", "formula": "∅ + saya → saya"},
        "senses": [{"id": 1, "pos": "pronoun", "ms_definition": "ganti nama diri",
                    "ms_is_verbatim": False, "zh_definition": "礼貌用语", "en_definition": "polite pronoun",
                    "nuance_note": "边界", "collocations": [{"ms": "nama saya", "zh": "我的名字", "en": "my name"}]}],
        "dual_scenarios": [{"scenario": "formal", "ms": "Saya datang.", "zh": "我来了。", "en": "I arrived."},
                           {"scenario": "colloquial", "spoken_features": ["dah → sudah"], "messages": [
                               {"speaker": "A (同事)", "ms_spoken": "Dah?", "ms_standard": "Sudah?", "zh": "好了吗？", "en": "Done?"},
                               {"speaker": "B (同事)", "ms_spoken": "Ya!", "ms_standard": "Ya!", "zh": "好了！", "en": "Yes!"}]}],
        "spoken_shortcuts": [{"abbr": "sy", "full_form": "saya", "note": "聊天"}],
        "sociolinguistic_register": {"usage_etiquette": "礼貌"},
        "etymology": {"historical_story": "历史", "cognitive_memory_aid": "记忆"},
        "provenance": {"attribution": "DBP PRPM"},
    }


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.root = self.enterContext(temporary_directory())
        self.entries = [entry("saya", 1), entry("pending", 2, "source_only"), entry("unknown", 3, "missing_source")]
        self.entries[2]["senses"] = []

    def test_sqlite_preserves_raw_data_nulls_senses_and_multilingual_fts(self):
        path = self.root / "dictionary.db"
        exporter.export_sqlite(self.entries, path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone(), ("ok",))
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(db.execute("SELECT count(*) FROM words").fetchone(), (3,))
            self.assertEqual(db.execute("SELECT count(*) FROM senses").fetchone(), (2,))
            self.assertIsNone(db.execute("SELECT jawi FROM words WHERE id=3").fetchone()[0])
            self.assertEqual(db.execute("SELECT nuances FROM senses WHERE word_id=1").fetchone(), ("边界",))
            for entry_id, raw in db.execute("SELECT id,raw_json FROM words ORDER BY id"):
                self.assertEqual(json.loads(raw), self.entries[entry_id - 1])
            for query in ("word:saya", "jawi:ساي", "zh_definition:礼貌用语", "en_definition:polite", "ms_definition:ganti", "word:say*"):
                self.assertIn((1,), db.execute("SELECT rowid FROM melayu_fts WHERE melayu_fts MATCH ?", (query,)).fetchall())

    def test_anki_filters_states_and_escapes_html_tsv_controls(self):
        sample = self.entries[0]
        sample["senses"][0]["zh_definition"] = '<script>alert("x")</script>\t甲\r\n乙 & 丙'
        path = self.root / "cards.tsv"
        exporter.export_anki(self.entries, path)
        rows = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].count("\t"), 1)
        front, back = rows[0].split("\t")
        self.assertIn('dir="rtl"', front)
        self.assertIn("ساي", front)
        self.assertNotIn("<script>", back)
        self.assertIn("&lt;script&gt;", back)
        self.assertIn("&amp;", back)
        for content in ("Berita", "WhatsApp", "A (同事)", "B (同事)", "Sudah?", "Done?", "polite pronoun", "nama saya", "my name", "词根 Jawi", "口语速查", "社交礼仪", "历史词源", "记忆法（非词源考据）", "DBP PRPM", "边界"):
            self.assertIn(content, back)
        self.assertIn("基于 DBP 官方词条", back)
        self.assertNotIn("DBP 原文:", back)

    def test_provenance_requires_strict_true_and_official_status(self):
        head, sense = {"status": "official"}, {"ms_is_verbatim": True}
        self.assertEqual(exporter.source_label(head, sense), "DBP 原文:")
        for marker in (False, None, 1, "true"):
            self.assertIn("基于 DBP 官方词条", exporter.source_label(head, {"ms_is_verbatim": marker}))
        self.assertIn("词根推导", exporter.source_label({"status": "root_derived"}, sense))
        self.assertIn("语料用法", exporter.source_label({"status": "corpus_usage"}, sense))

    def test_jsonl_and_archives_keep_complete_payloads_and_web_paths(self):
        path = self.root / "corpus.jsonl"
        exporter.export_jsonl(self.entries, path)
        self.assertEqual([json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()], self.entries)
        archive = self.root / "corpus.zip"
        exporter.archive_files([(path, path.name)], archive)
        with zipfile.ZipFile(archive) as zf:
            self.assertEqual(zf.namelist(), [path.name])
            self.assertEqual(zf.read(path.name), path.read_bytes())
        static = self.root / "static"
        (static / "data" / "shards").mkdir(parents=True)
        (static / "index.html").write_bytes(b"<html>test</html>")
        (static / "data" / "shards" / "a.json").write_bytes(b'{"a":{}}')
        exporter.export_web(static, self.root / "web.zip")
        with zipfile.ZipFile(self.root / "web.zip") as zf:
            self.assertEqual(set(zf.namelist()), {"index.html", "data/shards/a.json"})
            for name in zf.namelist():
                self.assertEqual(zf.read(name), (static / name).read_bytes())

    def test_failed_export_keeps_previous_artifact_and_can_retry(self):
        path = self.root / "dictionary.db"
        path.write_bytes(b"previous artifact")
        bad = deepcopy(self.entries)
        bad[0]["senses"].append(deepcopy(bad[0]["senses"][0]))
        with self.assertRaises(sqlite3.IntegrityError):
            exporter.export_sqlite(bad, path)
        self.assertEqual(path.read_bytes(), b"previous artifact")
        self.assertFalse(path.with_name(path.name + ".tmp").exists())
        exporter.export_sqlite(self.entries, path)
        exporter.export_sqlite(self.entries, path)
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute("SELECT count(*) FROM words").fetchone(), (3,))

    def test_cli_selection_and_zip_rebuild(self):
        with patch.object(exporter, "load_release", return_value=({"build_id": "test", "enriched_count": 1}, self.entries)), patch.object(exporter, "EXPORTS_DIR", self.root), redirect_stdout(io.StringIO()):
            exporter.main(["--anki", "--zip"])
            self.assertEqual({p.name for p in self.root.iterdir()}, {"open_melayu_15k_anki.tsv", "open_melayu_15k_anki.zip"})
            # --zip alone must rebuild, rather than packaging a stale TSV.
            (self.root / "open_melayu_15k_anki.tsv").write_text("stale", encoding="utf-8")
            with patch.object(exporter, "export_web", side_effect=lambda static, path: path.write_bytes(b"web fixture")) as web:
                exporter.main(["--zip"])
                web.assert_called_once()
            self.assertNotEqual((self.root / "open_melayu_15k_anki.tsv").read_text(encoding="utf-8"), "stale")


class ReleaseInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.static = cls.enterClassContext(temporary_directory()) / "static"
        shards = cls.static / "data" / "shards"
        shards.mkdir(parents=True)
        cls.manifest = {"build_id": "fixture", "total_words": 15000, "format_version": 2,
                        "conservation_check": True, "enriched_count": 0, "source_only_count": 0,
                        "missing_source_count": 15000, "provenance_breakdown": {}}
        (cls.static / "data.js").write_text("export const DATA_VERSION = 'fixture';", encoding="utf-8")
        (cls.static / "data" / "manifest.json").write_text(json.dumps(cls.manifest), encoding="utf-8")
        entries = {}
        index = []
        for n in range(1, 15001):
            word = f"a{n}"
            entries[word] = {"id": n, "word": word, "headword": {"word": word},
                             "is_enriched": False, "data_state": "missing_source"}
            index.append({"id": n, "w": word, "st": "m", "e": 0})
        for key in [*string.ascii_lowercase, "other"]:
            (shards / f"{key}.json").write_text(json.dumps(entries if key == "a" else {}), encoding="utf-8")
        (cls.static / "data" / "search_index.json").write_text(json.dumps(index), encoding="utf-8")

    def test_loads_only_static_tree_without_local_enriched_sources(self):
        manifest, entries = exporter.load_release(self.static)
        self.assertEqual(manifest, self.manifest)
        self.assertEqual([e["id"] for e in entries], list(range(1, 15001)))

    def test_preserves_display_capitalization(self):
        original = exporter.read_json

        def capitalized(path):
            data = original(path)
            if path.name == "a.json":
                data["a1"]["headword"]["word"] = "A1"
            return data

        with patch.object(exporter, "read_json", side_effect=capitalized):
            _, entries = exporter.load_release(self.static)
        self.assertEqual(entries[0]["word"], "a1")
        self.assertEqual(entries[0]["headword"]["word"], "A1")

    def test_rejects_corrupt_release_before_generating_artifacts(self):
        cases = ("version", "count", "id", "state", "index", "headword", "provenance")
        original = exporter.read_json
        for case in cases:
            def corrupted(path):
                data = original(path)
                if path.name == "manifest.json":
                    if case == "version":
                        data["build_id"] = "wrong"
                    elif case == "count":
                        data["enriched_count"] = 1
                    elif case == "provenance":
                        data["provenance_breakdown"] = {"official": 1}
                if path.name == "a.json":
                    if case == "id":
                        data["a2"]["id"] = 1
                    elif case == "state":
                        data["a1"]["is_enriched"] = True
                    elif case == "headword":
                        data["a1"]["headword"]["word"] = "wrong"
                if path.name == "search_index.json" and case == "index":
                    data[1] = data[0]
                return data
            with self.subTest(case=case), patch.object(exporter, "read_json", side_effect=corrupted):
                with self.assertRaises(ValueError):
                    exporter.load_release(self.static)
        with patch.object(Path, "glob", return_value=[]):
            with self.assertRaisesRegex(ValueError, "27 shards"):
                exporter.load_release(self.static)


if __name__ == "__main__":
    unittest.main()
