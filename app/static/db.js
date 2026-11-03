import { DATA_VERSION, SHARD_KEYS, shardFor, loadSearchIndex } from './data.js';

const memory = new Map();
const inflight = new Map();
let database;
export const cacheStatus = { persistent: true };

function openDatabase() {
  if (!database) {
    database = new Promise(resolve => {
      if (!globalThis.indexedDB) {
        cacheStatus.persistent = false;
        resolve(null);
        return;
      }
      let request;
      let unavailable = false;
      try {
        request = indexedDB.open('open-melayu-shards', 1);
      } catch {
        cacheStatus.persistent = false;
        resolve(null);
        return;
      }
      request.onupgradeneeded = () => {
        request.result.createObjectStore('shards');
      };
      request.onsuccess = () => {
        const db = request.result;
        if (unavailable) {
          db.close();
          return;
        }
        db.onversionchange = () => {
          db.close();
          database = null;
        };
        resolve(db);
      };
      request.onerror = request.onblocked = () => {
        unavailable = true;
        cacheStatus.persistent = false;
        resolve(null);
      };
    });
  }
  return database;
}

async function readShard(key) {
  const db = await openDatabase();
  if (!db) return null;
  return new Promise(resolve => {
    try {
      const request = db.transaction('shards').objectStore('shards').get(key);
      request.onsuccess = () => resolve(request.result ?? null);
      request.onerror = () => { cacheStatus.persistent = false; resolve(null); };
    } catch {
      cacheStatus.persistent = false;
      resolve(null);
    }
  });
}

async function writeShard(key, shard) {
  const db = await openDatabase();
  if (!db) return;
  await new Promise(resolve => {
    try {
      const transaction = db.transaction('shards', 'readwrite');
      transaction.objectStore('shards').put(shard, key);
      transaction.oncomplete = () => { cacheStatus.persistent = true; resolve(); };
      transaction.onerror = transaction.onabort = () => {
        cacheStatus.persistent = false;
        resolve();
      };
    } catch {
      cacheStatus.persistent = false;
      resolve();
    }
  });
}

// Memory LRU - keep at most 5 shards in RAM (Condition C08)
function remember(letter, shard) {
  memory.delete(letter);
  memory.set(letter, shard);
  if (memory.size > 5) {
    memory.delete(memory.keys().next().value);
  }
}

async function fetchShard(letter) {
  if (!SHARD_KEYS.includes(letter)) throw new Error('无效分片');
  const key = `${DATA_VERSION}:${letter}`;
  
  // 1. Check memory
  if (memory.has(letter)) {
    const shard = memory.get(letter);
    remember(letter, shard);
    return { shard, source: 'memory' };
  }
  
  // 2. Check IndexedDB
  const cached = await readShard(key);
  if (cached) {
    remember(letter, cached);
    return { shard: cached, source: 'indexeddb' };
  }
  
  // 3. Network fetch
  let response;
  try {
    response = await fetch(new URL(`./data/shards/${letter}.json`, import.meta.url));
  } catch {
    throw new Error('词条分片无法读取，请检查服务连接');
  }
  if (!response.ok) {
    throw new Error(`分片暂未生成或不存在（HTTP ${response.status}）`);
  }
  const shard = await response.json().catch(() => {
    throw new Error('分片数据解析失败');
  });
  if (!shard || typeof shard !== 'object' || Array.isArray(shard)) {
    throw new Error('分片数据结构不合法');
  }
  
  remember(letter, shard);
  await writeShard(key, shard);
  return { shard, source: 'network' };
}

export function loadShard(letter) {
  if (!inflight.has(letter)) {
    inflight.set(letter, fetchShard(letter).finally(() => inflight.delete(letter)));
  }
  return inflight.get(letter);
}

export const ensureShard = loadShard;

// Offline readiness is established from durable storage, never from the RAM LRU.
export async function prepareOffline(onProgress = () => {}, shouldPause = () => false) {
  const db = await openDatabase();
  if (!db) throw new Error('浏览器无法持久保存离线词库');
  await loadSearchIndex({ requireCache: true });
  let completed = 0;
  for (const letter of SHARD_KEYS) {
    if (shouldPause()) return { paused: true, completed, total: SHARD_KEYS.length };
    const key = `${DATA_VERSION}:${letter}`;
    if (!await readShard(key)) {
      const { shard, source } = await loadShard(letter);
      // A shard may already be in memory after an earlier failed storage write.
      if (source === 'memory') await writeShard(key, shard);
    }
    if (!await readShard(key)) throw new Error(`分片 ${letter} 无法持久保存，请检查存储空间`);
    onProgress({ completed: ++completed, total: SHARD_KEYS.length, letter });
  }
  cacheStatus.persistent = true;
  return { paused: false, completed, total: SHARD_KEYS.length };
}

export async function getWordDetail(word) {
  const letter = shardFor(word);
  const { shard } = await ensureShard(letter);
  const lower = String(word).trim().toLowerCase();
  return shard[lower] || null;
}
