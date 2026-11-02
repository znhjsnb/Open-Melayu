"""Reproducible local asset audit. No network calls and no raw-file writes.

Run: python src/benchmark_audit.py
Requires pyarrow; see requirements-audit.txt. All text decoding is strict UTF-8.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTER_TAGS = {"colloquial", "informal", "slang", "Internet", "nonstandard", "text-messaging"}
MORPH_TEMPLATES = {"af", "affix", "prefix", "suffix", "confix", "circumfix", "infix", "compound", "reduplication"}
SOURCES = {
    "dbp_malay_words_v2.json": "https://huggingface.co/datasets/malaysia-ai/DBP/resolve/main/malay-words-v2.json",
    "kaikki_malay.jsonl": "https://kaikki.org/dictionary/Malay/kaikki.org-dictionary-Malay.jsonl",
    "opensubtitles_frequency_ms_full.txt": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/ms/ms_full.txt",
    "opensubtitles_frequency_ms_50k.txt": "https://raw.githubusercontent.com/hermitdave/FrequencyWords/master/content/2018/ms/ms_50k.txt",
    "entries-ms.parquet": "https://huggingface.co/datasets/miserableface/kaikki-melayu-entries/resolve/main/entries-ms.parquet",
    "wordnet-ms.parquet": "https://huggingface.co/datasets/miserableface/melayu-wordnet/resolve/main/wordnet-ms.parquet",
}


def normalize(text: str) -> str:
    return unicodedata.normalize("NFC", text).strip().casefold()


def ratio(numerator: int, denominator: int) -> dict:
    return {"n": numerator, "d": denominator,
            "pct": round(100 * numerator / denominator, 6) if denominator else None}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def read_frequency(path: Path) -> list[tuple[str, int]]:
    rows = []
    seen = set()
    previous = None
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            parts = line.strip().rsplit(maxsplit=1)
            if len(parts) != 2 or not parts[1].isdigit():
                raise ValueError(f"{path}:{line_number}: expected token and positive count")
            word, count = parts[0], int(parts[1])
            key = normalize(word)
            if not key or count <= 0 or word in seen:
                raise ValueError(f"{path}:{line_number}: empty/duplicate token or non-positive count")
            if previous is not None and count > previous:
                raise ValueError(f"{path}:{line_number}: counts must be non-increasing")
            previous = count
            seen.add(word)
            rows.append((word, count))
    return rows


def read_kaikki(path: Path) -> list[dict]:
    records = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            row = json.loads(line)
            if (not isinstance(row.get("word"), str) or not row["word"].strip()
                    or not isinstance(row.get("senses"), list)
                    or row.get("lang_code") != "ms"):
                raise ValueError(f"{path}:{number}: invalid Malay entry")
            records.append(row)
    return records


def has_ipa(row: dict) -> bool:
    return any(s.get("ipa") for s in row.get("sounds", []))


def has_audio(row: dict) -> bool:
    return any(s.get("audio") or s.get("ogg_url") or s.get("mp3_url") for s in row.get("sounds", []))


def has_examples(row: dict) -> bool:
    return any(e.get("text") for s in row.get("senses", []) for e in s.get("examples", []))


def has_morph_template(row: dict) -> bool:
    return any(t.get("name", "").removesuffix("+") in MORPH_TEMPLATES
               for t in row.get("etymology_templates", []))


def entry_features(row: dict) -> dict[str, bool]:
    return {
        "ipa": has_ipa(row), "audio_reference": has_audio(row),
        "syllabification": bool(row.get("hyphenation") or row.get("hyphenations")),
        "etymology_text": bool(row.get("etymology_text")),
        "morphology_template_candidate": has_morph_template(row),
        "examples": has_examples(row),
        "jawi_form": any("Jawi" in f.get("tags", []) for f in row.get("forms", [])),
        "derived_links": bool(row.get("derived")) or any(s.get("derived") for s in row.get("senses", [])),
        "register_marked": any(REGISTER_TAGS.intersection(s.get("tags", [])) for s in row.get("senses", [])),
    }


def analyze_kaikki(rows: list[dict]) -> tuple[dict, dict]:
    by_word = defaultdict(list)
    for row in rows:
        by_word[normalize(row["word"])].append(row)
    senses = [s for row in rows for s in row["senses"]]
    examples = [e for s in senses for e in s.get("examples", []) if e.get("text")]
    features = {}
    for word, word_rows in by_word.items():
        measured = [entry_features(r) for r in word_rows]
        features[word] = {key: any(f[key] for f in measured) for key in measured[0]}
    sense_id_rows = defaultdict(list)
    for number, row in enumerate(rows, 1):
        for s in row["senses"]:
            sense_id_rows[s["id"]].append({"line": number, "word": row["word"], "pos": row["pos"], "glosses": s.get("glosses", [])})
    tags = Counter(t for s in senses for t in s.get("tags", []))
    morphology_templates = Counter(t.get("name", "") for r in rows for t in r.get("etymology_templates", []))
    gloss_scripts = Counter()
    for s in senses:
        for g in s.get("glosses", []):
            if re.search(r"[\u3400-\u9fff]", g):
                gloss_scripts["gloss_strings_with_han_characters"] += 1
    return {
        "records": len(rows), "distinct_raw_headwords": len({r["word"] for r in rows}),
        "distinct_normalized_headwords": len(by_word), "senses": len(senses),
        "records_with_multiple_senses": sum(len(r["senses"]) > 1 for r in rows),
        "sense_id_duplicates": len(senses) - len({s["id"] for s in senses}),
        "duplicated_sense_ids": {key: items for key, items in sense_id_rows.items() if len(items) > 1},
        "pos_records": dict(sorted(Counter(r["pos"] for r in rows).items())),
        "record_features": {key: ratio(sum(entry_features(r)[key] for r in rows), len(rows))
                            for key in entry_features(rows[0])},
        "headword_features": {key: ratio(sum(f[key] for f in features.values()), len(by_word))
                              for key in entry_features(rows[0])},
        "sense_features": {
            "glosses": ratio(sum(bool(s.get("glosses")) for s in senses), len(senses)),
            "examples": ratio(sum(any(e.get("text") for e in s.get("examples", [])) for s in senses), len(senses)),
            "two_or_more_examples": ratio(sum(sum(bool(e.get("text")) for e in s.get("examples", [])) >= 2 for s in senses), len(senses)),
            "alt_of": ratio(sum(bool(s.get("alt_of")) for s in senses), len(senses)),
            "form_of": ratio(sum(bool(s.get("form_of")) for s in senses), len(senses)),
        },
        "example_text_count": len(examples),
        "examples_with_translation": ratio(sum(bool(e.get("translation")) for e in examples), len(examples)),
        "example_keys": dict(sorted(Counter(k for e in examples for k in e).items())),
        "example_types": dict(sorted(Counter(e.get("type", "<missing>") for e in examples).items())),
        "example_tags": dict(sorted(Counter(t for e in examples for t in e.get("tags", [])).items())),
        "gloss_script_diagnostic_not_language_detection": dict(gloss_scripts),
        "sense_tags": dict(sorted(tags.items())), "register_tag_allowlist": sorted(REGISTER_TAGS),
        "etymology_template_names": dict(sorted(morphology_templates.items())),
        "top_level_keys": dict(sorted(Counter(k for r in rows for k in r).items())),
        "sense_keys": dict(sorted(Counter(k for s in senses for k in s).items())),
    }, features


def coverage(rows, dbp, kaikki, features, total_mass):
    n = len(rows)
    mass = sum(count for _, count in rows)
    flags = [(normalize(w) in dbp, normalize(w) in kaikki, count) for w, count in rows]
    masks = {
        "dbp": lambda d, k: d, "kaikki": lambda d, k: k,
        "both": lambda d, k: d and k, "either": lambda d, k: d or k,
        "dbp_only": lambda d, k: d and not k, "kaikki_only": lambda d, k: k and not d,
        "neither": lambda d, k: not (d or k),
    }
    return {
        "types": n, "occurrences": mass, "share_of_full_occurrences": ratio(mass, total_mass),
        "type_coverage": {name: ratio(sum(fn(d, k) for d, k, _ in flags), n) for name, fn in masks.items()},
        "occurrence_coverage_within_top": {name: ratio(sum(c for d, k, c in flags if fn(d, k)), mass) for name, fn in masks.items()},
        "kaikki_feature_coverage_all_top_types": {
            key: ratio(sum(features.get(normalize(w), {}).get(key, False) for w, _ in rows), n)
            for key in next(iter(features.values()))},
    }


def meaningful(value):
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return value is not None


def audit_parquet(path: Path, top_rows, kaikki):
    import pyarrow.parquet as pq
    table = pq.read_table(path)
    rows = table.to_pylist()
    columns = table.column_names
    lexical_column = next((x for x in ["lemma", "word", "headword"] if x in columns), None)
    lexemes = {normalize(r[lexical_column]) for r in rows if isinstance(r.get(lexical_column), str)} if lexical_column else set()
    synset_column = next((x for x in ["synset_id", "synset", "ili"] if x in columns), None)
    row_hashes = {json.dumps(r, ensure_ascii=False, sort_keys=True) for r in rows}
    stats = {
        "rows": table.num_rows, "schema": str(table.schema), "columns": columns,
        "nonempty_by_column": {c: ratio(sum(meaningful(r[c]) for r in rows), len(rows)) for c in columns},
        "distinct_by_column": {c: len({json.dumps(r[c], ensure_ascii=False, sort_keys=True) for r in rows}) for c in columns},
        "exact_duplicate_rows": len(rows) - len(row_hashes),
        "lexical_column": lexical_column, "distinct_normalized_lexemes": len(lexemes),
        "lexemes_also_in_kaikki": len(lexemes & kaikki),
        "lexemes_not_in_kaikki": len(lexemes - kaikki),
        "synset_column": synset_column,
        "distinct_synsets": len({r[synset_column] for r in rows}) if synset_column else None,
        "top_type_coverage": {str(n): ratio(sum(normalize(w) in lexemes for w, _ in top_rows[:n]), n) for n in [5000, 15000]},
        "sample_rows": rows[:3],
    }
    if synset_column and lexical_column:
        word_synsets = defaultdict(set)
        for row in rows:
            word_synsets[normalize(row[lexical_column])].add(row[synset_column])
        stats.update({
            "role_counts": dict(Counter(r.get("role") for r in rows)),
            "word_equals_value_rows": sum(r[lexical_column] == r.get("value") for r in rows),
            "lexemes_with_spaces": sum(" " in w for w in lexemes),
            "lexemes_with_multiple_synsets": sum(len(s) > 1 for s in word_synsets.values()),
            "max_synsets_per_lexeme": max(map(len, word_synsets.values()), default=0),
        })
    return stats, lexemes


def write_json(path: Path, value):
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def write_csv(path, rows, fields):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(raw: Path, output: Path):
    import pyarrow
    if raw.resolve() == output.resolve() or raw.resolve() in output.resolve().parents:
        raise ValueError("Output must not be inside raw inputs")
    with (raw / "dbp_malay_words_v2.json").open(encoding="utf-8") as stream:
        dbp_rows = json.load(stream)
    if not isinstance(dbp_rows, list) or not all(isinstance(w, str) and w.strip() for w in dbp_rows):
        raise ValueError("DBP file must contain a nonempty-string list")
    dbp = {normalize(w) for w in dbp_rows}
    freq = read_frequency(raw / "opensubtitles_frequency_ms_full.txt")
    freq_50k = read_frequency(raw / "opensubtitles_frequency_ms_50k.txt")
    if len(freq) < 15000 or len({normalize(w) for w, _ in freq[:15000]}) != 15000:
        raise ValueError("Full frequency input has fewer than 15000 types")
    records = read_kaikki(raw / "kaikki_malay.jsonl")
    kaikki = {normalize(r["word"]) for r in records}
    k_stats, features = analyze_kaikki(records)
    total_mass = sum(c for _, c in freq)
    normalized_frequency_groups = defaultdict(list)
    for rank, (word, count) in enumerate(freq, 1):
        normalized_frequency_groups[normalize(word)].append({"rank": rank, "word": word, "count": count})
    seed_path = Path(__file__).with_name("colloquial_candidates.json")
    with seed_path.open(encoding="utf-8") as stream:
        seed = json.load(stream)
    seed_terms = {w: (group, readings) for group, terms in seed["groups"].items() for w, readings in terms.items()}
    if sum(map(len, seed["groups"].values())) != len(seed_terms):
        raise ValueError("Duplicate colloquial seed candidates")
    index = {normalize(w): (rank, count) for rank, (w, count) in enumerate(freq, 1)}
    candidate_rows = [{"word": w, "group": group, "possible_expansions": " | ".join(readings),
                       "ambiguous_without_context": w in seed["ambiguous_without_context"],
                       "rank": index.get(w, (None, 0))[0], "count": index.get(w, (None, 0))[1],
                       "dbp": w in dbp, "kaikki": w in kaikki}
                      for w, (group, readings) in sorted(seed_terms.items())]
    colloquial = {"seed_version": seed["version"], "candidate_count": len(seed_terms),
                  "scope": seed["scope"], "candidate_rows": candidate_rows}
    for n in [5000, 15000, len(freq)]:
        hits = [r for r in candidate_rows if r["rank"] is not None and r["rank"] <= n]
        colloquial[str(n)] = {
            "candidate_type_matches": ratio(len(hits), n),
            "candidate_occurrence_matches": ratio(sum(r["count"] for r in hits), sum(c for _, c in freq[:n])),
            "by_group": dict(sorted(Counter(r["group"] for r in hits).items())),
            "ambiguous_type_matches": sum(r["ambiguous_without_context"] for r in hits),
            "kaikki_register_marked_types": ratio(sum(features.get(normalize(w), {}).get("register_marked", False) for w, _ in freq[:n]), n),
        }
    parquet_stats, parquet_lexemes = {}, {}
    for filename in ["entries-ms.parquet", "wordnet-ms.parquet"]:
        parquet_stats[filename], parquet_lexemes[filename] = audit_parquet(raw / filename, freq, kaikki)
    all_lexemes = dbp | kaikki | parquet_lexemes["wordnet-ms.parquet"]
    result = {
        "audit_version": 1, "runtime": {"python": platform.python_version(), "pyarrow": pyarrow.__version__},
        "method": {"normalization": "Unicode NFC + strip + casefold; preserve punctuation, spaces, accents and hyphens",
                   "ranking": "file order; positive descending counts; exact duplicate tokens rejected; normalization collisions reported, not merged; top15000 normalization uniqueness required; no token filtering",
                   "no_network": True, "source_urls": "download-script declarations, not proof of exact upstream revision"},
        "inputs": {name: {"bytes": (raw / name).stat().st_size, "sha256": sha256(raw / name),
                          "declared_download_url": url} for name, url in SOURCES.items()},
        "seed_sha256": sha256(seed_path),
        "dbp": {"list_items": len(dbp_rows), "distinct_raw": len(set(dbp_rows)),
                "distinct_normalized": len(dbp), "normalization_collisions": len(set(dbp_rows)) - len(dbp),
                "items_with_whitespace": sum(bool(re.search(r"\s", w)) for w in dbp_rows),
                "sample_first_20": dbp_rows[:20]},
        "frequency": {"full_types": len(freq), "full_occurrences": total_mass,
                      "top12000_occurrence_share": ratio(sum(c for _, c in freq[:12000]), total_mass),
                      "distinct_normalized_types": len(normalized_frequency_groups),
                      "normalization_collisions": {k: v for k, v in normalized_frequency_groups.items() if len(v) > 1},
                      "50k_types": len(freq_50k), "50k_matches_full_prefix": freq_50k == freq[:len(freq_50k)],
                      "count_one_types": sum(c == 1 for _, c in freq),
                      "types_containing_digit": sum(any(c.isdigit() for c in w) for w, _ in freq),
                      "top_20": [{"word": w, "count": c} for w, c in freq[:20]]},
        "dictionary_intersection": {"both": len(dbp & kaikki), "dbp_only": len(dbp - kaikki), "kaikki_only": len(kaikki - dbp),
                                    "jaccard": ratio(len(dbp & kaikki), len(dbp | kaikki))},
        "coverage": {str(n): coverage(freq[:n], dbp, kaikki, features, total_mass) for n in [5000, 15000]},
        "three_source_union_coverage": {str(n): ratio(sum(normalize(w) in all_lexemes for w, _ in freq[:n]), n) for n in [5000, 15000]},
        "colloquial_candidates": colloquial, "kaikki": k_stats, "parquet": parquet_stats,
    }
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "audit_metrics.json", result)
    audit_rows = [{"rank": rank, "word": w, "count": count, "dbp": normalize(w) in dbp,
                   "kaikki": normalize(w) in kaikki, "colloquial_candidate": normalize(w) in seed_terms,
                   **{key: features.get(normalize(w), {}).get(key, False) for key in next(iter(features.values()))}}
                  for rank, (w, count) in enumerate(freq, 1)]
    write_csv(output / "frequency_matches.csv", audit_rows, list(audit_rows[0]))
    missing = [r for r in audit_rows[:15000] if not r["dbp"] and not r["kaikki"]]
    write_csv(output / "top15000_missing_both.csv", missing, list(audit_rows[0]))
    write_csv(output / "colloquial_candidates.csv", candidate_rows, list(candidate_rows[0]))
    probes = {w: [r for r in records if normalize(r["word"]) == w]
              for w in ["ajar", "belajar", "mengajar", "pelajar", "tak", "nak", "diorang", "xde", "dkt", "sbb"]}
    write_json(output / "kaikki_probes.json", probes)
    for n, cov in result["coverage"].items():
        print(f"Top {n}: " + ", ".join(f"{k}={cov['type_coverage'][k]['n']} ({cov['type_coverage'][k]['pct']:.2f}%)" for k in ["dbp", "kaikki", "both", "neither"]))
    print(f"Kaikki: {len(records)} records, {len(kaikki)} normalized headwords, {k_stats['senses']} senses")
    print(f"Wrote audit artifacts to {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=ROOT / "raw")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "audit")
    args = parser.parse_args()
    try:
        run(args.raw_dir, args.output_dir)
    except (ValueError, OSError, ImportError) as exc:
        parser.exit(1, f"Audit failed: {exc}\n")


if __name__ == "__main__":
    main()
