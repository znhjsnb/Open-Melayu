"""Build Open-Melayu releases from the committed static data (stdlib only)."""

import argparse
from collections import Counter
from contextlib import contextmanager
import html
import json
from pathlib import Path
import re
import sqlite3
import string
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
STATIC_DIR = ROOT / "app" / "static"
EXPORTS_DIR = ROOT / "data" / "exports"
STATES = {"enriched": "e", "source_only": "s", "missing_source": "m"}
FILENAMES = {
    "sqlite": "open_melayu_15k.db",
    "anki": "open_melayu_15k_anki.tsv",
    "jsonl": "open_melayu_15k.jsonl",
}


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_release(static_dir=STATIC_DIR):
    """Fail before exporting if the manifest, shards or index disagree."""
    data_dir = static_dir / "data"
    manifest = read_json(data_dir / "manifest.json")
    require(manifest.get("format_version") == 2, "Unsupported manifest format")
    require(manifest.get("total_words") == 15000, "Expected 15,000 headwords")
    require(manifest.get("conservation_check") is True, "Manifest conservation failed")
    version = re.search(r"export const DATA_VERSION\s*=\s*['\"]([^'\"]+)['\"]",
                        (static_dir / "data.js").read_text(encoding="utf-8"))
    require(version and version[1] == manifest.get("build_id"),
            "DATA_VERSION differs from manifest build_id")
    shard_paths = sorted((data_dir / "shards").glob("*.json"))
    expected = {f"{c}.json" for c in string.ascii_lowercase} | {"other.json"}
    require({p.name for p in shard_paths} == expected, "Expected exactly 27 shards")
    words, ids = {}, set()
    for path in shard_paths:
        shard = read_json(path)
        require(isinstance(shard, dict), f"Invalid shard: {path.name}")
        for word, entry in shard.items():
            require(bool(word) and word == word.strip().lower(), f"Invalid headword: {word}")
            key = word[0] if word[0] in string.ascii_lowercase else "other"
            require(path.stem == key, f"Wrong shard for {word}")
            require(word not in words, f"Duplicate headword: {word}")
            entry_id = entry.get("id")
            require(type(entry_id) is int and entry_id not in ids, f"Invalid/duplicate ID: {word}")
            display_word = entry.get("headword", {}).get("word")
            require(entry.get("word") == word and isinstance(display_word, str)
                    and display_word.strip().lower() == word,
                    f"Headword mismatch: {word}")
            state = entry.get("data_state")
            require(state in STATES, f"Unknown data_state: {word}")
            require(entry.get("is_enriched") is (state == "enriched"),
                    f"is_enriched mismatch: {word}")
            words[word] = entry
            ids.add(entry_id)
    require(ids == set(range(1, 15001)), "IDs must be exactly 1..15000")
    counts = Counter(e["data_state"] for e in words.values())
    for state in STATES:
        require(counts[state] == manifest.get(f"{state}_count"), f"Manifest count mismatch: {state}")
    provenance = Counter(e["headword"].get("status") for e in words.values()
                         if e["data_state"] == "enriched")
    require(dict(provenance) == manifest.get("provenance_breakdown"), "Provenance counts differ")
    index = read_json(data_dir / "search_index.json")
    require(isinstance(index, list) and len(index) == len(words), "Index count mismatch")
    indexed = set()
    for row in index:
        word = row.get("w")
        require(word in words and word not in indexed, f"Invalid/duplicate index headword: {word}")
        entry = words[word]
        require(row.get("id") == entry["id"] and row.get("st") == STATES[entry["data_state"]]
                and row.get("e") == int(entry["is_enriched"]), f"Index mismatch: {word}")
        indexed.add(word)
    return manifest, sorted(words.values(), key=lambda e: e["id"])


