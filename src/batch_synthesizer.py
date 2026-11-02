"""
Open-Melayu: Track 2 Batch Synthesizer using Codex CLI (gpt-6.1-sol / high)
- Merges PRPM cache, Kaikki IPA/etymology, WordNet, Malaya colloquial rules, Rootwords, and Tatoeba sentences.
- Produces the authoritative 7-dimension schema for each word.
- Invokes Codex CLI strictly via UTF-8 stdin without user relay.
- Validates resulting JSON and writes to data/enriched/{word}.json and batch file.
"""
import os
import sys
import json
import bz2
import csv
import subprocess
import time

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"c:\Users\d\Documents\open-melayu"
RAW_DIR = os.path.join(ROOT_DIR, "raw")
DATA_DIR = os.path.join(ROOT_DIR, "data")
ENRICHED_DIR = os.path.join(DATA_DIR, "enriched")
TASKS_DIR = os.path.join(ROOT_DIR, ".codex_tasks")

os.makedirs(ENRICHED_DIR, exist_ok=True)
os.makedirs(TASKS_DIR, exist_ok=True)

class ResourceLoader:
    def __init__(self):
        print("[*] Loading offline resources for synthesis...")
        t0 = time.time()
        
        # 1. Colloquial rules
        with open(os.path.join(RAW_DIR, "malaya_colloquial_rules.json"), "r", encoding="utf-8") as f:
            self.colloquial_rules = json.load(f)
            
        # Reverse map for shortcuts: target_word -> [shortcuts]
        self.reverse_shortcuts = {}
        for short, full in self.colloquial_rules.items():
            full_w = full.lower().strip()
            if full_w not in self.reverse_shortcuts:
                self.reverse_shortcuts[full_w] = []
            self.reverse_shortcuts[full_w].append(short)

        # 2. Root words
        with open(os.path.join(RAW_DIR, "malay_rootwords.json"), "r", encoding="utf-8") as f:
            self.roots = json.load(f)

        # 3. Kaikki Malay
        self.kaikki = {}
        with open(os.path.join(RAW_DIR, "kaikki_malay.jsonl"), "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                w = item.get("word", "").lower()
                if w not in self.kaikki:
                    self.kaikki[w] = []
                self.kaikki[w].append(item)

        # 4. Tatoeba Malay sentences
        self.sentences = {}
        zsm_file = os.path.join(RAW_DIR, "zsm_sentences.tsv.bz2")
        if os.path.exists(zsm_file):
            with bz2.open(zsm_file, "rt", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter='\t')
                for row in reader:
                    if len(row) >= 3:
                        self.sentences[row[0]] = row[2]
                        
        print(f"[+] Resources loaded in {time.time()-t0:.2f}s (Colloquial: {len(self.colloquial_rules)}, Roots: {len(self.roots)}, Kaikki: {len(self.kaikki)}, Sentences: {len(self.sentences)})")

    def get_prpm_data(self, word: str) -> dict:
        w = word.lower().strip()
        reserved_set = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2'}
        raw_fname = f"_reserved_{w}.json" if w in reserved_set else f"{w}.json"
        raw_path = os.path.join(ROOT_DIR, "data", "prpm_raw", raw_fname)
        if os.path.exists(raw_path):
            try:
                with open(raw_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        cache_path = os.path.join(RAW_DIR, "prpm_cache", f"{w}.json")
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Check if root has it
        root = self.roots.get(w)
        if root and root != w:
            root_fname = f"_reserved_{root}.json" if root in reserved_set else f"{root}.json"
            root_raw = os.path.join(ROOT_DIR, "data", "prpm_raw", root_fname)
            if os.path.exists(root_raw):
                try:
                    with open(root_raw, "r", encoding="utf-8") as f:
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

    def get_word_packet(self, word: str) -> dict:
        w = word.lower().strip()
        prpm = self.get_prpm_data(w)
        kaikki_entries = self.kaikki.get(w, [])
        
        # Sounds / IPA
        ipas = []
        etymologies = []
        glosses = []
        for k in kaikki_entries:
            for s in k.get("sounds", []) or []:
                if s.get("ipa"):
                    ipas.append(s.get("ipa"))
            if k.get("etymology_text"):
                etymologies.append(k.get("etymology_text"))
            for sense in k.get("senses", []) or []:
                for g in sense.get("glosses", []) or []:
                    glosses.append(g)

        # Root
        root = self.roots.get(w, w)
        
        # Shortcuts
        shortcuts = self.reverse_shortcuts.get(w, [])
        is_shortcut_for = self.colloquial_rules.get(w)
        
        # Sentences
        sample_sents = []
        for sid, text in self.sentences.items():
            if f" {w} " in f" {text.lower()} ":
                sample_sents.append(text)
                if len(sample_sents) >= 4:
                    break

        return {
            "word": w,
            "prpm": prpm,
            "ipas": list(set(ipas)),
            "etymologies": list(set(etymologies)),
            "kaikki_glosses": glosses[:8],
            "root": root,
            "is_shortcut_for": is_shortcut_for,
            "shortcuts": shortcuts[:6],
            "sample_sentences": sample_sents
        }

SCHEMA_TEMPLATE = """
Each entry in the output array MUST follow this exact 7-dimension JSON schema:
{
  "headword": {
    "word": "<word>",
    "syllables": "<e.g. be.la.jar, use DBP syllables if available or phonetic break>",
    "ipa": "<IPA phonetic notation, e.g. /bəˈlad͡ʒa(r)/>",
    "jawi": "<Official Jawi script, e.g. بلاجر>",
    "frequency_rank": <integer or null>,
    "status": "official" | "colloquial" | "loanword"
  },
  "morphology": {
    "is_root": true | false,
    "root_word": "<Kata Dasar root, or self if is_root>",
    "affix": "<prefix/suffix/circumfix or null, e.g. ber-, meN-, peN-...-an>",
    "affix_type": "prefix" | "suffix" | "circumfix" | "infix" | "none",
    "formula": "<Mathematical formula e.g. ber- + ajar → belajar>",
    "pattern_note": "<Concise morphological phonological rule, e.g. dissimilation or nasal assimilation>",
    "word_family": [
      { "word": "<related family word>", "affix": "<affix>", "gloss": "<Chinese & English brief meaning>" }
    ]
  },
  "senses": [
    {
      "id": 1,
      "pos": "verb" | "noun" | "adjective" | "adverb" | "pronoun" | "preposition" | "conjunction" | "particle",
      "zh_definition": "<Comprehensive, precise Chinese definition>",
      "en_definition": "<Clear English definition>",
      "ms_definition": "<DBP Kamus Dewan official Malay definition>",
      "nuances": "<Pragmatic notes, distinctions from English/Chinese equivalents, collocations>"
    }
  ],
  "dual_scenarios": [
    {
      "scenario": "formal",
      "context": "公文 / 新闻 / 课堂 / 正式书面语",
      "ms": "<Natural formal Malaysian Malay sentence>",
      "zh": "<Accurate Chinese translation>",
      "en": "<Accurate English translation>"
    },
    {
      "scenario": "colloquial",
      "context": "大马日常生活口语 / WhatsApp 社交聊天 (Bahasa Pasar)",
      "ms_spoken": "<Authentic spoken Malaysian sentence with common spoken contractions/particles lah/kan/dah/nak/kat>",
      "ms_standard": "<Standard equivalent Malay sentence>",
      "zh": "<Vibrant, authentic Chinese colloquial translation>",
      "en": "<Natural English colloquial translation>",
      "spoken_features": ["<explanation of abbreviations or colloquial particles used>"]
    }
  ],
  "spoken_shortcuts": [
    { "abbr": "<SMS/chat abbreviation, e.g. tak, bljr, xde, sbb, diorang, kat>", "full_form": "<standard word>", "note": "<usage frequency / context note>" }
  ],
  "cultural_pragmatics": {
    "register": "standard" | "formal" | "colloquial" | "intimate" | "taboo",
    "politeness_note": "<Register politeness guidance in Malaysian multiracial society (e.g. saya vs aku, awak vs kau)>",
    "usage_etiquette": "<Real-world usage etiquette and pragmatic tips>"
  },
  "etymology": {
    "origin": "<Austronesian (Inherited) / Sanskrit / Arabic / Tamil / Hokkien / English / Dutch / Portuguese / Persian>",
    "source_language": "<Language name>",
    "root_origin": "<Original etymon or root note>",
    "cognitive_memory_aid": "<Memorable cognitive mnemonic or morphological decomposition to remember the word>"
  }
}
"""

def generate_batch_prompt(batch_words: list, packets: list, batch_id: int) -> str:
    prompt = f"""# Task: Synthesize Open-Melayu 7-Dimension Dictionary Entries (Batch {batch_id})

You are the Lead Lexicographer and Codex Core Engineer for Open-Melayu: the zero-compromise, best-in-class Malay-Chinese-English Cognitive Dictionary.

## Words to Synthesize in this Batch:
{json.dumps(batch_words, ensure_ascii=False)}

## Raw Ground Truth Materials:
Below are the assembled raw linguistic facts from official DBP PRPM, Kaikki, Malaya colloquial rules, Malay root words, and Tatoeba authentic sentences:

```json
{json.dumps(packets, ensure_ascii=False, indent=2)}
```

## Schema Requirements:
{SCHEMA_TEMPLATE}

## Strict Quality Instructions:
1. **Zero Hallucination on Syllables & Jawi**: Use the official DBP PRPM syllables and Jawi whenever provided in raw materials. If PRPM was grouped under root, extract the exact DBP Jawi and syllables for the derived form.
2. **Formulaic Morphology**: Explicitly write the math-like formula `affix + root → surface_word` (e.g. `ber- + ajar → belajar`, `meN- (meng-) + ajar → mengajar`, `peN- (pel-) + ajar → pelajar`).
3. **Dual Scenarios (Formal vs Colloquial)**:
   - Formal MUST sound like authentic Malaysian Berita Harian / DBP standard.
   - Colloquial MUST sound like real Malaysian everyday spoken Malay / WhatsApp chat (using words like *dah*, *nak*, *kat*, *jom*, *kot*, particles *lah/kan*).
4. **Cultural Pragmatics**: For pronouns like `saya`/`aku`/`awak`/`kau`, give razor-sharp Malaysian social etiquette guidance (who can say it to whom without being considered *kurang ajar*).
5. **Output Destination**:
   - Write the synthesized JSON array containing all {len(batch_words)} words to:
     `c:\\Users\\d\\Documents\\open-melayu\\data\\enriched\\batch_{batch_id}.json`
   - Also write each individual word entry to:
     `c:\\Users\\d\\Documents\\open-melayu\\data\\enriched\\<word>.json`
   - Your response should confirm the files written and summarize the entries.
"""
    return prompt

def execute_codex_batch(batch_id: int, prompt_content: str):
    task_file = os.path.join(TASKS_DIR, f"task_batch_{batch_id}.md")
    with open(task_file, "w", encoding="utf-8") as f:
        f.write(prompt_content)

    print(f"[*] Dispatching Batch {batch_id} to Codex CLI (gpt-6.1-sol / high)...")
    cmd = (
        f'Get-Content -Raw -Encoding UTF8 "{task_file}" | '
        f'codex exec -s workspace-write -c approval_policy="never" -c sandbox_workspace_write.network_access=true -C "{ROOT_DIR}" -'
    )
    
    t0 = time.time()
    proc = subprocess.run(
        ["powershell", "-NoProfile", "-Command", cmd],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore"
    )
    duration = round(time.time() - t0, 1)
    
    if proc.returncode == 0:
        print(f"[+] Batch {batch_id} completed successfully in {duration}s!")
        print(proc.stdout[-500:])
    else:
        print(f"[-] Batch {batch_id} failed with exit code {proc.returncode} in {duration}s:")
        print(proc.stderr[:800])
        print(proc.stdout[:800])

if __name__ == "__main__":
    loader = ResourceLoader()
    
    # Read 15,000 candidate pool
    pool_path = os.path.join(DATA_DIR, "candidate_pool_15k.json")
    with open(pool_path, "r", encoding="utf-8") as f:
        candidates = json.load(f)
        
    all_words = [x["word"] for x in candidates]
    
    batch_size = 10
    batch_idx = 3 # Default to Batch 3 (ranks 21-30)
    if len(sys.argv) > 1:
        batch_idx = int(sys.argv[1])
        
    start_pos = (batch_idx - 1) * batch_size
    batch_words = all_words[start_pos:start_pos + batch_size]
    
    print(f"\n[*] Preparing Batch {batch_idx} (ranks {start_pos+1} to {start_pos+len(batch_words)}): {batch_words}")
    packets = [loader.get_word_packet(w) for w in batch_words]
    prompt = generate_batch_prompt(batch_words, packets, batch_idx)
    
    execute_codex_batch(batch_idx, prompt)
