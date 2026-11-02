"""Verify the Batch 3 delivery without invoking the synthesis pipeline or network."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORDS = 'dengan anda tahu ke kami ya dari dalam sini semua'.split()


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result, f'duplicate JSON key: {key}'
        result[key] = value
    return result


def read(path):
    raw = path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf'), f'UTF-8 BOM: {path}'
    text = raw.decode('utf-8', errors='strict')
    assert '\ufffd' not in text and '??' not in text, f'encoding corruption: {path}'
    assert all(ord(c) >= 32 or c in '\n\r\t' for c in text), path
    return json.loads(text, object_pairs_hook=pairs,
                      parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))


def fields(obj, names):
    assert isinstance(obj, dict) and set(obj) == set(names.split()), names


def strings(obj, names):
    assert all(isinstance(obj[k], str) and obj[k].strip() for k in names.split()), names


def has_word(word, text):
    return re.search(r'\b' + re.escape(word) + r'\b', text, re.I) is not None


entries = read(ROOT / 'data/enriched/batch_3.json')
assert isinstance(entries, list) and len(entries) == 10
assert [e['headword']['word'] for e in entries] == WORDS
pilot = {e['word']: e['rank'] for e in read(ROOT / 'data/pilot_50_candidates.json')}
corpus = {}
with (ROOT / 'raw/opensubtitles_frequency_ms_full.txt').open(encoding='utf-8') as stream:
    for rank, line in enumerate(stream, 1):
        word = line.split()[0]
        if word in WORDS and word not in corpus:
            corpus[word] = rank
        if len(corpus) == len(WORDS):
            break

jawi_matches = syllable_matches = 0
excluded = {'by', 'with', 'deep', 'all', 'everything', 'yah', 'yha', 'yakk', 'yahhh'}
for entry in entries:
    fields(entry, 'headword morphology senses dual_scenarios spoken_shortcuts cultural_pragmatics etymology')
    head = entry['headword']
    word = head['word']
    fields(head, 'word syllables ipa jawi frequency_rank status')
    strings(head, 'word syllables ipa jawi status')
    assert type(head['frequency_rank']) is int
    assert head['frequency_rank'] == corpus[word] == pilot[word]
    assert head['status'] in {'official', 'colloquial', 'loanword'}
    assert head['ipa'][0] + head['ipa'][-1] in {'//', '[]'}
    assert all('ARABIC' in unicodedata.name(c, '') for c in head['jawi'])
    cache_path = ROOT / 'data/prpm_raw' / f'{word}.json'
    if not cache_path.exists():
        cache_path = ROOT / 'raw/prpm_cache' / f'{word}.json'
    cache = read(cache_path) if cache_path.exists() else {}
    if cache.get('jawi'):
        assert head['jawi'] == cache['jawi'], word
        jawi_matches += 1
    if cache.get('syllables'):
        assert head['syllables'] == cache['syllables'], word
        syllable_matches += 1

    morph = entry['morphology']
    fields(morph, 'is_root root_word affix affix_type formula pattern_note word_family')
    strings(morph, 'root_word affix_type formula pattern_note')
    assert type(morph['is_root']) is bool and morph['is_root']
    assert morph['root_word'] == word
    assert morph['affix'] is None and morph['affix_type'] == 'none'
    assert morph['formula'] == f'∅ + {word} → {word}'
    assert isinstance(morph['word_family'], list)
    for family in morph['word_family']:
        fields(family, 'word affix gloss')
        strings(family, 'word affix gloss')
        assert re.search('[\u4e00-\u9fff]', family['gloss']) and '/' in family['gloss']

    senses = entry['senses']
    assert isinstance(senses, list) and senses
    assert [s['id'] for s in senses] == list(range(1, len(senses) + 1))
    for sense in senses:
        fields(sense, 'id pos zh_definition en_definition ms_definition nuances')
        strings(sense, 'pos zh_definition en_definition ms_definition nuances')
        assert type(sense['id']) is int
        assert sense['pos'] in {'verb', 'noun', 'adjective', 'adverb', 'pronoun',
                               'preposition', 'conjunction', 'particle'}
        assert re.search('[\u4e00-\u9fff]', sense['zh_definition'])

    scenarios = entry['dual_scenarios']
    assert isinstance(scenarios, list) and len(scenarios) == 2
    assert [s['scenario'] for s in scenarios] == ['formal', 'colloquial']
    formal, spoken = scenarios
    fields(formal, 'scenario context ms zh en')
    strings(formal, 'scenario context ms zh en')
    assert has_word(word, formal['ms']), word
    fields(spoken, 'scenario context ms_spoken ms_standard zh en spoken_features')
    strings(spoken, 'scenario context ms_spoken ms_standard zh en')
    assert has_word(word, spoken['ms_standard']), word
    assert isinstance(spoken['spoken_features'], list) and spoken['spoken_features']
    assert all(isinstance(x, str) and x.strip() for x in spoken['spoken_features'])
    assert re.search(r'\b(lah|jom|kat|dah|nak|tak|ni|tu|dulu)\b', spoken['ms_spoken'], re.I)
    for scenario in scenarios:
        assert re.search('[\u4e00-\u9fff]', scenario['zh'])

    assert isinstance(entry['spoken_shortcuts'], list)
    for shortcut in entry['spoken_shortcuts']:
        fields(shortcut, 'abbr full_form note')
        strings(shortcut, 'abbr full_form note')
        assert shortcut['abbr'] not in excluded
    culture = entry['cultural_pragmatics']
    fields(culture, 'register politeness_note usage_etiquette')
    strings(culture, 'register politeness_note usage_etiquette')
    assert culture['register'] in {'standard', 'formal', 'colloquial', 'intimate', 'taboo'}
    etymology = entry['etymology']
    fields(etymology, 'origin source_language root_origin cognitive_memory_aid')
    strings(etymology, 'origin source_language root_origin cognitive_memory_aid')
    assert read(ROOT / 'data/enriched' / f'{word}.json') == entry, word

by_word = {e['headword']['word']: e for e in entries}
assert by_word['dalam']['headword']['jawi'] == 'دالم'
assert by_word['dalam']['headword']['syllables'] == 'da.lam'
assert by_word['ke']['headword']['jawi'] == 'ک'
assert by_word['ya']['headword']['jawi'] == 'ياء'
assert by_word['semua']['headword']['syllables'] == 'se.mua'
assert '不包括' in by_word['kami']['senses'][0]['zh_definition']
assert 'daripada' in json.dumps(by_word['dari'], ensure_ascii=False)
assert 'di dalam' in json.dumps(by_word['dalam'], ensure_ascii=False)
assert any(s['pos'] == 'particle' for s in by_word['ke']['senses'])
assert by_word['anda']['spoken_shortcuts'] == []

prior_hashes = 0
for batch in [1, 2]:
    prior = read(ROOT / f'data/audit/batch_{batch}_verification.json')
    for item in prior['files']:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256'], item['path']
        prior_hashes += 1

files = []
for name in ['batch_3'] + WORDS:
    path = ROOT / 'data/enriched' / f'{name}.json'
    raw = path.read_bytes()
    files.append({'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw),
                  'sha256': hashlib.sha256(raw).hexdigest()})
report = {
    'batch': 3, 'checked_at_utc': datetime.now(timezone.utc).isoformat(), 'result': 'passed',
    'entry_count': len(entries), 'sense_count': sum(len(e['senses']) for e in entries),
    'scenario_count': sum(len(e['dual_scenarios']) for e in entries),
    'individual_file_count': len(WORDS), 'top_level_key_count': 7,
    'checks': [
        'strict UTF-8 JSON; no BOM, duplicate keys, non-finite values or damaged placeholders',
        'exact seven dimensions and all nested fields; allowed enums and scalar/list types',
        'ordered unique headwords and consecutive sense ids; basic-word formulas',
        'bilingual family glosses; Chinese definitions and Arabic-script Jawi',
        'formal and colloquial scenarios, target words, translations and spoken-feature annotations',
        'frequency ranks independently matched to full local subtitle corpus and pilot list',
        'all available local PRPM Jawi and syllable values preserved',
        'individual JSON objects equal their entries in batch_3.json',
        'excluded English shortcut mappings; targeted pronoun and preposition distinctions present',
        'all 22 delivery hashes from Batches 1 and 2 unchanged'
    ],
    'prpm_cached_jawi_exact_matches': jawi_matches,
    'prpm_cached_syllables_exact_matches': syllable_matches,
    'previous_delivery_hashes_unchanged': prior_hashes,
    'frequency_ranks': {w: corpus[w] for w in WORDS},
    'linguistic_review': 'Editorial self-review completed; automated checks do not certify independent expert review.',
    'evidence_limits': [
        'ke Jawi taken from local Kaikki; independent DBP preposition Jawi headword not retrieved',
        'ke and ya single-syllable divisions are editorial; dalam DBP division retrieved online',
        'ya affirmative etymology uncertain; Arabic etymology restricted to vocative and letter-name senses',
        'dari earlier etymological source unverified; inscription first-attestation dates not asserted',
        'DBP quotations, DBP-based paraphrases and Kaikki-based editorial senses explicitly distinguished',
        'single headword metadata cannot encode every homograph; scope and pronunciation differences labelled'
    ],
    'notes': 'docs/BATCH_3_NOTES.md', 'files': files
}
path = ROOT / 'data/audit/batch_3_verification.json'
path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps({k: report[k] for k in ['result', 'entry_count', 'sense_count', 'scenario_count',
                                       'individual_file_count', 'prpm_cached_jawi_exact_matches',
                                       'prpm_cached_syllables_exact_matches',
                                       'previous_delivery_hashes_unchanged']}))
