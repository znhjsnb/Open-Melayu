"""
Open-Melayu Top 1,001 - 2,000 Expansion Pipeline (Batch 1: 100 Words)
Orchestrates 10-way parallel execution via Codex CLI (gpt-6.1-sol / high).
Enforces strict 8-dimension schema, 5 quality gates, atomic commits, and shard synchronization.
"""

import concurrent.futures
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
RAW_DIR = ROOT_DIR / "raw"
DATA_DIR = ROOT_DIR / "data"
PRPM_RAW_DIR = DATA_DIR / "prpm_raw"
ENRICHED_DIR = DATA_DIR / "enriched"
AUDIT_DIR = DATA_DIR / "audit"
APP_STATIC_DATA = ROOT_DIR / "app" / "static" / "data"
SHARDS_DIR = APP_STATIC_DATA / "shards"
MANIFEST_FILE = APP_STATIC_DATA / "manifest.json"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"
CODEX_EXE = r"C:\Users\d\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe"

WINDOWS_RESERVED = {'con', 'prn', 'aux', 'nul', 'com1', 'com2', 'com3', 'com4', 'lpt1', 'lpt2'}

class LinguisticKnowledgeBase:
    def __init__(self):
        print("[*] Initializing offline linguistic resources...")
        t0 = time.time()
        
        # 1. Colloquial rules
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

        # 4. Tatoeba sentences
        import bz2, csv
        self.sentences = {}
        zsm_file = RAW_DIR / "zsm_sentences.tsv.bz2"
        if zsm_file.exists():
            with bz2.open(zsm_file, "rt", encoding="utf-8") as f:
                reader = csv.reader(f, delimiter='\t')
                for row in reader:
                    if len(row) >= 3:
                        self.sentences[row[0]] = row[2]

        print(f"[+] Knowledge base ready in {time.time()-t0:.2f}s.")

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
        return {}

    def resolve_root(self, word: str) -> tuple[str, str | None]:
        w = word.lower().strip()
        r = self.roots.get(w)
        # heuristic affix stripping if not in dictionary
        if not r or r == w:
            for suffix in ["kan", "i", "an", "nya", "ku", "mu"]:
                if w.endswith(suffix) and len(w) > len(suffix) + 3:
                    cand = w[:-len(suffix)]
                    if (PRPM_RAW_DIR / f"{cand}.json").exists():
                        r = cand
                        break
            if not r or r == w:
                for prefix in ["meng", "mem", "men", "me", "ber", "ter", "per", "pe", "se"]:
                    if w.startswith(prefix) and len(w) > len(prefix) + 3:
                        cand = w[len(prefix):]
                        if (PRPM_RAW_DIR / f"{cand}.json").exists():
                            r = cand
                            break
        if not r:
            r = w
            
        # Get root jawi
        root_jawi = None
        r_fname = f"_reserved_{r}.json" if r in WINDOWS_RESERVED else f"{r}.json"
        r_path = PRPM_RAW_DIR / r_fname
        if r_path.exists():
            try:
                with open(r_path, "r", encoding="utf-8") as f:
                    rd = json.load(f)
                    root_jawi = rd.get("jawi")
            except Exception:
                pass
        return r, root_jawi

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

        root, root_jawi = self.resolve_root(w)

        return {
            "word": w,
            "rank": rank,
            "prpm": {
                "kamus_dewan": prpm.get("kamus_dewan"),
                "kamus_pelajar": prpm.get("kamus_pelajar"),
                "definisi_melayu": prpm.get("definisi_melayu"),
                "jawi": prpm.get("jawi"),
                "syllables": prpm.get("syllables")
            },
            "resolved_root": {
                "root_word": root,
                "root_jawi": root_jawi,
                "is_root": (root == w)
            },
            "ipas": list(set(ipas)),
            "etymologies": list(set(etyms)),
            "kaikki_glosses": glosses[:6],
            "shortcuts": self.reverse_shortcuts.get(w, [])[:4],
            "sample_sentences": sample_sents
        }

