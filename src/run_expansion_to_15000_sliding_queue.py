"""
Open-Melayu Master 15,000 Expansion Pipeline (Sliding Pull Queue Edition v3)
===========================================================================
Incorporates all peer-reviewed audit recommendations from Codex (2026-11-02):
  1. Quality Lock: Strictly enforce `gpt-6.1-sol / high` reasoning effort.
  2. Packaging: Retain efficient 4-word batches (economical prefix caching).
  3. Timeout: 420s (7 minutes) to eliminate premature timeouts.
  4. Continuous Pull Queue (Sliding Window):
     - Eliminates the 27% idle tail wasted on round barrier synchronization.
     - Maintains exactly 25 concurrent slots in flight continuously.
     - Immediately pulls the next batch when any worker completes.
  5. Nuanced Jawi Validation:
     - Follows RULES.md: If PRPM provides Jawi, output must have valid non-empty Jawi.
     - If PRPM has no Jawi (foreign loanword/single letter), null/None is permitted, but '????' is banned.
  6. Quarantine Isolation:
     - Stragglers get 1 retry in 2-word batches.
     - Persistent edge-case failures (>2 retries) are quarantined to prevent queue clogging.
  7. Atomic Milestone Publishing:
     - Automated shard sync, 15,000 conservation check, and Git commit every ~100 validated words.
"""

import os
import sys
import json
import time
import subprocess
import threading
import concurrent.futures
from pathlib import Path
from collections import deque

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
RAW_DIR = ROOT_DIR / "raw"
DATA_DIR = ROOT_DIR / "data"
ENRICHED_DIR = DATA_DIR / "enriched"
AUDIT_DIR = DATA_DIR / "audit"
SHARDS_DIR = ROOT_DIR / "app" / "static" / "data" / "shards"
MANIFEST_FILE = ROOT_DIR / "app" / "static" / "data" / "manifest.json"
DATA_JS = ROOT_DIR / "app" / "static" / "data.js"
CODEX_EXE = r"C:\Users\d\AppData\Local\OpenAI\Codex\bin\22cfb1d302613eae\codex.exe"

ENRICHED_DIR.mkdir(parents=True, exist_ok=True)
AUDIT_DIR.mkdir(parents=True, exist_ok=True)

class SlidingWindowRateLimiter:
    def __init__(self, max_per_minute: float = 36.0):
        self.max_per_minute = max_per_minute
        self.lock = threading.Lock()
        self.timestamps = []

    def acquire(self):
        with self.lock:
            now = time.time()
            self.timestamps = [t for t in self.timestamps if now - t < 60.0]
            if len(self.timestamps) >= self.max_per_minute:
                sleep_needed = 60.0 - (now - self.timestamps[0]) + 0.05
                if sleep_needed > 0:
                    time.sleep(sleep_needed)
                    now = time.time()
                    self.timestamps = [t for t in self.timestamps if now - t < 60.0]
            self.timestamps.append(now)

limiter = SlidingWindowRateLimiter(max_per_minute=36.0)

