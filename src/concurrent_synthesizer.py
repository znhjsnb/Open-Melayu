"""
Open-Melayu 30-Way Concurrent Synthesizer (Track 2 Mass Production)
- 30 parallel workers using ThreadPoolExecutor
- 5 words per micro-batch
- Strict 8-dimension schema (including historical evolution stories & collocations)
- Zero file write collisions via per-worker isolated staging directories
- Central schema validator before atomic commit to data/enriched/
- Real-time progress logging
"""

import os
import sys
import json
import bz2
import csv
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# UTF-8 stdout
if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(r"c:\Users\d\Documents\open-melayu")
RAW_DIR = ROOT_DIR / "raw"
DATA_DIR = ROOT_DIR / "data"
PRPM_RAW_DIR = DATA_DIR / "prpm_raw"
ENRICHED_DIR = DATA_DIR / "enriched"
STAGING_DIR = ROOT_DIR / ".tmp" / "codex_staging"
TASKS_DIR = ROOT_DIR / ".codex_tasks"

ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
STAGING_DIR.mkdir(parents=True, exist_ok=True)
TASKS_DIR.mkdir(parents=True, exist_ok=True)

WINDOWS_RESERVED = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2'}

class LinguisticKnowledgeBase:
    def __init__(self):
        print("[*] Loading offline linguistic knowledge base...")
        t0 = time.time()
        
        # 1. Colloquial rules & reverse mapping
        with open(RAW_DIR / "malaya_colloquial_rules.json", "r", encoding="utf-8") as f:
            self.colloquial_rules = json.load(f)
        self.reverse_shortcuts = {}
        for short, full in self.colloquial_rules.items():
            full_w = full.lower().strip()
            if full_w not in self.reverse_shortcuts:
                self.reverse_shortcuts[full_w] = []
            self.reverse_shortcuts[full_w].append(short)

        # 2. Root words
        with open(RAW_DIR / "malay_rootwords.json", "r", encoding="utf-8") as f:
            self.roots = json.load(f)

        # 3. Kaikki Malay
        self.kaikki = {}
        with open(RAW_DIR / "kaikki_malay.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                w = item.get("word", "").lower()
                if w not in self.kaikki:
                    self.kaikki[w] = []
                self.kaikki[w].append(item)

        # 4. Tatoeba Sentences
        self.sentences = {}
        zsm_file = RAW_DIR / "zsm_sentences.tsv.bz2"
        if zsm_file.exists():
            with bz2.open(zsm_file, "rt", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter='\t')
                for row in reader:
                    if len(row) >= 3:
                        self.sentences[row[0]] = row[2]

        print(f"[+] Knowledge base loaded in {time.time()-t0:.2f}s "
              f"(Roots: {len(self.roots)}, Kaikki: {len(self.kaikki)}, Sentences: {len(self.sentences)})")

    def get_prpm_data(self, word: str) -> dict:
        w = word.lower().strip()
        raw_fname = f"_reserved_{w}.json" if w in WINDOWS_RESERVED else f"{w}.json"
        raw_path = PRPM_RAW_DIR / raw_fname
        if raw_path.exists():
            try:
                with open(raw_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        # Check root
        root = self.roots.get(w)
        if root and root != w:
            root_fname = f"_reserved_{root}.json" if root in WINDOWS_RESERVED else f"{root}.json"
            root_path = PRPM_RAW_DIR / root_fname
            if root_path.exists():
                try:
                    with open(root_path, "r", encoding="utf-8") as f:
                        r_data = json.load(f)
                        return {
                            "word": word,
                            "found_in_prpm": True,
                            "derived_under_root": root,
                            "root_kamus_dewan": r_data.get("kamus_dewan"),
                            "root_syllables": r_data.get("syllables"),
                            "root_jawi": r_data.get("jawi")
                        }
                except Exception:
                    pass
        return {"word": word, "found_in_prpm": False}

    def assemble_word_packet(self, word: str, rank: int) -> dict:
        w = word.lower().strip()
        prpm = self.get_prpm_data(w)
        kaikki_entries = self.kaikki.get(w, [])
        
        ipas = []
        etyms = []
        glosses = []
        for k in kaikki_entries:
            for s in k.get("sounds", []) or []:
                if s.get("ipa"):
                    ipas.append(s.get("ipa"))
            if k.get("etymology_text"):
                etyms.append(k.get("etymology_text"))
            for sense in k.get("senses", []) or []:
                for g in sense.get("glosses", []) or []:
                    glosses.append(g)

        sample_sents = []
        for sid, text in self.sentences.items():
            if f" {w} " in f" {text.lower()} ":
                sample_sents.append(text)
                if len(sample_sents) >= 3:
                    break

        return {
            "word": w,
            "rank": rank,
            "prpm": prpm,
            "ipas": list(set(ipas)),
            "etymologies": list(set(etyms)),
            "kaikki_glosses": glosses[:6],
            "root": self.roots.get(w, w),
            "shortcuts": self.reverse_shortcuts.get(w, [])[:4],
            "sample_sentences": sample_sents
        }

SCHEMA_TEMPLATE = """
Each word entry in the array must strictly follow this 8-dimension JSON schema:
{
  "headword": {
    "word": "<word>",
    "syllables": "<e.g. de·ngan, use PRPM syllables if present>",
    "ipa": "<IPA phonetic notation>",
    "jawi": "<Official Jawi script, e.g. دڠن, from PRPM>",
    "frequency_rank": <integer rank>,
    "tags": ["CEFR-A1" | "CEFR-A2" | "CEFR-B1" | "CEFR-B2", "SPM必考" | "日常高频" | "公文标准"]
  },
  "morphology": {
    "is_root": true | false,
    "root_word": "<Kata Dasar root>",
    "affix": "<prefix/suffix/circumfix or null>",
    "affix_type": "prefix" | "suffix" | "circumfix" | "none",
    "formula": "<Math-like formula, e.g. ber- + jalan → berjalan or ∅ + saya → saya>",
    "pattern_note": "<Concise phonological rule or state>",
    "word_family": [{ "word": "<family word>", "affix": "<affix>", "gloss": "<Chinese brief meaning>" }]
  },
  "senses": [
    {
      "id": 1,
      "pos": "verb" | "noun" | "adjective" | "adverb" | "pronoun" | "preposition" | "conjunction" | "particle",
      "zh_definition": "<Precise, natural Chinese definition>",
      "ms_definition": "<DBP Kamus Dewan official Malay definition>",
      "nuances": "<Pragmatic distinctions, usage caveats>",
      "collocations": [
        { "ms": "<High frequency Malay collocation>", "zh": "<Chinese meaning>" },
        { "ms": "<Second high frequency collocation>", "zh": "<Chinese meaning>" }
      ]
    }
  ],
  "dual_scenarios": [
    {
      "scenario": "formal",
      "context": "公文 / 新闻报章 / 会议致辞",
      "ms": "<Authentic standard Malaysian Malay sentence>",
      "zh": "<Natural Chinese translation>",
      "en": "<Accurate English translation>"
    },
    {
      "scenario": "colloquial",
      "context": "大马日常生活口语 / WhatsApp 社交聊天 (Bahasa Pasar)",
      "ms_spoken": "<Authentic spoken Malaysian sentence with particles lah/kan/dah/nak/kat/kot>",
      "ms_standard": "<Standard equivalent sentence>",
      "zh": "<Colloquial Chinese translation>",
      "spoken_features": ["<explanation of spoken contraction or particle used>"]
    }
  ],
  "spoken_shortcuts": [
    { "abbr": "<SMS/chat contraction>", "full_form": "<standard word>", "note": "<context note>" }
  ],
  "cultural_pragmatics": {
    "register": "standard" | "formal" | "colloquial" | "intimate",
    "politeness_note": "<Register politeness guidance in Malaysian multiracial society>",
    "usage_etiquette": "<Real-world etiquette guidance, pronoun boundaries, and taboos>"
  },
  "etymology": {
    "origin": "<Austronesian / Sanskrit / Arabic / Tamil / Hokkien / English / Dutch / Portuguese>",
    "source_language": "<Language name>",
    "root_origin": "<Original etymon or root note>",
    "historical_story": "<Lively narrative of the word's historical origin, cultural maritime context, and how it evolved into modern Malay>",
    "cognitive_memory_aid": "<Memorable cognitive mnemonic or hook>"
  }
}
"""

def validate_entry(entry: dict) -> tuple[bool, str]:
    if not isinstance(entry, dict):
        return False, "Entry is not a dict"
    for dim in ['headword', 'morphology', 'senses', 'dual_scenarios', 'spoken_shortcuts', 'cultural_pragmatics', 'etymology']:
        if dim not in entry:
            return False, f"Missing required dimension: {dim}"
    head = entry.get('headword', {})
    if not head.get('word') or not head.get('jawi'):
        return False, "Headword missing word or Jawi"
    senses = entry.get('senses', [])
    if not isinstance(senses, list) or len(senses) == 0:
        return False, "Senses must be non-empty list"
    etym = entry.get('etymology', {})
    if not etym.get('historical_story'):
        return False, "Etymology missing historical_story"
    return True, "Valid"

def execute_worker_batch(worker_id: int, batch_id: int, packets: list) -> tuple[int, bool, int, str]:
    worker_staging_dir = STAGING_DIR / f"worker_{worker_id}"
    worker_staging_dir.mkdir(parents=True, exist_ok=True)
    
    target_output_file = worker_staging_dir / f"batch_{batch_id}.json"
    prompt_file = TASKS_DIR / f"task_batch_{batch_id}.md"

    words_list = [p['word'] for p in packets]
    
    prompt = f"""# Task: Synthesize Open-Melayu 8-Dimension Cognitive Entries (Batch {batch_id})
Words to synthesize ({len(packets)} words): {json.dumps(words_list, ensure_ascii=False)}

## Assembled Ground Truth Packets:
```json
{json.dumps(packets, ensure_ascii=False, indent=2)}
```

## Schema Requirements:
{SCHEMA_TEMPLATE}

## Strict Instructions:
1. **Zero Hallucination on Syllables & Jawi**: Use the official DBP syllables and Jawi provided in the raw packets.
2. **Historical Evolution Story**: In `etymology.historical_story`, provide a vivid 2-3 sentence cultural & historical narrative of how the word emerged and evolved.
3. **Collocations**: In `senses[].collocations`, provide 2 authentic collocations with Chinese translations.
4. **Dual Scenarios**: Formal MUST sound like standard Malaysian media; Colloquial MUST sound like authentic WhatsApp chat.
5. **Output Destination**: Write the final JSON array containing all {len(packets)} entries directly to:
`{str(target_output_file).replace('\\', '/')}`
"""

    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)

    cmd = (
        f'Get-Content -Raw -Encoding UTF8 "{prompt_file}" | '
        f'codex exec -s workspace-write -c approval_policy="never" -c sandbox_workspace_write.network_access=true -C "{ROOT_DIR}" -'
    )

    t0 = time.time()
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        timeout=600
    )
    duration = round(time.time() - t0, 1)

    if not target_output_file.exists():
        return batch_id, False, 0, f"Worker {worker_id} output file missing after {duration}s"

    try:
        with open(target_output_file, "r", encoding="utf-8") as sf:
            batch_data = json.load(sf)
    except Exception as e:
        return batch_id, False, 0, f"Worker {worker_id} JSON parse error: {e}"

    if not isinstance(batch_data, list) or len(batch_data) != len(packets):
        return batch_id, False, 0, f"Worker {worker_id} returned {len(batch_data) if isinstance(batch_data, list) else 0} items, expected {len(packets)}"

    # Validate and commit
    valid_count = 0
    for entry in batch_data:
        ok, err = validate_entry(entry)
        if not ok:
            return batch_id, False, valid_count, f"Validation error on {entry.get('headword',{}).get('word')}: {err}"
        
        w = entry['headword']['word'].strip().lower()
        w_file = ENRICHED_DIR / f"{w}.json"
        with open(w_file, "w", encoding="utf-8") as wf:
            json.dump(entry, wf, ensure_ascii=False, indent=2)
        valid_count += 1

    return batch_id, True, valid_count, f"Worker {worker_id} successfully produced {valid_count} words in {duration}s"

