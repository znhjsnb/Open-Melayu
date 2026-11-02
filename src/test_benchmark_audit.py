"""Tests for material measurement errors, using isolated temporary inputs."""
import json
import unittest
import uuid
from pathlib import Path

from benchmark_audit import analyze_kaikki, coverage, normalize, read_frequency, read_kaikki


class AuditTests(unittest.TestCase):
    def setUp(self):
        directory = Path(__file__).resolve().parents[1] / ".audit-tmp"
        directory.mkdir(exist_ok=True)
        self.path = directory / f"test-{uuid.uuid4().hex}.txt"

    def tearDown(self):
        self.path.unlink(missing_ok=True)

    def frequency(self, text):
        self.path.write_text(text, encoding="utf-8")
        return read_frequency(self.path)

    def test_normalization_preserves_lexical_boundaries(self):
        self.assertEqual(normalize(" AJAR "), "ajar")
        self.assertEqual(normalize("e\u0301"), normalize("é"))
        self.assertNotEqual(normalize("di rumah"), normalize("dirumah"))
        self.assertNotEqual(normalize("kata-kata"), normalize("katakata"))

    def test_frequency_ligature_collision_keeps_source_ranks(self):
        self.assertEqual(normalize("backﬂip"), "backflip")
        self.assertEqual(self.frequency("backflip 4\nbackﬂip 1\n"), [("backflip", 4), ("backﬂip", 1)])

    def test_reject_corrupt_frequency(self):
        for text in ["tak no\n", "tak 0\n", "tak -1\n", "tak 1\ntak 1\n", "tak 1\nnak 2\n", "\n"]:
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.frequency(text)

    def test_strict_utf8(self):
        self.path.write_bytes(b"tak 1\n\xff")
        with self.assertRaises(UnicodeDecodeError):
            read_frequency(self.path)

    def test_senses_and_casefolded_headwords_are_separate_units(self):
        records = [
            {"word": "Ajar", "pos": "verb", "senses": [{"id": "one", "glosses": ["teach"]}, {"id": "two"}]},
            {"word": "ajar", "pos": "noun", "senses": [{"id": "two"}], "sounds": [{"ipa": "/a/"}]},
        ]
        stats, features = analyze_kaikki(records)
        self.assertEqual((stats["records"], stats["distinct_raw_headwords"], stats["distinct_normalized_headwords"], stats["senses"]), (2, 2, 1, 3))
        self.assertEqual(stats["sense_id_duplicates"], 1)
        self.assertTrue(features["ajar"]["ipa"])

    def test_weighted_coverage_and_type_coverage_differ(self):
        data = coverage([("tak", 90), ("ajar", 10)], {"ajar"}, {"tak"}, {"tak": {"ipa": True}}, 200)
        self.assertEqual(data["type_coverage"]["kaikki"]["pct"], 50)
        self.assertEqual(data["occurrence_coverage_within_top"]["kaikki"]["pct"], 90)
        self.assertEqual(data["share_of_full_occurrences"]["pct"], 50)
        self.assertEqual(data["type_coverage"]["either"]["n"], 2)

    def test_reject_non_malay_record_and_invalid_json(self):
        for text in [json.dumps({"word": "cat", "lang_code": "en", "senses": []}), "{bad"]:
            self.path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                read_kaikki(self.path)


if __name__ == "__main__":
    unittest.main()