class LinguisticKnowledgeBase:
    def __init__(self):
        print("[*] Initializing ultra-fast in-memory linguistic resources for full 15,000 pool...")
        t0 = time.time()
        
        # 1. Reverse shortcuts
        self.reverse_shortcuts = {}
        with open(RAW_DIR / "malaya_colloquial_rules.json", "r", encoding="utf-8") as f:
            cdata = json.load(f)
            for short, full_w in cdata.get("shortcuts", {}).items():
                if full_w not in self.reverse_shortcuts:
                    self.reverse_shortcuts[full_w] = []
                self.reverse_shortcuts[full_w].append(short)

        # 2. Rootwords
        with open(RAW_DIR / "malay_rootwords.json", "r", encoding="utf-8") as f:
            self.rootwords = json.load(f)

        # 3. Kaikki
        self.kaikki = {}
        with open(RAW_DIR / "kaikki_malay.jsonl", "r", encoding="utf-8") as f:
            for line in f:
                item = json.loads(line)
                w = item.get("word")
                if w:
                    if w not in self.kaikki:
                        self.kaikki[w] = []
                    self.kaikki[w].append(item)
                    
        # 4. RAM index of all PRPM raw filenames
        self.prpm_file_map = {
            entry.name[:-5]: entry.path 
            for entry in os.scandir(DATA_DIR / "prpm_raw") 
            if entry.name.endswith(".json")
        }
        self.prpm_cache = {}
        print(f"[+] Knowledge base ready in {time.time() - t0:.2f}s ({len(self.prpm_file_map)} PRPM files indexed).")

    def get_prpm_data(self, word: str) -> dict:
        w = word.lower().strip()
        if w in self.prpm_cache:
            return self.prpm_cache[w]
        path = self.prpm_file_map.get(w)
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.prpm_cache[w] = d
                    return d
            except Exception:
                pass
        self.prpm_cache[w] = {}
        return {}

    def resolve_root(self, word: str) -> tuple[str, str | None]:
        w = word.lower().strip()
        r = self.rootwords.get(w)
        if not r or r == w:
            for suffix in ["kan", "i", "an", "nya", "ku", "mu", "lah", "kah"]:
                if w.endswith(suffix) and len(w) > len(suffix) + 2:
                    cand = w[:-len(suffix)]
                    if cand in self.prpm_file_map:
                        r = cand
                        break
            if not r or r == w:
                for prefix in ["meng", "mem", "men", "me", "ber", "ter", "per", "pe", "se"]:
                    if w.startswith(prefix) and len(prefix) + 2 < len(w):
                        cand = w[len(prefix):]
                        if cand in self.prpm_file_map:
                            r = cand
                            break
        if not r:
            r = w
            
        rd = self.get_prpm_data(r)
        root_jawi = rd.get("jawi")
        return r, root_jawi

    def assemble_word_packet(self, word: str, rank: int) -> dict:
        w = word.lower().strip()
        prpm = self.get_prpm_data(w)
        root, root_jawi = self.resolve_root(w)

        kaikki_entries = self.kaikki.get(w, [])
        ipas = []
        glosses = []
        for k in kaikki_entries:
            for s in k.get("sounds", []) or []:
                if s.get("ipa"):
                    ipas.append(s.get("ipa"))
            for sense in k.get("senses", []) or []:
                for g in sense.get("glosses", []) or []:
                    glosses.append(g)

        kd = prpm.get("kamus_dewan") or prpm.get("kamus_pelajar") or prpm.get("definisi_melayu") or ""
        if not kd and root != w:
            r_data = self.get_prpm_data(root)
            kd = r_data.get("kamus_dewan") or r_data.get("kamus_pelajar") or ""
            
        trimmed_kd = kd[:300] + ("..." if len(kd) > 300 else "")
        jawi_val = prpm.get("jawi") or root_jawi
        syl_val = prpm.get("syllables")

        return {
            "word": w,
            "rank": rank,
            "jawi": jawi_val,
            "syllables": syl_val,
            "core_dbp_definition": trimmed_kd,
            "resolved_root": {
                "root_word": root,
                "root_jawi": root_jawi,
                "is_root": (root == w)
            },
            "phonetics": {
                "ipa_candidates": ipas[:2],
                "gloss_hints": glosses[:3]
            }
        }