def run_30_way_production(target_words_count=1000, concurrency=30):
    kb = LinguisticKnowledgeBase()

    # Load candidate pool
    with open(DATA_DIR / "candidate_pool_15k.json", "r", encoding="utf-8") as f:
        candidates = json.load(f)

    # Filter out already enriched words
    existing_enriched = set()
    for p in ENRICHED_DIR.glob("*.json"):
        if not p.name.startswith("batch_"):
            existing_enriched.add(p.stem.lower())

    print(f"[*] Already enriched in data/enriched: {len(existing_enriched)} words")

    words_to_produce = []
    for item in candidates[:target_words_count]:
        w = item["word"].strip().lower()
        if w not in existing_enriched:
            words_to_produce.append(item)

    print(f"[*] Words remaining to reach rank {target_words_count}: {len(words_to_produce)} words")
    if not words_to_produce:
        print("[+] Target already reached!")
        return

    # Partition into 5-word micro-batches
    micro_batch_size = 5
    micro_batches = []
    for i in range(0, len(words_to_produce), micro_batch_size):
        batch_slice = words_to_produce[i:i + micro_batch_size]
        batch_packets = [kb.assemble_word_packet(x["word"], x["rank"]) for x in batch_slice]
        batch_id = 100 + (i // micro_batch_size)
        micro_batches.append((batch_id, batch_packets))

    print(f"[*] Total micro-batches to process: {len(micro_batches)} (5 words/batch)")
    print(f"[*] Firing up {concurrency}-way parallel ThreadPoolExecutor...")

    start_time = time.time()
    total_committed = len(existing_enriched)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_map = {}
        for idx, (b_id, pkts) in enumerate(micro_batches):
            worker_id = idx % concurrency
            fut = executor.submit(execute_worker_batch, worker_id, b_id, pkts)
            future_map[fut] = (b_id, pkts)

        for fut in as_completed(future_map):
            b_id, pkts = future_map[fut]
            try:
                res_bid, success, count, msg = fut.result()
                if success:
                    total_committed += count
                    elapsed = time.time() - start_time
                    words_per_min = round(total_committed / (elapsed / 60), 1) if elapsed > 0 else 0
                    print(f"[✓ SUCCESS] Batch {res_bid} committed! Total Enriched: {total_committed}/{target_words_count} | Speed: {words_per_min} words/min")
                else:
                    print(f"[✗ FAIL] Batch {b_id} failed: {msg}")
            except Exception as e:
                print(f"[!] Exception on batch {b_id}: {e}")

    print(f"\n================ PRODUCTION COMPLETE ================")
    print(f"Finished in {round(time.time() - start_time, 1)}s. Total Enriched: {total_committed}")
    print(f"=====================================================")

if __name__ == "__main__":
    target = 1000
    concurrency = 30
    if len(sys.argv) > 1:
        target = int(sys.argv[1])
    if len(sys.argv) > 2:
        concurrency = int(sys.argv[2])
    run_30_way_production(target_words_count=target, concurrency=concurrency)