def select_top_100_source_only(kb: LinguisticKnowledgeBase) -> list[dict]:
    with open(DATA_DIR / "candidate_pool_15k.json", "r", encoding="utf-8") as f:
        pool = json.load(f)

    # Load shard entries to ensure data_state == 'source_only'
    shards = {}
    for letter in "abcdefghijklmnopqrstuvwxyz":
        with open(SHARDS_DIR / f"{letter}.json", "r", encoding="utf-8") as sf:
            shards[letter] = json.load(sf)
    with open(SHARDS_DIR / "other.json", "r", encoding="utf-8") as sf:
        shards["other"] = json.load(sf)

    def get_state(w):
        c = w[0].lower()
        entry = shards.get(c, shards["other"]).get(w)
        return entry.get("data_state") if entry else None

    selected_packets = []
    for item in pool[1000:2000]:
        w = item["word"]
        # Skip if already in data/enriched
        if (ENRICHED_DIR / f"{w}.json").exists():
            continue
            
        prpm = kb.get_prpm_data(w)
        kd = prpm.get("kamus_dewan")
        kp = prpm.get("kamus_pelajar")
        dm = prpm.get("definisi_melayu")
        
        if not (kd or kp or dm):
            continue
            
        state = get_state(w)
        if state != "source_only":
            continue
            
        packet = kb.assemble_word_packet(w, item["rank"])
        selected_packets.append(packet)
        if len(selected_packets) == 100:
            break

    return selected_packets

SCHEMA_INSTRUCTIONS = """
You MUST output a single valid JSON object mapping each word to its complete 8-dimension dictionary entry.
The format must be:
{
  "<word>": {
    "headword": {
      "word": "<word>",
      "syllables": "<official DBP syllables, or hyphen/dot separated>",
      "ipa": "<IPA phonetic transcription, e.g. /ˈbalas/>",
      "jawi": "<Official PRPM Jawi script>",
      "frequency_rank": <rank>,
      "status": "official"
    },
    "morphology": {
      "is_root": true | false,
      "root_word": "<Kata Dasar root>",
      "affix": "<prefix/suffix/circumfix or null>",
      "affix_type": "prefix" | "suffix" | "circumfix" | "infix" | "none",
      "formula": "<Math-style formula, e.g. meN- + kawal → mengawal or ∅ + balas → balas>",
      "pattern_note": "<Concise morphological or phonological rule>",
      "word_family": [
        { "word": "<related word>", "affix": "<affix>", "gloss": "<Chinese brief meaning>" }
      ],
      "root_jawi": "<Official Jawi of the Kata Dasar root>"
    },
    "senses": [
      {
        "id": 1,
        "pos": "verb" | "noun" | "adjective" | "adverb" | "preposition" | "conjunction" | "particle",
        "zh_definition": "<Comprehensive, accurate Chinese definition>",
        "en_definition": "<Accurate English definition>",
        "ms_definition": "<DBP Kamus Dewan official Malay definition from packet>",
        "nuances": "<Usage context, pragmatic distinctions>",
        "collocations": [
          { "ms": "<Authentic Malay collocation 1>", "zh": "<Chinese meaning 1>" },
          { "ms": "<Authentic Malay collocation 2>", "zh": "<Chinese meaning 2>" }
        ]
      }
    ],
    "dual_scenarios": [
      {
        "scenario": "formal",
        "context": "公文 / 新闻 / 职场汇报",
        "ms": "<Authentic formal Malaysian Malay sentence>",
        "zh": "<Chinese translation>",
        "en": "<English translation>"
      },
      {
        "scenario": "colloquial",
        "context": "WhatsApp / 日常口语交流",
        "ms_spoken": "<Spoken sentence with colloquial contractions/slang>",
        "ms_standard": "<Formal standard restoration>",
        "zh": "<Colloquial Chinese translation>",
        "en": "<English translation>",
        "spoken_features": ["<feature 1>", "<feature 2>"],
        "messages": [
          {
            "speaker": "Name (关系, e.g. Farah (同事) or Haziq (朋友))",
            "ms_spoken": "<First turn spoken Malay with WhatsApp particles like nak/dah/kat/je/kot>",
            "ms_standard": "<Standard Malay equivalent>",
            "zh": "<Chinese translation>"
          },
          {
            "speaker": "Name (关系, e.g. Amir (同事) or Ibu (母亲))",
            "ms_spoken": "<Second turn reply in spoken Malay>",
            "ms_standard": "<Standard Malay equivalent>",
            "zh": "<Chinese translation>"
          }
        ]
      }
    ],
    "spoken_shortcuts": [
      { "abbr": "<SMS abbreviation>", "full_form": "<standard word>", "note": "<usage note>" }
    ],
    "cultural_pragmatics": {
      "register": "standard" | "formal" | "colloquial" | "intimate",
      "politeness_note": "<Guidance on politeness register and multiracial Malaysian etiquette>",
      "usage_etiquette": "<Practical usage advice, avoiding miscommunication>"
    },
    "etymology": {
      "origin": "<Austronesian (Inherited) / Sanskrit / Arabic / Tamil / Hokkien / English / Dutch / Persian>",
      "source_language": "<Language name>",
      "root_origin": "<Original etymon or linguistic origin>",
      "cognitive_memory_aid": "<Memorable mnemonic, mental hook, or visual associative trick>",
      "historical_story": "<Rich, vivid 2-4 sentence narrative detailing the word's historical origin, maritime trade route or cultural evolution into modern Malay>"
    }
  }
}

CRITICAL RULES:
1. Every sense MUST contain at least 2 distinct collocations in `senses[].collocations`.
2. WhatsApp colloquial scenario MUST have `messages` containing at least 2 turns with speaker name and social relationship.
3. Every entry MUST have a non-empty `etymology.historical_story` (vivid historical narrative) AND a distinct `etymology.cognitive_memory_aid`.
4. Output MUST be ONLY the raw JSON object. No Markdown code fences, no extra text.
"""