SCHEMA_PROMPT = """You are the Senior Computational Lexicographer for the Open-Melayu Trilingual Lexicon (Malay - Chinese - English).
Synthesize the complete, authoritative 8-dimension cognitive dictionary entry for each of the provided Malay words.

Return a single JSON object mapping each word to its complete 8-dimension entry:
{
  "<word>": {
    "headword": {
      "word": "<word>",
      "syllables": "<syllables from packet>",
      "ipa": "<IPA from packet or standard>",
      "jawi": "<Jawi from packet>",
      "frequency_rank": <rank>,
      "status": "official"
    },
    "morphology": {
      "is_root": true | false,
      "root_word": "<root_word from packet>",
      "affix": "<affix or null>",
      "affix_type": "prefix" | "suffix" | "circumfix" | "none",
      "formula": "<formula, e.g. meN- + kawal → mengawal or ∅ + balas → balas>",
      "pattern_note": "<concise phonological rule>",
      "word_family": [
        { "word": "<family word 1>", "affix": "<affix>", "gloss": "<Chinese brief meaning>" },
        { "word": "<family word 2>", "affix": "<affix>", "gloss": "<Chinese brief meaning>" }
      ],
      "root_jawi": "<root_jawi from packet or same as jawi>"
    },
    "senses": [
      {
        "id": 1,
        "pos": "verb" | "noun" | "adjective" | "adverb" | "preposition" | "conjunction" | "particle",
        "zh_definition": "<Precise Chinese definition>",
        "en_definition": "<Concise dictionary-grade English definition>",
        "ms_definition": "<Official Malay definition>",
        "nuances": "<Pragmatic notes and usage boundaries>",
        "collocations": [
          { "ms": "<High frequency collocation 1>", "zh": "<Chinese translation 1>", "en": "<English translation 1>" },
          { "ms": "<High frequency collocation 2>", "zh": "<Chinese translation 2>", "en": "<English translation 2>" }
        ]
      }
    ],
    "dual_scenarios": [
      {
        "scenario": "formal",
        "context": "公文 / 新闻 / 职场汇报",
        "ms": "<Authentic standard Malaysian Malay sentence>",
        "zh": "<Chinese translation>",
        "en": "<English translation>"
      },
      {
        "scenario": "colloquial",
        "context": "WhatsApp / 日常口语交流",
        "ms_spoken": "<Spoken sentence with authentic particles>",
        "ms_standard": "<Standard equivalent sentence>",
        "zh": "<Colloquial Chinese translation>",
        "en": "<English translation>",
        "spoken_features": ["<feature 1>"],
        "messages": [
          {
            "speaker": "Name (关系, e.g. Farah (朋友))",
            "ms_spoken": "<First turn spoken Malay with particles dah/kat/nak/je>",
            "ms_standard": "<Standard Malay equivalent>",
            "zh": "<Chinese translation>",
            "en": "<Natural, idiomatic conversational English translation>"
          },
          {
            "speaker": "Name (关系, e.g. Amir (同事))",
            "ms_spoken": "<Second turn reply in spoken Malay>",
            "ms_standard": "<Standard Malay equivalent>",
            "zh": "<Chinese translation>",
            "en": "<Natural, idiomatic conversational English translation>"
          }
        ]
      }
    ],
    "etymology": {
      "historical_story": "<Fascinating 40-80 word historical or cultural narrative on word origins>",
      "cognitive_memory_aid": "<Punchy cognitive mnemonic connecting pronunciation to meaning>"
    },
    "cultural_pragmatics": {
      "politeness_note": "<Crucial Malaysian etiquette note on register and respect>",
      "usage_etiquette": "<Taboo boundaries or social contexts where this word fits>"
    }
  }
}

Quality Rules:
1. Every collocation must have: `ms`, `zh`, and `en`.
2. Both `zh_definition` AND `en_definition` AND `ms_definition` are mandatory and non-empty.
3. WhatsApp colloquial scenario MUST have `messages` containing at least 2 turns with speaker name, `ms_spoken`, `ms_standard`, `zh`, AND `en`.
4. Output MUST be ONLY the raw JSON object. No markdown code fences, no extra text.
"""

