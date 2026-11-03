"""Independently verify generated release payloads against the static snapshot."""

from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import sqlite3
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def digest(handle):
    sha = hashlib.sha256()
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
        sha.update(chunk)
    return sha.digest()


def verify(root=ROOT):
    static = root / "app" / "static"
    exports = root / "data" / "exports"
    manifest = json.loads((static / "data" / "manifest.json").read_text(encoding="utf-8"))
    sources = {}
    shards = sorted((static / "data" / "shards").glob("*.json"))
    check(len(shards) == 27, "Expected 27 source shards")
    for path in shards:
        for entry in json.loads(path.read_text(encoding="utf-8")).values():
            check(entry["id"] not in sources, "Duplicate source ID")
            sources[entry["id"]] = entry
    check(set(sources) == set(range(1, 15001)), "Source ID coverage differs")
    counts = Counter(e["data_state"] for e in sources.values())
    check(len(sources) == manifest["total_words"], "Manifest total differs")
    for state in ("enriched", "source_only", "missing_source"):
        check(counts[state] == manifest[f"{state}_count"], f"Manifest {state} differs")

    corpus = exports / "open_melayu_15k.jsonl"
    with corpus.open(encoding="utf-8") as handle:
        row_count = 0
        for row_count, line in enumerate(handle, 1):
            check(json.loads(line) == sources.get(row_count), f"JSONL row {row_count} differs")
    check(row_count == 15000, "Expected 15,000 JSONL rows")

    # mode=ro ensures validation cannot create or modify a database.
    database = exports / "open_melayu_15k.db"
    db = sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        check(db.execute("PRAGMA integrity_check").fetchone() == ("ok",), "SQLite integrity failed")
        check(not db.execute("PRAGMA foreign_key_check").fetchall(), "SQLite foreign keys failed")
        check(db.execute("SELECT count(*) FROM words").fetchone()[0] == 15000, "SQLite word count differs")
        check(db.execute("SELECT count(*) FROM melayu_fts").fetchone()[0] == 15000, "FTS coverage differs")
        sense_count = 0
        for row in db.execute("SELECT * FROM words ORDER BY id"):
            e = sources[row[0]]
            h, m, et = e.get("headword") or {}, e.get("morphology") or {}, e.get("etymology") or {}
            expected = (e["id"], e["word"], h.get("jawi"), h.get("ipa"), h.get("syllables"),
                        m.get("root_word"), m.get("root_jawi"), m.get("formula"), e["data_state"], h.get("status"),
                        et.get("historical_story"), et.get("cognitive_memory_aid"))
            check(row[:-1] == expected and json.loads(row[-1]) == e, f"SQLite payload differs: {e['word']}")
            actual = db.execute("SELECT * FROM senses WHERE word_id=? ORDER BY sense_id", (e["id"],)).fetchall()
            senses = sorted(e.get("senses") or [], key=lambda s: s["id"])
            expected_senses = [(e["id"], e["word"], s["id"], s.get("pos"), s.get("zh_definition"),
                                s.get("en_definition"), s.get("ms_definition"),
                                s.get("nuances") or s.get("nuance_note") or s.get("nuance")) for s in senses]
            check(actual == expected_senses, f"SQLite senses differ: {e['word']}")
            sense_count += len(senses)
        check(db.execute("SELECT count(*) FROM senses").fetchone()[0] == sense_count, "Extra SQLite senses")
        for query in ("word:saya", "word:say*", "jawi:ساي", "en_definition:pronoun", "ms_definition:ganti"):
            result = db.execute("SELECT rowid FROM melayu_fts WHERE melayu_fts MATCH ?", (query,)).fetchall()
            check((1,) in result, f"FTS query failed: {query}")
    finally:
        db.close()

    anki = exports / "open_melayu_15k_anki.tsv"
    expected_anki = [sources[n] for n in sorted(sources) if sources[n]["data_state"] == "enriched"]
    with anki.open(encoding="utf-8", newline="") as handle:
        card_count = 0
        for card_count, line in enumerate(handle, 1):
            check(card_count <= len(expected_anki), "Extra Anki cards")
            check(line.count("\t") == 1 and line.endswith("\n") and "\r" not in line, f"Invalid TSV row {card_count}")
            front, back = line.rstrip("\n").split("\t")
            entry = expected_anki[card_count - 1]
            check(f'>{html.escape(entry["word"], quote=True)}</div>' in front, "Anki headword/order differs")
            check("Berita" in back and "WhatsApp" in back, f"Anki scenarios missing: {entry['word']}")
            if entry["headword"].get("jawi"):
                check('dir="rtl"' in front, "Anki Jawi direction missing")
    check(card_count == manifest["enriched_count"], "Anki enriched count differs")

    payloads = {"sqlite": database, "anki": anki, "jsonl": corpus}
    for kind, payload in payloads.items():
        archive = exports / f"open_melayu_15k_{kind}.zip"
        with zipfile.ZipFile(archive) as zf:
            check(zf.namelist() == [payload.name], f"ZIP members differ: {archive.name}")
            with zf.open(payload.name) as packed, payload.open("rb") as original:
                check(digest(packed) == digest(original), f"ZIP payload differs: {archive.name}")
            check(zf.testzip() is None, f"ZIP CRC failure: {archive.name}")
        print(f"PASS {archive.name}: {archive.stat().st_size:,} bytes")
    web = exports / "open_melayu_15k_web_static.zip"
    with zipfile.ZipFile(web) as zf:
        files = {p.relative_to(static).as_posix(): p for p in static.rglob("*") if p.is_file()}
        check(len(zf.namelist()) == len(files) and set(zf.namelist()) == set(files), "Static ZIP paths differ")
        for name, original in files.items():
            with zf.open(name) as packed, original.open("rb") as handle:
                check(digest(packed) == digest(handle), f"Static ZIP bytes differ: {name}")
        check(zf.testzip() is None, "Static ZIP CRC failure")
    print(f"PASS {web.name}: {web.stat().st_size:,} bytes; {len(files)} identical files, 27 shards")
    print(f"PASS {row_count:,} JSONL / 15,000 SQLite words / {sense_count:,} senses / {card_count:,} Anki cards; {dict(counts)}")


if __name__ == "__main__":
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    verify()