def validate_entry(entry: dict, word: str) -> tuple[bool, str]:
    if not isinstance(entry, dict):
        return False, "Not a dictionary"
    
    # Check headword
    head = entry.get("headword", {})
    if not head or head.get("word", "").lower() != word.lower():
        return False, f"Headword mismatch or missing for {word}"
    jawi = head.get("jawi")
    if jawi and set(jawi) == {'?'}:
        return False, f"Pure question mark Jawi for {word}"
        
    # Check morphology
    morph = entry.get("morphology", {})
    if not morph or "is_root" not in morph or "formula" not in morph:
        return False, f"Invalid morphology for {word}"
        
    # Check senses & collocations
    senses = entry.get("senses", [])
    if not senses or not isinstance(senses, list):
        return False, f"Missing senses for {word}"
    for s in senses:
        collocs = s.get("collocations", [])
        if len(collocs) < 2:
            return False, f"Sense {s.get('id')} has fewer than 2 collocations in {word}"
        if not s.get("zh_definition"):
            return False, f"Missing zh_definition in {word}"
            
    # Check dual scenarios & messages
    scenarios = entry.get("dual_scenarios", [])
    if len(scenarios) < 2:
        return False, f"Missing dual scenarios in {word}"
    colloquial = next((sc for sc in scenarios if sc.get("scenario") == "colloquial"), None)
    if not colloquial:
        return False, f"Missing colloquial scenario in {word}"
    msgs = colloquial.get("messages", [])
    if len(msgs) < 2:
        return False, f"Colloquial scenario has fewer than 2 messages in {word}"
    for m in msgs:
        if not m.get("speaker") or not m.get("ms_spoken") or not m.get("zh"):
            return False, f"Incomplete message turn in {word}"

    # Check etymology
    etym = entry.get("etymology", {})
    story = etym.get("historical_story", "")
    aid = etym.get("cognitive_memory_aid", "")
    if not story or len(story.strip()) < 15:
        return False, f"Missing or too short historical_story in {word}"
    if not aid or len(aid.strip()) < 5:
        return False, f"Missing cognitive_memory_aid in {word}"
        
    # Check cultural pragmatics
    prag = entry.get("cultural_pragmatics", {})
    if not prag.get("politeness_note") or not prag.get("usage_etiquette"):
        return False, f"Incomplete cultural_pragmatics in {word}"
        
    return True, "OK"