def validate_trilingual_entry(entry: dict, packet: dict, word: str) -> tuple[bool, str]:
    if not isinstance(entry, dict):
        return False, "Entry is not a dict"
    
    head = entry.get("headword", {})
    if not head.get("word") or head.get("word").lower() != word.lower():
        return False, f"Headword mismatch: {head.get('word')} != {word}"

    # Nuanced Jawi validation per RULES.md:
    raw_jawi = packet.get("jawi")
    jawi = head.get("jawi")
    if raw_jawi and str(raw_jawi).strip() and str(raw_jawi).strip().lower() not in ("null", "none"):
        # Source has authoritative Jawi: output must be valid string without '?'
        if not jawi or not isinstance(jawi, str) or "?" in jawi or jawi.strip().lower() in ("null", "none"):
            return False, f"Missing/invalid Jawi in {word} (source has '{raw_jawi}')"
    else:
        # Source has NO Jawi (e.g. English loanword, single letter): null/None permitted, '????' banned
        if isinstance(jawi, str) and "?" in jawi:
            return False, f"Invalid question mark placeholder Jawi in {word}: '{jawi}'"

    morph = entry.get("morphology", {})
    if "formula" not in morph or not morph.get("formula"):
        return False, f"Missing morphology formula in {word}"

    senses = entry.get("senses", [])
    if not senses or not isinstance(senses, list):
        return False, f"Missing senses for {word}"
        
    for s in senses:
        if not s.get("zh_definition") or len(s["zh_definition"].strip()) < 2:
            return False, f"Missing/short zh_definition in {word}"
        if not s.get("en_definition") or len(s["en_definition"].strip()) < 3:
            return False, f"Missing/short en_definition in {word}"
        if not s.get("ms_definition") or len(s["ms_definition"].strip()) < 3:
            return False, f"Missing/short ms_definition in {word}"

        collocs = s.get("collocations", [])
        if len(collocs) < 2:
            return False, f"Sense {s.get('id')} has <2 collocations in {word}"
        colloc_seen = set()
        for c in collocs:
            if not c.get("ms") or not c.get("zh") or not c.get("en"):
                return False, f"Collocation missing ms/zh/en in {word}"
            c_key = c["ms"].lower().strip()
            if c_key in colloc_seen:
                return False, f"Duplicate collocation '{c_key}' in {word}"
            colloc_seen.add(c_key)
            
    scenarios = entry.get("dual_scenarios", [])
    if len(scenarios) < 2:
        return False, f"Missing dual scenarios in {word}"
    formal = next((sc for sc in scenarios if sc.get("scenario") == "formal"), None)
    if not formal or not formal.get("ms") or not formal.get("zh") or not formal.get("en"):
        return False, f"Incomplete formal scenario in {word}"

    colloquial = next((sc for sc in scenarios if sc.get("scenario") == "colloquial"), None)
    if not colloquial:
        return False, f"Missing colloquial scenario in {word}"
    msgs = colloquial.get("messages", [])
    if len(msgs) < 2:
        return False, f"Colloquial scenario has <2 messages in {word}"
    for m in msgs:
        if not m.get("speaker") or not m.get("ms_spoken") or not m.get("ms_standard") or not m.get("zh") or not m.get("en"):
            return False, f"Incomplete message turn in {word}"

    etym = entry.get("etymology", {})
    story = etym.get("historical_story", "")
    aid = etym.get("cognitive_memory_aid", "")
    if not story or len(story.strip()) < 15:
        return False, f"Missing/short historical_story in {word}"
    if not aid or len(aid.strip()) < 5:
        return False, f"Missing cognitive_memory_aid in {word}"
        
    prag = entry.get("cultural_pragmatics", {})
    if not prag.get("politeness_note") or not prag.get("usage_etiquette"):
        return False, f"Incomplete cultural_pragmatics in {word}"
        
    return True, "OK"

def process_micro_batch(batch_tag: str, packets: list) -> dict:
    start_time = time.time()
    words = [p["word"] for p in packets]
    packet_map = {p["word"]: p for p in packets}
    out_file = AUDIT_DIR / f"full15k_{batch_tag}_output.json"
    
    prompt = f"""{SCHEMA_PROMPT}

Words to synthesize ({len(words)} words):
{json.dumps(words, ensure_ascii=False)}

Input Ground Truth Packets:
{json.dumps(packets, ensure_ascii=False, indent=2)}
"""

    limiter.acquire()
    cmd = [
        CODEX_EXE, "exec",
        "-C", str(ROOT_DIR),
        "-c", 'model="gpt-6.1-sol"',
        "-c", 'model_reasoning_effort="high"',
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
            timeout=420  # 420 seconds timeout to eliminate right-censored aborts
        )
        elapsed = round(time.time() - start_time, 1)
        if proc.returncode != 0:
            return {"batch_tag": batch_tag, "status": "error", "error": f"Code {proc.returncode}", "words": words, "packets": packets, "elapsed": elapsed}
            
        if not out_file.exists():
            return {"batch_tag": batch_tag, "status": "error", "error": "Output missing", "words": words, "packets": packets, "elapsed": elapsed}

        with open(out_file, "r", encoding="utf-8") as f:
            raw = f.read().strip()
            
        if "```" in raw:
            lines = raw.splitlines()
            clean = []
            in_fence = False
            for l in lines:
                if l.strip().startswith("```"):
                    in_fence = not in_fence
                    continue
                clean.append(l)
            raw = "\n".join(clean).strip()

        data = json.loads(raw)
        validated_entries = {}
        errors = {}
        for w in words:
            if w not in data:
                errors[w] = "Missing in output JSON"
                continue
            entry = data[w]
            pkt = packet_map[w]
            ok, err = validate_trilingual_entry(entry, pkt, w)
            if not ok:
                errors[w] = err
            else:
                entry["sociolinguistic_register"] = entry.get("cultural_pragmatics", {})
                validated_entries[w] = entry

        status = "ok" if not errors else ("partial" if validated_entries else "error")
        return {
            "batch_tag": batch_tag,
            "status": status,
            "validated": validated_entries,
            "errors": errors,
            "words": words,
            "packets": packets,
            "elapsed": elapsed
        }

    except subprocess.TimeoutExpired:
        return {"batch_tag": batch_tag, "status": "timeout", "words": words, "packets": packets, "elapsed": round(time.time() - start_time, 1)}
    except Exception as e:
        return {"batch_tag": batch_tag, "status": "exception", "error": str(e), "words": words, "packets": packets, "elapsed": round(time.time() - start_time, 1)}

