"""
Sync enriched words into search_index.json
Ensures search_index.json reflects all 1,841 enriched words with e=1, st='e', accurate jawi, ipa, and definitions.
Preserves total count 15,000 and exact structure.
"""

import os
import sys
import json
import glob
from pathlib import Path

ROOT_DIR = Path(r"C:\Users\d\Documents\open-melayu")
INDEX_PATH = ROOT_DIR / "app" / "static" / "data" / "search_index.json"
ENRICHED_DIR = ROOT_DIR / "data" / "enriched"

if hasattr(sys.stdout, "reconfigure") and sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")

def sync_search_index():
    print(f"[*] Loading search index from {INDEX_PATH}...")
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        search_index = json.load(f)
    
    assert len(search_index) == 15000, f"Expected 15,000 items, got {len(search_index)}"
    
    # Map index by word
    index_by_word = {item["w"]: item for item in search_index}
    
    # Load all enriched words
    enriched_files = sorted(ENRICHED_DIR.glob("*.json"))
    word_files = [f for f in enriched_files if not f.name.startswith("batch_")]
    print(f"[*] Loaded {len(word_files)} enriched word files from {ENRICHED_DIR}...")
    
    updated_count = 0
    total_enriched_marked = 0
    
    for wf in word_files:
        w = wf.stem.lower()
        with open(wf, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if w in index_by_word:
            item = index_by_word[w]
            hw = data.get("headword", {})
            morph = data.get("morphology", {})
            senses = data.get("senses", [])
            
            # Senses definitions list
            zh_defs = [s.get("zh_definition", "") for s in senses if s.get("zh_definition")]
            if not zh_defs:
                zh_defs = ["（未提取到分条释义文本）"]
            
            # Update fields
            item["j"] = hw.get("jawi") or ""
            item["p"] = hw.get("ipa") or ""
            item["r"] = morph.get("root") or hw.get("word") or ""
            item["s"] = zh_defs[:4]
            if item.get("e") != 1 or item.get("st") != "e":
                updated_count += 1
            item["e"] = 1
            item["st"] = "e"
            total_enriched_marked += 1
        else:
            print(f"[!] Warning: enriched word {w} not found in search_index.json!")
    
    print(f"[+] Total enriched marked in index: {total_enriched_marked} (Newly updated: {updated_count})")
    assert total_enriched_marked == len(word_files), f"Expected {len(word_files)}, got {total_enriched_marked}"
    
    # Save back atomically
    tmp_path = INDEX_PATH.with_suffix(".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(search_index, f, ensure_ascii=False, separators=(',', ':'))
    
    if INDEX_PATH.exists():
        INDEX_PATH.unlink()
    tmp_path.rename(INDEX_PATH)
    
    print(f"[+] Search index updated and saved atomically: {INDEX_PATH.stat().st_size} bytes")

if __name__ == "__main__":
    sync_search_index()