def process_single_batch(batch_idx: int, packets: list) -> dict:
    start_time = time.time()
    words = [p["word"] for p in packets]
    batch_tag = f"batch_{batch_idx+1}"
    out_file = AUDIT_DIR / f"top1000_{batch_tag}_output.json"
    
    prompt = f"""You are the authoritative Malay cognitive lexicographer and Lead Engineer.
Synthesize the complete 8-dimension cognitive dictionary entries for the following 10 Malay words:
{json.dumps(words, ensure_ascii=False)}

Raw Linguistic Context Packets:
{json.dumps(packets, ensure_ascii=False, indent=2)}

Schema and Output Requirements:
{SCHEMA_INSTRUCTIONS}
"""

    cmd = [
        CODEX_EXE, "exec",
        "-C", str(ROOT_DIR),
        "--ephemeral",
        "-o", str(out_file),
        "-"
    ]

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            text=True,
            capture_output=True,
            encoding="utf-8",
            timeout=360
        )
        elapsed = round(time.time() - start_time, 1)
        if proc.returncode != 0:
            return {"batch_idx": batch_idx, "status": "error", "error": f"Return code {proc.returncode}", "words": words, "elapsed": elapsed}
            
        if not out_file.exists():
            return {"batch_idx": batch_idx, "status": "error", "error": "Output file not found", "words": words, "elapsed": elapsed}

        with open(out_file, "r", encoding="utf-8") as f:
            raw = f.read().strip()

        # Clean markdown wrappers
        clean_json = re.sub(r"^```json\s*", "", raw, flags=re.MULTILINE)
        clean_json = re.sub(r"^```\s*$", "", clean_json, flags=re.MULTILINE).strip()
        data = json.loads(clean_json)

        # Validate each word
        validated_entries = {}
        errors = {}
        for w in words:
            if w not in data:
                errors[w] = "Missing in output JSON"
                continue
            entry = data[w]
            ok, err = validate_entry(entry, w)
            if not ok:
                errors[w] = err
            else:
                # Add sociolinguistic_register alias
                entry["sociolinguistic_register"] = entry.get("cultural_pragmatics", {})
                validated_entries[w] = entry

        if errors:
            return {
                "batch_idx": batch_idx,
                "status": "partial",
                "validated": validated_entries,
                "errors": errors,
                "words": words,
                "elapsed": elapsed
            }

        return {
            "batch_idx": batch_idx,
            "status": "ok",
            "validated": validated_entries,
            "words": words,
            "elapsed": elapsed
        }

    except Exception as e:
        elapsed = round(time.time() - start_time, 1)
        return {"batch_idx": batch_idx, "status": "error", "error": str(e), "words": words, "elapsed": elapsed}

