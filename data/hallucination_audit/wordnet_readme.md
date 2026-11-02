---
license: mit
language:
- ms
- id
source_datasets:
- omw
tags:
- wordnet
- malay
- indonesian
- dictionary
- synonyms
size_categories:
- 10K<n<100K
---

# Melayu wordnet — Wordnet Bahasa (OMW) (224,578 rows)

Malay (105,028) and Indonesian (119,550) synset data from
[Wordnet Bahasa](http://wn-msa.sourceforge.net/) as packaged by the
[Open Multilingual Wordnet](https://omwn.org) (omw-zsm + omw-ind).

## Columns
- `synset` (string): offset+pos key (joins to Princeton WordNet / CILI)
- `word` (string): lemma for lemma rows; empty otherwise
- `lang` (string): ms or id
- `role` (string): lemma | definition | example | related | hypernym | hyponym | other
- `value` (string): row payload (gloss/example/pointer)

## Provenance
- OMW data: https://github.com/omwn/omw-data (`wns/msa/wn-data-zsm.tab`, `wn-data-ind.tab`)
- extracted: 2026-10-28
- ms/id rows only; English WordNet lemmas NOT redistributed — join by `synset` key at will.

## License & citation
**MIT** (per OMW index). Cite: Nurril Hirfana Mohamed Noor, Suerya Sapuan and Francis
Bond, 2011, *"Creating the open Wordnet Bahasa"*, PACLIC 25. Aggregation cite:
Bond & Paik, 2012, *A survey of wordnets and their licenses*, GWC 2012.