def update_shards_and_manifest():
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_enriched_to_shards.py")], check=True, capture_output=True)
    subprocess.run(["python", str(ROOT_DIR / "src" / "sync_search_index.py")], check=True, capture_output=True)
    
    total_shard_words = 0
    enriched_count = 0
    source_only_count = 0
    missing_source_count = 0

    for s_file in SHARDS_DIR.glob("*.json"):
        with open(s_file, "r", encoding="utf-8") as f:
            sdata = json.load(f)
        total_shard_words += len(sdata)
        for w, entry in sdata.items():
            state = entry.get("data_state")
            if state == "enriched":
                enriched_count += 1
            elif state == "source_only":
                source_only_count += 1
            elif state == "missing_source":
                missing_source_count += 1

    conservation_check = (total_shard_words == 15000 and (enriched_count + source_only_count + missing_source_count == 15000))
    if not conservation_check:
        raise ValueError(f"Conservation broken! Shards: {total_shard_words}, E:{enriched_count}, S:{source_only_count}, M:{missing_source_count}")

    new_build_id = f"om-{time.strftime('%Y%m%d')}-v{int(time.time()) % 10000}"
    manifest_data = {
        "build_id": new_build_id,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "total_words": 15000,
        "enriched_count": enriched_count,
        "source_only_count": source_only_count,
        "missing_source_count": missing_source_count,
        "conservation_check": conservation_check,
        "format_version": 2
    }

    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, ensure_ascii=False, indent=2)

    with open(DATA_JS, "r", encoding="utf-8") as f:
        js_content = f.read()
    import re
    js_content = re.sub(r'export const DATA_VERSION = [\'"][^\'"]+[\'"];', f"export const DATA_VERSION = '{new_build_id}';", js_content)
    with open(DATA_JS, "w", encoding="utf-8") as f:
        f.write(js_content)

    # Automated milestone Git commit
    try:
        subprocess.run(["git", "-C", str(ROOT_DIR), "add", "app/static/", "data/enriched/", "data/audit/grand_expansion_progress.json", "START.md", "docs/"], check=False)
        subprocess.run(["git", "-C", str(ROOT_DIR), "commit", "-m", f"feat(lexicon): milestone {enriched_count} words trilingual build {new_build_id}"], check=False)
    except Exception as ge:
        print(f"[!] Git commit notice: {ge}")

    return enriched_count, source_only_count, missing_source_count, new_build_id

def get_all_remaining_candidates(kb: LinguisticKnowledgeBase, quarantined: set) -> list[dict]:
    with open(DATA_DIR / "candidate_pool_15k.json", "r", encoding="utf-8") as f:
        pool = json.load(f)

    valid_candidates = []
    for item in pool:
        w = item["word"].lower().strip()
        if w in quarantined:
            continue
        if (ENRICHED_DIR / f"{w}.json").exists():
            continue
            
        pdata = kb.get_prpm_data(w)
        kd = pdata.get("kamus_dewan") or pdata.get("kamus_pelajar") or pdata.get("definisi_melayu")
        
        root, root_jawi = kb.resolve_root(w)
        root_kd = None
        if root != w:
            r_data = kb.get_prpm_data(root)
            root_kd = r_data.get("kamus_dewan") or r_data.get("kamus_pelajar")
            
        if kd or root_kd:
            valid_candidates.append(kb.assemble_word_packet(w, item["rank"]))

    return valid_candidates