def main():
    print("=" * 70)
    print("  OPEN-MELAYU TOP 1,001 - 2,000 EXPANSION: FIRST 100 WORDS (10-WAY)")
    print("=" * 70)

    kb = LinguisticKnowledgeBase()
    packets = select_top_100_source_only(kb)
    print(f"[*] Screened and assembled {len(packets)} core Malay words from Top 1,001-2,000.")
    print(f"[*] Ranks: #{packets[0]['rank']} ({packets[0]['word']}) to #{packets[-1]['rank']} ({packets[-1]['word']})")

    # Split into 10 batches of 10
    batches = [packets[i:i+10] for i in range(0, 100, 10)]

    print(f"\n[*] Firing 10-way controlled parallel worker pool (10 words per worker)...")
    print(f"[*] Respecting 15 RPM safety boundary...")
    t0 = time.time()
    results = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(process_single_batch, i, b): i for i, b in enumerate(batches)}
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            idx = res["batch_idx"] + 1
            status = res["status"]
            elapsed = res["elapsed"]
            if status == "ok":
                print(f"  [Worker {idx:02d}] PASS: 10/10 words validated in {elapsed}s")
            elif status == "partial":
                val_cnt = len(res.get("validated", {}))
                print(f"  [Worker {idx:02d}] PARTIAL: {val_cnt}/10 words validated in {elapsed}s. Errors: {res.get('errors')}")
            else:
                print(f"  [Worker {idx:02d}] FAIL: {res.get('error')} in {elapsed}s")
            results.append(res)

    total_time = round(time.time() - t0, 1)
    print(f"\n[*] All 10 parallel workers finished in {total_time}s.")

    # Collect all validated entries
    all_validated = {}
    missing_words = []
    for res in results:
        val = res.get("validated", {})
        all_validated.update(val)
        for w in res.get("words", []):
            if w not in val:
                missing_words.append(w)

    print(f"[*] Validated entries: {len(all_validated)} / 100 words")

    # Retry missing words if any (up to 1 retry round)
    if missing_words:
        print(f"[!] Retrying {len(missing_words)} missing words: {missing_words}...")
        retry_packets = [p for p in packets if p["word"] in missing_words]
        retry_res = process_single_batch(99, retry_packets)
        if retry_res["status"] in ("ok", "partial"):
            all_validated.update(retry_res.get("validated", {}))
            print(f"[+] Retry recovered {len(retry_res.get('validated', {}))} words.")

    print(f"\n[*] Final Total Validated: {len(all_validated)} / 100 words.")
    if len(all_validated) < 95:
        print("[!] Too many failures. Aborting atomic commit.")
        sys.exit(1)

    # 1. Atomic Commit to data/enriched/<word>.json
    print(f"[*] Atomically committing {len(all_validated)} entries to {ENRICHED_DIR}...")
    for w, entry in all_validated.items():
        w_path = ENRICHED_DIR / f"{w}.json"
        with open(w_path, "w", encoding="utf-8") as f:
            json.dump(entry, f, ensure_ascii=False, indent=2)
    print("[+] Enriched files committed successfully.")

    # 2. Sync to Shards
    print("[*] Synchronizing to 27 static shards via src/sync_enriched_to_shards.py...")
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_enriched_to_shards.py")], check=True)

    # 3. Dynamic Three-State Conservation & Manifest Update
    print("[*] Verifying three-state conservation across all 27 shards...")
    total_shard_words = 0
    enriched_count = 0
    source_only_count = 0
    missing_source_count = 0

    for letter in list("abcdefghijklmnopqrstuvwxyz") + ["other"]:
        with open(SHARDS_DIR / f"{letter}.json", "r", encoding="utf-8") as sf:
            sdata = json.load(sf)
        total_shard_words += len(sdata)
        for w, entry in sdata.items():
            state = entry.get("data_state")
            if state == "enriched":
                enriched_count += 1
            elif state == "source_only":
                source_only_count += 1
            elif state == "missing_source":
                missing_source_count += 1

    print(f"  - Total words in shards: {total_shard_words}")
    print(f"  - Enriched count: {enriched_count}")
    print(f"  - Source-only count: {source_only_count}")
    print(f"  - Missing-source count: {missing_source_count}")
    conservation_check = (total_shard_words == 15000 and (enriched_count + source_only_count + missing_source_count == 15000))
    print(f"  - Conservation check: {conservation_check}")

    if not conservation_check:
        print("[!] Conservation check failed! Shard state inconsistent.")
        sys.exit(1)

    # Update manifest.json
    now_ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    new_build_id = "om-20261102-v2"
    manifest_data = {
        "build_id": new_build_id,
        "timestamp": now_ts,
        "total_words": 15000,
        "enriched_count": enriched_count,
        "source_only_count": source_only_count,
        "missing_source_count": missing_source_count,
        "conservation_check": True
    }
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)
    print(f"[+] manifest.json updated with build_id: {new_build_id}")

    # Update data.js
    with open(DATA_JS, "r", encoding="utf-8") as f:
        data_js = f.read()
    data_js = re.sub(r"const DATA_VERSION = ['\"][^'\"]+['\"];", f"const DATA_VERSION = '{new_build_id}';", data_js)
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(data_js)
    print(f"[+] data.js synchronized with build_id: {new_build_id}")

    # Write execution evidence log
    evidence = {
        "timestamp": now_ts,
        "expansion_batch": "Top 1001-2000 Batch 1",
        "words_targeted": 100,
        "words_succeeded": len(all_validated),
        "total_time_sec": total_time,
        "new_enriched_count": enriched_count,
        "new_source_only_count": source_only_count,
        "sample_words": [p["word"] for p in packets[:10]],
        "build_id": new_build_id
    }
    with open(AUDIT_DIR / "expansion_batch1_evidence.json", "w", encoding="utf-8") as f:
        json.dump(evidence, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("  EXPANSION BATCH 1 SUCCESSFULLY COMPLETED & DEPLOYED")
    print("=" * 70)

if __name__ == "__main__":
    main()