@contextmanager
def atomic_output(path):
    """Replace a finished artifact; keep the previous one if generation fails."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    try:
        yield temporary
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def compact_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def nuances(sense):
    return sense.get("nuances") or sense.get("nuance_note") or sense.get("nuance")


def export_sqlite(entries, path):
    with atomic_output(path) as temporary:
        connection = sqlite3.connect(temporary)
        try:
            connection.executescript("""
                PRAGMA foreign_keys = ON;
                CREATE TABLE words (
                    id INTEGER PRIMARY KEY, word TEXT NOT NULL UNIQUE,
                    jawi TEXT, ipa TEXT, syllables TEXT, root_word TEXT, root_jawi TEXT,
                    formula TEXT, data_state TEXT NOT NULL, status TEXT,
                    etymology_story TEXT, memory_aid TEXT, raw_json TEXT NOT NULL
                );
                CREATE TABLE senses (
                    word_id INTEGER NOT NULL REFERENCES words(id), word TEXT NOT NULL,
                    sense_id INTEGER NOT NULL, pos TEXT, zh_definition TEXT,
                    en_definition TEXT, ms_definition TEXT, nuances TEXT,
                    PRIMARY KEY (word_id, sense_id)
                );
                CREATE INDEX senses_word ON senses(word);
                CREATE VIRTUAL TABLE melayu_fts USING fts5(
                    word, jawi, root_word, zh_definition, en_definition, ms_definition,
                    nuances, tokenize='unicode61'
                );
            """)
            with connection:
                for entry in entries:
                    head = entry.get("headword") or {}
                    morph = entry.get("morphology") or {}
                    etym = entry.get("etymology") or {}
                    senses = entry.get("senses") or []
                    connection.execute("INSERT INTO words VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                        entry["id"], entry["word"], head.get("jawi"), head.get("ipa"),
                        head.get("syllables"), morph.get("root_word"), morph.get("root_jawi"),
                        morph.get("formula"), entry["data_state"], head.get("status"),
                        etym.get("historical_story"), etym.get("cognitive_memory_aid"), compact_json(entry),
                    ))
                    for sense in senses:
                        connection.execute("INSERT INTO senses VALUES (?,?,?,?,?,?,?,?)", (
                            entry["id"], entry["word"], sense["id"], sense.get("pos"),
                            sense.get("zh_definition"), sense.get("en_definition"),
                            sense.get("ms_definition"), nuances(sense),
                        ))
                    connection.execute("INSERT INTO melayu_fts(rowid,word,jawi,root_word,"
                                       "zh_definition,en_definition,ms_definition,nuances) "
                                       "VALUES (?,?,?,?,?,?,?,?)", (
                        entry["id"], entry["word"], head.get("jawi"), morph.get("root_word"),
                        *["\n".join(s.get(field) or "" for s in senses)
                          for field in ("zh_definition", "en_definition", "ms_definition")],
                        "\n".join(nuances(s) or "" for s in senses),
                    ))
                connection.execute("INSERT INTO melayu_fts(melayu_fts) VALUES ('optimize')")
                connection.execute("INSERT INTO melayu_fts(melayu_fts) VALUES ('integrity-check')")
            require(connection.execute("PRAGMA integrity_check").fetchone() == ("ok",),
                    "SQLite integrity check failed")
        finally:
            connection.close()


def text(value):
    """Only exporter-owned markup can enter the single-line Anki HTML."""
    return html.escape(re.sub(r"[\t\r\n]+", " ", str(value if value is not None else "")), quote=True)


def paragraph(label, value, *, jawi=False):
    if value is None or value == "":
        return ""
    content = text(value)
    if jawi:
        content = f'<span lang="ms-Arab" dir="rtl" style="unicode-bidi:isolate">{content}</span>'
    return f"<p><b>{text(label)}</b> {content}</p>"


def source_label(head, sense):
    if head.get("status") == "official":
        return "DBP 原文:" if sense.get("ms_is_verbatim") is True else "马来语释义 (基于 DBP 官方词条):"
    if head.get("status") == "root_derived":
        return "马来语释义 (基于 DBP 词根推导):"
    return "马来语释义 (字幕高频语料用法):"


def anki_card(entry):
    head, morph = entry.get("headword") or {}, entry.get("morphology") or {}
    front = (f'<div lang="ms" style="font-size:32px;font-weight:700">{text(entry["word"])}</div>'
             + paragraph("Jawi", head.get("jawi"), jawi=True)
             + paragraph("IPA", head.get("ipa")) + paragraph("音节", head.get("syllables")))
    back = [f'<article style="text-align:left;line-height:1.65"><p>#{entry["id"]} · '
            f'{text(entry["data_state"])} · {text(head.get("status"))}</p>', "<h3>构词</h3>",
            paragraph("词根", morph.get("root_word")), paragraph("词根 Jawi", morph.get("root_jawi"), jawi=True),
            paragraph("公式", morph.get("formula")), paragraph("构词说明", morph.get("pattern_note"))]
    for family in morph.get("word_family") or []:
        back.append(paragraph("词族", " · ".join(str(family.get(k) or "") for k in ("word", "affix", "gloss"))))
    back.append("<h3>释义与搭配</h3>")
    for sense in entry.get("senses") or []:
        back.extend([f'<h4>{text(sense.get("id"))}. {text(sense.get("pos"))}</h4>',
                     paragraph("中文", sense.get("zh_definition")), paragraph("English", sense.get("en_definition")),
                     paragraph(source_label(head, sense), sense.get("ms_definition")), paragraph("使用边界", nuances(sense))])
        for col in sense.get("collocations") or []:
            back.append("<p>" + "<br>".join(text(col.get(k)) for k in ("ms", "zh", "en")) + "</p>")
    back.append("<h3>双境语料</h3>")
    for scenario in entry.get("dual_scenarios") or []:
        kind = scenario.get("scenario") or scenario.get("type") or scenario.get("register")
        back.append(f'<h4>{"WhatsApp 街头口语" if kind == "colloquial" else "Berita / Dokumen 正式语体"}</h4>')
        back.append(paragraph("场景", scenario.get("context")))
        for key, label in (("ms", "Bahasa Melayu"), ("ms_spoken", "口语"), ("ms_standard", "标准语"), ("zh", "中文"), ("en", "English")):
            back.append(paragraph(label, scenario.get(key)))
        for message in scenario.get("messages") or []:
            back.append(f'<blockquote><b>{text(message.get("speaker"))}</b>')
            for key, label in (("ms_spoken", "口语"), ("ms_standard", "标准语"), ("zh", "中文"), ("en", "English")):
                back.append(paragraph(label, message.get(key)))
            back.append("</blockquote>")
        for feature in scenario.get("spoken_features") or []:
            back.append(paragraph("口语特征", feature))
    back.append("<h3>口语速查</h3>")
    for shortcut in entry.get("spoken_shortcuts") or []:
        back.append(paragraph("缩略", f'{shortcut.get("abbr", "")} → {shortcut.get("full_form", "")} · {shortcut.get("note", "")}'))
    back.append("<h3>社交礼仪</h3>")
    pragmatics = entry.get("cultural_pragmatics") or entry.get("sociolinguistic_register") or {}
    for key, value in pragmatics.items():
        back.append(paragraph(key, "；".join(map(str, value)) if isinstance(value, list) else value))
    back.append("<h3>词源与记忆</h3>")
    for key, value in (entry.get("etymology") or {}).items():
        label = {"historical_story": "历史词源", "cognitive_memory_aid": "记忆法（非词源考据）"}.get(key, key)
        back.append(paragraph(label, value))
    back.append(paragraph("来源", (entry.get("provenance") or {}).get("attribution")))
    back.append("</article>")
    return front + "\t" + "".join(back)


def export_anki(entries, path):
    with atomic_output(path) as temporary:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for entry in entries:
                if entry["data_state"] == "enriched":
                    handle.write(anki_card(entry) + "\n")


def export_jsonl(entries, path):
    with atomic_output(path) as temporary:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            for entry in entries:
                handle.write(compact_json(entry) + "\n")


def archive_files(files, path):
    with atomic_output(path) as temporary:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
            for source, name in files:
                archive.write(source, arcname=name)


def export_web(static_dir, path):
    archive_files(((p, p.relative_to(static_dir).as_posix())
                   for p in sorted(static_dir.rglob("*")) if p.is_file()), path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Build all formats and all four ZIPs (also the default)")
    for kind in ("sqlite", "anki", "jsonl", "web"):
        parser.add_argument(f"--{kind}", action="store_true", help=f"Build {kind} only (flags can be combined)")
    parser.add_argument("--zip", action="store_true", help="ZIP selected formats; alone rebuilds all release packages")
    args = parser.parse_args(argv)
    selected = [kind for kind in (*FILENAMES, "web") if getattr(args, kind)]
    all_formats = args.all or not selected
    if all_formats:
        selected = [*FILENAMES, "web"]
    started = time.monotonic()
    try:
        manifest, entries = load_release()
        print(f'Open-Melayu 15K {manifest["build_id"]}: {len(entries):,} words, '
              f'{manifest["enriched_count"]:,} enriched', flush=True)
        exporters = {"sqlite": export_sqlite, "anki": export_anki, "jsonl": export_jsonl}
        for kind in selected:
            if kind == "web":
                path = EXPORTS_DIR / "open_melayu_15k_web_static.zip"
                export_web(STATIC_DIR, path)
            else:
                path = EXPORTS_DIR / FILENAMES[kind]
                exporters[kind](entries, path)
                if all_formats or args.zip:
                    archive = EXPORTS_DIR / f"open_melayu_15k_{kind}.zip"
                    archive_files([(path, path.name)], archive)
                    print(f"  {archive.name}: {archive.stat().st_size:,} bytes", flush=True)
            print(f"  {path.name}: {path.stat().st_size:,} bytes", flush=True)
        print(f"Completed in {time.monotonic() - started:.1f}s: {EXPORTS_DIR}")
    except (OSError, ValueError, sqlite3.Error, zipfile.BadZipFile) as error:
        parser.exit(1, f"Export failed: {error}\n")


if __name__ == "__main__":
    if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
