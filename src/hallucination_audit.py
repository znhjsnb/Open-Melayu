"""Independent, strict UTF-8 asset checks; writes only data/hallucination_audit/."""
from __future__ import annotations

import hashlib
import json
import platform
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.audit-deps'))
import pyarrow.parquet as pq


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    out = ROOT / 'data/hallucination_audit'
    out.mkdir(parents=True, exist_ok=True)
    result = {'observed_utc': datetime.now(timezone.utc).isoformat(),
              'python': platform.python_version(), 'pyarrow': __import__('pyarrow').__version__}
    result['files'] = {p.name: {'bytes': p.stat().st_size,
        'MB': round(p.stat().st_size / 1e6, 6),
        'MiB': round(p.stat().st_size / 2**20, 6), 'sha256': digest(p)}
        for p in sorted((ROOT / 'raw').iterdir()) if p.is_file()}
    dbp = json.loads((ROOT / 'raw/dbp_malay_words_v2.json').read_text(encoding='utf-8'))
    result['dbp'] = {'type': type(dbp).__name__, 'rows': len(dbp),
        'unique_exact': len(set(dbp)), 'unique_casefold': len({w.casefold() for w in dbp}),
        'all_strings': all(isinstance(w, str) for w in dbp),
        'contains_examples': {w: w in dbp for w in ['abandoned', 'mesovarium', 'hydroterpene', 'tak', 'ajar', 'belajar']}}
    with (ROOT / 'raw/kaikki_malay.jsonl').open(encoding='utf-8') as f:
        entries = [json.loads(line) for line in f]
    def ipa(r): return any(s.get('ipa') for s in r.get('sounds', []))
    def audio(r): return any(s.get('audio') or s.get('ogg_url') or s.get('mp3_url') for s in r.get('sounds', []))
    predicates = {'ipa': ipa, 'audio': audio,
        'hyphenation': lambda r: bool(r.get('hyphenation') or r.get('hyphenations')),
        'etymology_text': lambda r: bool(r.get('etymology_text')),
        'etymology_templates': lambda r: bool(r.get('etymology_templates')),
        'examples': lambda r: any(s.get('examples') for s in r.get('senses', [])),
        'derived': lambda r: bool(r.get('derived')),
        'forms': lambda r: bool(r.get('forms'))}
    result['kaikki'] = {'records': len(entries),
        'headwords_exact': len({r['word'] for r in entries}),
        'headwords_casefold': len({r['word'].casefold() for r in entries}),
        'sense_objects': sum(len(r.get('senses', [])) for r in entries),
        'lang_codes': dict(Counter(r.get('lang_code') for r in entries)),
        'fields_by_record': {k: sum(bool(fn(r)) for r in entries) for k, fn in predicates.items()},
        'fields_by_headword_casefold': {k: len({r['word'].casefold() for r in entries if fn(r)}) for k, fn in predicates.items()},
        'probes': {w: [r for r in entries if r['word'] == w] for w in ['ajar', 'belajar', 'mengajar', 'pelajar', 'tak', 'nak', 'kat', 'diorang']}}
    result['frequency'] = {}
    for name in ['opensubtitles_frequency_ms_full.txt', 'opensubtitles_frequency_ms_50k.txt']:
        with (ROOT / 'raw' / name).open(encoding='utf-8') as f:
            rows = [line.strip().rsplit(maxsplit=1) for line in f]
        counts = [int(row[1]) for row in rows]
        total = sum(counts)
        result['frequency'][name] = {'rows': len(rows), 'unique_exact': len({r[0] for r in rows}),
            'occurrences': total, 'top10': rows[:10],
            'rank_probes': {w: next((i+1 for i, r in enumerate(rows) if r[0] == w), None) for w in ['tak', 'nak', 'kat', 'diorang']},
            'top_token_coverage': {str(n): {'occurrences': sum(counts[:n]), 'pct': 100 * sum(counts[:n]) / total} for n in [4000, 5000, 12000, 15000]}}
    result['parquet'] = {}
    for name in ['entries-ms.parquet', 'wordnet-ms.parquet']:
        table = pq.read_table(ROOT / 'raw' / name)
        rows = table.to_pylist()
        item = {'rows': table.num_rows, 'schema': str(table.schema), 'first_two': rows[:2],
                'nonempty_by_column': {c: sum(v is not None and v != '' and v != [] for v in table[c].to_pylist()) for c in table.column_names}}
        for c in ['word', 'lemma', 'synset', 'synset_id', 'entry_id', 'source', 'lang', 'pos', 'role']:
            if c in table.column_names:
                values = table[c].to_pylist()
                item['unique_' + c] = len(set(values))
                if c in ['source', 'lang', 'pos', 'role']:
                    item['distribution_' + c] = dict(Counter(values))
        result['parquet'][name] = item
    static = ROOT.parent / 'dict/app/static/data'
    index = json.loads((static / 'search_index.json').read_text(encoding='utf-8'))
    shard_rows = []
    shard_counts = {}
    for p in sorted((static / 'shards').glob('*.json')):
        rows = json.loads(p.read_text(encoding='utf-8'))
        if isinstance(rows, dict):
            rows = list(rows.values())
        shard_counts[p.name] = len(rows)
        shard_rows.extend(rows)
    index_words = [r['w'] for r in index]
    words = [r['word'] for r in shard_rows]
    result['dict_static'] = {'search_index_records': len(index), 'shards': len(shard_counts),
        'shard_counts': shard_counts, 'detail_records': len(shard_rows),
        'unique_headwords': len(set(words)), 'sense_objects': sum(len(r.get('senses', [])) for r in shard_rows),
        'missing_from_details': sorted(set(index_words) - set(words)),
        'extra_in_details': sorted(set(words) - set(index_words)), 'duplicate_detail_words': len(words) - len(set(words))}
    path = out / 'local_metrics.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {k: v for k, v in result.items() if k not in ['kaikki', 'parquet']}
    summary['kaikki'] = {k:v for k,v in result['kaikki'].items() if k != 'probes'}
    summary['parquet'] = {name: {k:v for k,v in item.items() if k not in ['schema','first_two']} for name,item in result['parquet'].items()}
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
