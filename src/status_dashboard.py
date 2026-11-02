"""
Open-Melayu: Real-time Status Dashboard
Reads live progress from Track 1 (Crawler) and Track 2 (Enriched Dictionaries)
Outputs a clean, human-readable terminal summary.
"""
import os
import sys
import json
import time

sys.stdout.reconfigure(encoding='utf-8')

ROOT_DIR = r"c:\Users\d\Documents\open-melayu"
CACHE_DIR = os.path.join(ROOT_DIR, "raw", "prpm_cache")
ENRICHED_DIR = os.path.join(ROOT_DIR, "data", "enriched")
PROGRESS_FILE = os.path.join(ROOT_DIR, "data", "crawler_progress.json")
PILOT_FILE = os.path.join(ROOT_DIR, "data", "pilot_50_candidates.json")

def get_status():
    # 1. Track 1 Crawler Status
    crawler_status = {}
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            crawler_status = json.load(f)
            
    cache_count = len(os.listdir(CACHE_DIR)) if os.path.exists(CACHE_DIR) else 0

    # 2. Track 2 Enriched Status
    enriched_files = [f for f in os.listdir(ENRICHED_DIR) if f.endswith('.json') and not f.startswith('batch_')] if os.path.exists(ENRICHED_DIR) else []
    batch_files = [f for f in os.listdir(ENRICHED_DIR) if f.startswith('batch_')] if os.path.exists(ENRICHED_DIR) else []

    # 3. Pilot Status
    pilot_words = []
    if os.path.exists(PILOT_FILE):
        with open(PILOT_FILE, 'r', encoding='utf-8') as f:
            pilot_words = [x['word'] for x in json.load(f)]
            
    pilot_done = [w for w in pilot_words if f"{w}.json" in enriched_files]

    return {
        "crawler": {
            "cached_total": cache_count,
            "current_index": crawler_status.get("current_index", 0),
            "total_candidates": crawler_status.get("total_candidates", 15000),
            "last_word": crawler_status.get("last_word", "-"),
            "last_found": crawler_status.get("last_found", False),
            "updated_at": crawler_status.get("updated_at", "-")
        },
        "synthesis": {
            "enriched_words_count": len(enriched_files),
            "batch_files_count": len(batch_files),
            "pilot_completed": f"{len(pilot_done)}/{len(pilot_words)}",
            "recent_words": enriched_files[-10:]
        }
    }

if __name__ == "__main__":
    st = get_status()
    print("=" * 60)
    print("        OPEN-MELAYU 双轨实时运行看板 (Dashboard)")
    print("=" * 60)
    print(f"[Track 1: DBP 官方爬虫] (持续后台常驻)")
    print(f"  • 官方 PRPM 缓存总量 : {st['crawler']['cached_total']} 词")
    print(f"  • 当前排查候选进度   : {st['crawler']['current_index']} / {st['crawler']['total_candidates']}")
    print(f"  • 最近爬取词汇       : '{st['crawler']['last_word']}' (官方命中: {st['crawler']['last_found']})")
    print(f"  • 最近心跳时间       : {st['crawler']['updated_at']}")
    print("-" * 60)
    print(f"[Track 2: Codex 7维生产] (已完成 Batch 1 & 2)")
    print(f"  • 独立完成词条数     : {st['synthesis']['enriched_words_count']} 词")
    print(f"  • Pilot 50 词先导进度: {st['synthesis']['pilot_completed']}")
    print(f"  • 已交付批次集合     : {st['synthesis']['batch_files_count']} 个主批次")
    print(f"  • 最近交付词条       : {st['synthesis']['recent_words'][:5]}...")
    print("=" * 60)
