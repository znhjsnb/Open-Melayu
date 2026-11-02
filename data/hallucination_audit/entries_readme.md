---
license: cc-by-sa-4.0
language:
- ms
- id
language_creators:
- machine
- crowd
source_datasets:
- kaikki
- wiktionary
tags:
- dictionary
- malay
- indonesian
- wiktionary
- kaikki
size_categories:
- 10K<n<100K
---

# Melayu kaikki entries (55,997 rows)

Machine-readable Malay (17,485) and Indonesian (38,512)
dictionary entries extracted from English Wiktionary by
[wiktextract](https://github.com/tatuylonen/wiktextract) and served as
[kaikki.org](https://kaikki.org) machine-readable dictionary snapshots,
lightly processed to parquet.

## Columns

- `entry_id` (string): sha1(word	pos) as 16-hex id, stable join key
- `word` (string): headword: Malay (ms) or Indonesian (id) lemma as written in Wiktionary
- `lang` (string): Wiktionary language code: ms or id (from the wiki language template, not the title)
- `pos` (string): part of speech, Wiktionary label (noun, verb, adjective, suffix, ...)
- `ipa` (list<string>): transcriptions found in the entry's sounds section
- `glosses` (list<string>): English glosses for all senses, concatenated
- `tags` (list<string>): sense-level tags (register, usage, grammar markers)
- `topics` (list<string>): Wiktionary topic categories
- `forms` (list<string>): '<form>\t<tag1|tag2>' — inflected/alternative forms incl. Jawi
- `audio_urls` (list<string>): Wikimedia CDN audio (mp3 preferred, ogg fallback)
- `etymology_text` (string): English-language etymology as displayed on Wiktionary
- `wikt_url` (string): link back to the Wiktionary entry page
- `source` (string): kaikki.org URL the snapshot was taken from

## Provenance
- kaikki.org snapshot: 
- extracted (kaikii.org): 2026-10-27, from the enwiktionary dump dated 2026-10-01
- processing pipeline: `dataset/kaikki` in the `melayu` repo (`make download` → `make process` → `make upload`)

## License & attribution
Distributed under the Wiktionary dual license: **CC BY-SA 4.0** and **GFDL**
(both downstream requirements). If you use this data in academic research, cite
Tatu Ylonen: *Wiktextract: Wiktionary as Machine-Readable Structured Data*,
LREC 2022.