def run_continuous_sliding_expansion():
    kb = LinguisticKnowledgeBase()
    
    MAX_CONCURRENT_SLOTS = 25
    MICRO_BATCH_SIZE = 4
    MILESTONE_INTERVAL = 100
    SESSION_ID = int(time.time()) % 10000
    
    quarantine_path = AUDIT_DIR / "quarantine_words.json"
    quarantined = set()
    if quarantine_path.exists():
        try:
            with open(quarantine_path, "r", encoding="utf-8") as f:
                q_data = json.load(f)
                quarantined = set(q_data.keys())
        except Exception:
            pass

    print(f"\n[★] CONTINUOUS SLIDING PULL QUEUE LAUNCHED (25 SLOTS, 420s TIMEOUT, HIGH QUALITY)!")
    print(f"[*] Quarantined words at startup: {len(quarantined)}")
    
    # In-memory tracking
    in_flight_words = set()
    retry_packet_queue = deque() # Holds lists of packets needing retry (size 2 or 4)
    word_attempt_count = {}      # w -> int
    batch_counter = 0
    words_since_last_milestone = 0
    total_validated_session = 0
    session_start_time = time.time()
    sync_lock = threading.Lock()

    # Pre-fetch candidate pool
    initial_candidates = get_all_remaining_candidates(kb, quarantined)
    candidate_queue = deque(initial_candidates)
    print(f"[*] Initial pending candidate pool: {len(candidate_queue)} words.")

    def get_next_batch() -> tuple[str, list[dict]] | None:
        nonlocal batch_counter
        # Priority 1: Straggler retry queue
        if retry_packet_queue:
            batch_counter += 1
            pkts = retry_packet_queue.popleft()
            tag = f"s{SESSION_ID:04d}_retry_{batch_counter:05d}"
            for p in pkts:
                in_flight_words.add(p["word"])
            return tag, pkts

        # Priority 2: Fresh candidates
        batch_pkts = []
        while candidate_queue and len(batch_pkts) < MICRO_BATCH_SIZE:
            pkt = candidate_queue.popleft()
            w = pkt["word"]
            if (ENRICHED_DIR / f"{w}.json").exists() or w in in_flight_words or w in quarantined:
                continue
            batch_pkts.append(pkt)
            in_flight_words.add(w)

        if batch_pkts:
            batch_counter += 1
            tag = f"s{SESSION_ID:04d}_p_{batch_counter:05d}"
            return tag, batch_pkts

        # If candidate queue is exhausted, check if any un-enriched remain in candidate_pool_15k
        # that weren't in memory
        fresh_check = get_all_remaining_candidates(kb, quarantined)
        for fc in fresh_check:
            if fc["word"] not in in_flight_words:
                candidate_queue.append(fc)

        if candidate_queue:
            batch_pkts = []
            while candidate_queue and len(batch_pkts) < MICRO_BATCH_SIZE:
                pkt = candidate_queue.popleft()
                w = pkt["word"]
                if (ENRICHED_DIR / f"{w}.json").exists() or w in in_flight_words or w in quarantined:
                    continue
                batch_pkts.append(pkt)
                in_flight_words.add(w)
            if batch_pkts:
                batch_counter += 1
                tag = f"s{SESSION_ID:04d}_p_{batch_counter:05d}"
                return tag, batch_pkts

        return None

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_SLOTS) as executor:
        futures = {}

        # 1. Seed initial 25 slots
        while len(futures) < MAX_CONCURRENT_SLOTS:
            task = get_next_batch()
            if not task:
                break
            tag, pkts = task
            fut = executor.submit(process_micro_batch, tag, pkts)
            futures[fut] = (tag, pkts)

        print(f"[+] Initialized {len(futures)} concurrent slots in-flight. Starting continuous sliding pull loop...\n")

        while futures:
            # Wait for the next slot to finish
            done, _ = concurrent.futures.wait(futures, return_when=concurrent.futures.FIRST_COMPLETED)

            for fut in done:
                tag, pkts = futures.pop(fut)
                words = [p["word"] for p in pkts]
                for w in words:
                    in_flight_words.discard(w)

                res = fut.result()
                status = res.get("status", "error")
                elapsed = res.get("elapsed", 0)
                validated = res.get("validated", {})
                errors = res.get("errors", {})

                # Commit validated entries to disk
                if validated:
                    for w, entry in validated.items():
                        w_path = ENRICHED_DIR / f"{w}.json"
                        with open(w_path, "w", encoding="utf-8") as f:
                            json.dump(entry, f, ensure_ascii=False, indent=2)

                    total_validated_session += len(validated)
                    words_since_last_milestone += len(validated)

                # Handle failed words (Retry or Quarantine)
                stragglers_to_retry = []
                for p in pkts:
                    w = p["word"]
                    if w in validated:
                        continue
                    word_attempt_count[w] = word_attempt_count.get(w, 0) + 1
                    err_msg = errors.get(w, res.get("error", status))

                    if word_attempt_count[w] < 3: # Allow up to 2 attempts
                        stragglers_to_retry.append(p)
                    else:
                        print(f"      [!] Quarantining persistently failing word '{w}': {err_msg}")
                        quarantined.add(w)
                        # Save quarantine file
                        try:
                            q_dict = {}
                            if quarantine_path.exists():
                                with open(quarantine_path, "r", encoding="utf-8") as qf:
                                    q_dict = json.load(qf)
                            q_dict[w] = {
                                "error": err_msg,
                                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00")
                            }
                            with open(quarantine_path, "w", encoding="utf-8") as qf:
                                json.dump(q_dict, qf, ensure_ascii=False, indent=2)
                        except Exception as qe:
                            print(f"[!] Quarantine log err: {qe}")

                if stragglers_to_retry:
                    # Enqueue in 2-word packets
                    for i in range(0, len(stragglers_to_retry), 2):
                        retry_packet_queue.append(stragglers_to_retry[i:i + 2])

                # Clean log line
                val_cnt = len(validated)
                total_cnt = len(words)
                curr_enriched = len(list(ENRICHED_DIR.glob("*.json")))
                session_elapsed = time.time() - session_start_time
                wpm = round(total_validated_session / (session_elapsed / 60.0), 1) if session_elapsed > 0 else 0

                print(f"  [SLOT] Batch {tag}: {val_cnt}/{total_cnt} valid in {elapsed}s ({status}) | In-Flight: {len(futures)} | Buffer: {words_since_last_milestone}/{MILESTONE_INTERVAL} | Total Enriched: {curr_enriched} ({wpm} wpm)")

                # Milestone commit check
                if words_since_last_milestone >= MILESTONE_INTERVAL:
                    with sync_lock:
                        print(f"\n[*] Milestone reached! Synchronizing shards, search index & Git commit...")
                        try:
                            e_cnt, s_cnt, m_cnt, b_id = update_shards_and_manifest()
                            print(f"[+] MILESTONE COMMITTED: Build {b_id} | Enriched: {e_cnt} | Conservation OK\n")
                            words_since_last_milestone = 0
                        except Exception as se:
                            print(f"[!] Milestone sync error: {se}\n")

                # REFILL SLOT IMMEDIATELY! Keep 25 slots continuously saturated!
                while len(futures) < MAX_CONCURRENT_SLOTS:
                    next_task = get_next_batch()
                    if not next_task:
                        break
                    n_tag, n_pkts = next_task
                    n_fut = executor.submit(process_micro_batch, n_tag, n_pkts)
                    futures[n_fut] = (n_tag, n_pkts)

    # Final wrap-up sync
    print(f"\n[★★★] ALL CANDIDATES PROCESSED! Performing final atomic sync and commit...")
    with sync_lock:
        e_cnt, s_cnt, m_cnt, b_id = update_shards_and_manifest()
        print(f"[★★★] FINAL BUILD COMMITTED: {b_id} | Total Enriched: {e_cnt} words [★★★]")

if __name__ == "__main__":
    run_continuous_sliding_expansion()
