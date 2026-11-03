// Open-Melayu Data Specification & Cache Version
export const DATA_VERSION = 'om-20261103-v9756';
export const INDEX_CACHE = `open-melayu-index-${DATA_VERSION}`;
export const SHELL_CACHE = 'open-melayu-shell-v5';

export function normalizeWord(word) {
  return String(word ?? '').trim().toLowerCase();
}

export function shardFor(word) {
  const norm = normalizeWord(word);
  const first = norm.charAt(0);
  return /^[a-z]$/.test(first) ? first : 'other';
}

export const shardKeyForWord = shardFor;
export const SHARD_KEYS = [...'abcdefghijklmnopqrstuvwxyz', 'other'];

// Cache only validated indexes; a damaged cached response must be retryable.
export async function loadSearchIndex({ requireCache = false } = {}) {
  const url = new URL('./data/search_index.json', import.meta.url);
  let cache;
  try {
    cache = await caches.open(INDEX_CACHE);
    const cached = await cache.match(url);
    if (cached?.ok) {
      const data = await cached.json();
      if (Array.isArray(data)) return data;
    }
  } catch {
    // Browsing can continue without persistent storage.
  }
  if (requireCache && !cache) throw new Error('浏览器无法缓存搜索索引');
  const response = await fetch(url);
  if (!response.ok) throw new Error(`索引载入失败（HTTP ${response.status}）`);
  const data = await response.clone().json();
  if (!Array.isArray(data)) throw new Error('索引格式不合法');
  if (cache) {
    try {
      await cache.put(url, response);
      if (requireCache && !Array.isArray(await (await cache.match(url)).json())) throw new Error('搜索索引缓存无效');
    } catch (error) { if (requireCache) throw error; }
  }
  return data;
}
