"""Read-only Phase 3 audit; writes evidence and an isolated export under this project.

No production generation, paid API calls, service reloads, or writes to source assets.
"""
import ast
import bz2
import collections
import contextlib
import datetime
import hashlib
import io
import json
import random
import re
import runpy
import statistics
import sys
import tomllib
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/audit/phase3_evidence.json'
KEYS = ['headword', 'morphology', 'senses', 'dual_scenarios', 'spoken_shortcuts',
        'cultural_pragmatics', 'sociolinguistic_register', 'etymology']
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def read(p):
    def pairs(items):
        d = {}
        for k, v in items:
            if k in d:
                raise ValueError('duplicate JSON key: ' + k)
            d[k] = v
        return d
    return json.loads(p.read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=lambda s: (_ for _ in ()).throw(ValueError(s)))


def empty_paths(x, prefix=''):
    if x is None or x == '' or x == [] or x == {}:
        yield prefix
    elif isinstance(x, dict):
        for k, v in x.items():
            yield from empty_paths(v, prefix + '.' + k if prefix else k)
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from empty_paths(v, f'{prefix}[{i}]')


def main():
    paths = sorted((ROOT / 'data/enriched').glob('*.json'))
    candidates = read(ROOT / 'data/candidate_pool_15k.json')
    pool = {x['word'].strip().lower(): x for x in candidates}
    source_files = paths + list((ROOT / 'data/prpm_raw').glob('*.json'))
    source_files += list((ROOT / 'app/static/data').rglob('*.json'))
    source_files += [ROOT / x for x in ['src/concurrent_synthesizer.py',
                     'src/export_web_shards.py', 'app/server.py',
                     'docs/PROJECT_HANDOFF.md', 'docs/CONVERSATION_PHASE3_FOR_AUDIT.md']]
    before = {str(p.relative_to(ROOT)): digest(p) for p in source_files}
    e = {'audited_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
         'scope': 'current disk snapshot; no historical process or network trace assertion',
         'input_sha256': before}
    entries, batches, bad, details, duplicate_words = {}, {}, {}, {}, []
    for p in paths:
        try:
            x = read(p)
            if isinstance(x, list):
                batches[p.name] = len(x)
                continue
            w = x['headword']['word']
            if w in entries:
                duplicate_words.append(w)
            entries[w] = x
            issues = []
            missing = [k for k in KEYS if k not in x]
            for k in KEYS:
                if k in x and not isinstance(x[k], list if k in ['senses', 'dual_scenarios', 'spoken_shortcuts'] else dict):
                    issues.append('type:' + k)
            for s in x.get('senses', []):
                if len(s.get('collocations', [])) < 2:
                    issues.append('fewer_than_two_collocations:' + str(s.get('id')))
                for k in ['pos', 'zh_definition', 'ms_definition', 'nuances']:
                    if not s.get(k):
                        issues.append('empty_sense:' + k)
            scenarios = {s.get('scenario'): s for s in x.get('dual_scenarios', [])}
            for kind, fields in [('formal', ['ms', 'zh', 'en', 'context']),
                                 ('colloquial', ['ms_spoken', 'ms_standard', 'zh', 'spoken_features', 'context'])]:
                for k in fields:
                    if not scenarios.get(kind, {}).get(k):
                        issues.append('scenario:' + kind + '.' + k)
            for k in ['root_word', 'formula', 'pattern_note']:
                if not x.get('morphology', {}).get(k):
                    issues.append('morphology:' + k)
            for k in ['register', 'politeness_note', 'usage_etiquette']:
                if not x.get('cultural_pragmatics', {}).get(k):
                    issues.append('pragmatics:' + k)
            for k in ['origin', 'source_language', 'root_origin', 'historical_story', 'cognitive_memory_aid']:
                if not x.get('etymology', {}).get(k):
                    issues.append('etymology:' + k)
            details[w] = {'file': p.name, 'missing_dimensions': missing,
                          'empty_paths': list(empty_paths(x)), 'nested_issues': issues,
                          'rank': x['headword'].get('frequency_rank'), 'bytes': p.stat().st_size}
        except Exception as exc:
            bad[p.name] = str(exc)
    rng = random.Random(20261101)
    sample = sorted(set(rng.sample(sorted(entries), 12) +
                        ['tv', 'okay', 'saya', 'dengan', 'mendapatkan', 'rumah', 'jom', 'tuhan', 'bangunan', 'bijak']))
    e['enriched'] = {
        'json_file_count': len(paths), 'batch_arrays': batches, 'individual_count': len(entries),
        'parse_errors': bad, 'duplicate_headwords': duplicate_words,
        'exact_top1000': set(entries) == {x['word'].strip().lower() for x in candidates[:1000]},
        'missing_from_top1000': sorted({x['word'].strip().lower() for x in candidates[:1000]} - set(entries)),
        'dimension_present_counts': {k: sum(k in v for v in entries.values()) for k in KEYS},
        'missing_jawi': sorted(w for w, v in entries.items() if not v['headword'].get('jawi')),
        'missing_syllables': sorted(w for w, v in entries.items() if not v['headword'].get('syllables')),
        'nested_issue_entries': {w: d['nested_issues'] for w, d in details.items() if d['nested_issues']},
        'rank_mismatches': [w for w, v in entries.items() if v['headword'].get('frequency_rank') != pool.get(w, {}).get('rank')],
        'details': details, 'sample_seed': 20261101,
        'sample': {w: {'checks': details[w], 'entry': entries[w]} for w in sample if w in entries},
        'bytes': {'min': min(d['bytes'] for d in details.values()),
                  'median': statistics.median(d['bytes'] for d in details.values()),
                  'max': max(d['bytes'] for d in details.values()),
                  'total': sum(d['bytes'] for d in details.values())}}
    e['enriched']['invalid_nonempty_jawi'] = {
        w: v['headword']['jawi'] for w, v in entries.items()
        if v['headword'].get('jawi') and not re.search(r'[\u0600-\u06ff]', v['headword']['jawi'])}
    e['enriched']['question_mark_runs'] = {}
    def question_paths(x, prefix=''):
        if isinstance(x, str) and re.search(r'\?{2,}', x):
            yield {'path': prefix, 'value': x}
        elif isinstance(x, dict):
            for k, v in x.items():
                yield from question_paths(v, prefix + '.' + k if prefix else k)
        elif isinstance(x, list):
            for i, v in enumerate(x):
                yield from question_paths(v, f'{prefix}[{i}]')
    for w, v in entries.items():
        q = list(question_paths(v))
        if q:
            e['enriched']['question_mark_runs'][w] = q
    e['enriched']['sense_count'] = sum(len(v['senses']) for v in entries.values())
    e['enriched']['senses_without_two_collocations'] = sum(
        len(s.get('collocations', [])) < 2 for v in entries.values() for s in v['senses'])
    e['enriched']['historical_story_count'] = sum(bool(v['etymology'].get('historical_story')) for v in entries.values())
    # Extract this single pure function: never import or run the production scheduler.
    tree = ast.parse((ROOT / 'src/concurrent_synthesizer.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_entry')
    scope = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), '<isolated-validator>', 'exec'), scope)
    validate = scope['validate_entry']
    results = {}
    for w, v in entries.items():
        try:
            ok, reason = validate(v)
            if not ok:
                results[w] = reason
        except Exception as exc:
            results[w] = str(exc)
    fake = {'headword': {'word': 'FAKE', 'jawi': 'FAKE'}, 'morphology': {},
            'senses': [{}], 'dual_scenarios': [], 'spoken_shortcuts': [],
            'cultural_pragmatics': {}, 'etymology': {'historical_story': 'FAKE'}}
    e['production_validator'] = {'failed_current_entries': results,
                               'pass_count': len(entries) - len(results),
                               'synthetic_empty_entry_accepted': validate(fake),
                               'synthetic_test_is_not_production_data': True}
    raw, raw_bad = {}, {}
    for p in (ROOT / 'data/prpm_raw').glob('*.json'):
        try:
            raw[p.name] = read(p)
        except Exception as exc:
            raw_bad[p.name] = str(exc)
    def has_defs(v):
        return bool(v.get('kamus_dewan') or v.get('kamus_pelajar') or v.get('raw_definitions'))
    reserved = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2'}
    def raw_for(w):
        return raw.get(('_reserved_' if w in reserved else '') + w + '.json', {})
    e['prpm'] = {'json_count': len(raw) + len(raw_bad), 'parse_errors': raw_bad,
                 'with_definitions': sum(has_defs(v) for v in raw.values()),
                 'with_error': sum(bool(v.get('error')) for v in raw.values()),
                 'with_jawi': sum(bool(v.get('jawi')) for v in raw.values()),
                 'with_syllables': sum(bool(v.get('syllables')) for v in raw.values()),
                 'both_jawi_and_syllables': sum(bool(v.get('jawi') and v.get('syllables')) for v in raw.values()),
                 'enriched_head_metadata_differences': {
                     w: {k: {'raw': raw_for(w).get(k), 'enriched': v['headword'].get(k)}
                         for k in ['jawi', 'syllables'] if raw_for(w).get(k) != v['headword'].get(k)}
                     for w, v in entries.items() if any(raw_for(w).get(k) != v['headword'].get(k) for k in ['jawi', 'syllables'])}}
    base = ROOT / 'app/static/data'
    manifest = read(base / 'manifest.json')
    idx = read(base / 'search_index.json')
    shard_files = sorted((base / 'shards').glob('*.json'))
    shards, duplicates = {}, []
    for p in shard_files:
        for w, v in read(p).items():
            if w in shards:
                duplicates.append(w)
            shards[w] = v
    index_map = {v['w'].lower(): v for v in idx}
    enriched_diff = {}
    for w, entry in entries.items():
        sv = shards.get(w, {})
        diffs = [k for k in KEYS if k in entry and sv.get(k) != entry[k]]
        if diffs:
            enriched_diff[w] = diffs
    e['web'] = {'manifest': manifest, 'index_count': len(idx),
        'index_unique_words': len(index_map), 'index_unique_ids': len({v['id'] for v in idx}),
        'index_state_counts': dict(collections.Counter(v['st'] for v in idx)),
        'index_bytes': (base / 'search_index.json').stat().st_size,
        'index_MiB': (base / 'search_index.json').stat().st_size / 1024**2,
        'index_decimal_MB': (base / 'search_index.json').stat().st_size / 10**6,
        'shard_count': len(shard_files), 'shard_names': [p.name for p in shard_files],
        'shard_sizes': {p.name: len(read(p)) for p in shard_files},
        'shard_unique_words': len(shards), 'shard_duplicate_words': duplicates,
        'shard_state_counts': dict(collections.Counter(v['data_state'] for v in shards.values())),
        'candidate_set_equals_index': set(pool) == set(index_map),
        'candidate_set_equals_shards': set(pool) == set(shards),
        'index_shard_id_mismatches': [w for w in index_map if shards.get(w, {}).get('id') != index_map[w]['id']],
        'index_candidate_rank_mismatches': [w for w in index_map if pool.get(w, {}).get('rank') != index_map[w]['id']],
        'enriched_content_differences': enriched_diff,
        'missing_source_falsely_labelled_official_senses': sum(
            v['data_state'] == 'missing_source' and any(s.get('nuances') == 'DBP 官方马来语词典定义' for s in v.get('senses', []))
            for v in shards.values())}
    # Rebuild in a fresh isolated directory; do not overwrite published data.
    sandbox = ROOT / '.audit-tmp/phase3_export'
    mod = runpy.run_path(str(ROOT / 'src/export_web_shards.py'), run_name='phase3_export_audit')
    glob = mod['export_shards'].__globals__
    glob.update(OUTPUT_DIR=sandbox, SHARDS_DIR=sandbox / 'shards')
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        mod['export_shards']()
    rebuilt = read(sandbox / 'manifest.json')
    e['isolated_export'] = {'directory': str(sandbox.relative_to(ROOT)), 'stdout': captured.getvalue(),
        'manifest_matches_except_timestamp': {k: v for k, v in rebuilt.items() if k != 'timestamp'} ==
                                            {k: v for k, v in manifest.items() if k != 'timestamp'},
        'index_byte_equal': digest(sandbox / 'search_index.json') == digest(base / 'search_index.json'),
        'shards_byte_equal': all(digest(sandbox / 'shards' / p.name) == digest(p) for p in shard_files)}
    # Count assets without interpreting availability as complete linguistic coverage.
    kk = [json.loads(s) for s in (ROOT / 'raw/kaikki_malay.jsonl').read_text(encoding='utf-8').splitlines() if s.strip()]
    words = {v['word'].lower() for v in kk}
    e['raw_assets'] = {'kaikki_records': len(kk), 'kaikki_unique_lower_words': len(words),
        'kaikki_words_with_ipa': len({v['word'].lower() for v in kk if any(s.get('ipa') for s in v.get('sounds', []) or [])}),
        'kaikki_words_with_etymology': len({v['word'].lower() for v in kk if v.get('etymology_text')}),
        'roots_count': len(read(ROOT / 'raw/malay_rootwords.json')),
        'colloquial_rules_count': len(read(ROOT / 'raw/malaya_colloquial_rules.json')),
        'tatoeba_rows': sum(1 for _ in bz2.open(ROOT / 'raw/zsm_sentences.tsv.bz2', 'rt', encoding='utf-8'))}
    cfg = tomllib.loads(Path('C:/Users/d/.codex/config.toml').read_text(encoding='utf-8'))
    cache = read(Path('C:/Users/d/.codex/models_cache.json'))
    e['model'] = {'config': {k: cfg.get(k) for k in ['model', 'model_reasoning_effort', 'openai_base_url']},
                  'desktop_enabled_efforts': cfg.get('desktop', {}).get('enabled-reasoning-efforts'),
                  'cache_fetched_at': cache.get('fetched_at'), 'cache_client_version': cache.get('client_version'),
                  'sol_metadata': [{k: m.get(k) for k in ['slug', 'default_reasoning_level', 'supported_reasoning_levels']}
                                   for m in cache.get('models', []) if m.get('slug') == 'gpt-6.1-sol']}
    launcher = Path('C:/Users/d/Desktop/启动Open-Melayu词典工作台.bat')
    e['service'] = {'launcher_exists': launcher.exists(),
                    'launcher_content': launcher.read_text(encoding='utf-8') if launcher.exists() else None,
                    'http': {}}
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for port, route in [(8766, '/api/health'), (8766, '/api/stats'),
                         (8766, '/data/manifest.json'), (8765, '/')]:
        url = f'http://127.0.0.1:{port}{route}'
        try:
            with opener.open(url, timeout=5) as resp:
                body = resp.read()
                e['service']['http'][url] = {'status': resp.status, 'content_type': resp.headers.get('Content-Type'),
                                            'body': json.loads(body) if 'json' in resp.headers.get('Content-Type', '') else None}
        except Exception as exc:
            e['service']['http'][url] = {'error': str(exc)}
    ref = Path('C:/Users/d/Documents/dict/app/static')
    e['handoff'] = {'root_RULES_exists': (ROOT / 'RULES.md').exists(),
        'reference_files_exist': {n: (ref / n).exists() for n in ['index.html', 'styles.css', 'app.js', 'worker.js', 'db.js']},
        'current_equals_reference': {n: (ROOT / 'app/static' / n).exists() and digest(ROOT / 'app/static' / n) == digest(ref / n)
                                     for n in ['index.html', 'styles.css', 'app.js', 'worker.js', 'db.js']}}
    transcript = (ROOT / 'docs/CONVERSATION_PHASE3_FOR_AUDIT.md').read_text(encoding='utf-8')
    e['transcript'] = {'truncation_markers': re.findall(r'<truncated[^>]*>', transcript),
                        'antigravity_turns': len(re.findall(r'^## .*ANTIGRAVITY:', transcript, re.M))}
    history_root = Path('C:/Users/d/.gemini/antigravity/brain/a15a97c6-dccc-4f20-bae5-6b32e0337038/.system_generated')
    history_path = history_root / 'logs/transcript.jsonl'
    e['history'] = {'available': history_path.exists()}
    if history_path.exists():
        rows = [json.loads(l) for l in history_path.read_text(encoding='utf-8').splitlines() if l.strip()]
        selected = {2031, 2106, 2125, 2126, 2143, 2144, 2190, 2199, 2200,
                    2214, 2226, 2232, 2243, 2244, 2245, 2246, 2247, 2248, 2250, 2256, 2310}
        e['history'].update(path=str(history_path), sha256=digest(history_path),
            selected_records=[{k: r[k] for k in ['step_index', 'created_at', 'type', 'content', 'tool_calls'] if k in r}
                              for r in rows if r.get('step_index') in selected],
            visible_phase3_turns=[{k: r[k] for k in ['step_index', 'created_at', 'content']}
                for r in rows if r.get('type') == 'PLANNER_RESPONSE' and r.get('content')
                and '2026-11-01T14:36:00Z' <= r.get('created_at', '') <= '2026-11-01T15:48:17Z'])
        log_path = history_root / 'tasks/task-2106.log'
        if log_path.exists():
            log = log_path.read_text(encoding='utf-8')
            e['history']['production_log'] = {
                'path': str(log_path), 'sha256': digest(log_path),
                'success_batch_count': log.count('[✓ SUCCESS]'), 'failed_batch_count': log.count('[✗ FAIL]'),
                'exception_batch_count': log.count('[!] Exception'),
                'exception_lines': [l for l in log.splitlines() if '[!] Exception' in l],
                'finish': re.findall(r'Finished in .*', log),
                'first_lines': log.splitlines()[:14], 'last_lines': log.splitlines()[-14:]}
    after = {str(p.relative_to(ROOT)): digest(p) for p in source_files}
    e['input_changed_during_audit'] = [n for n in before if before[n] != after[n]]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(e, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    summary = {'evidence': str(OUT.relative_to(ROOT)),
               'individual_words': len(entries), 'jawi_missing': len(e['enriched']['missing_jawi']),
               'syllables_missing': len(e['enriched']['missing_syllables']),
               'invalid_nonempty_jawi': e['enriched']['invalid_nonempty_jawi'],
               'question_run_entries': len(e['enriched']['question_mark_runs']),
               'validator_pass': e['production_validator']['pass_count'],
               'validator_fail_reasons': dict(collections.Counter(results.values())),
               'nested_issue_entries': len(e['enriched']['nested_issue_entries']),
               'senses_count': e['enriched']['sense_count'],
               'senses_without_two_collocations': e['enriched']['senses_without_two_collocations'],
               'historical_story_count': e['enriched']['historical_story_count'],
               'web': e['web']['manifest'], 'isolated_export': e['isolated_export'],
               'input_changed_during_audit': e['input_changed_during_audit']}
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
