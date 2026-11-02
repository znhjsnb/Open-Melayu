// Open-Melayu Data Specification & Cache Version
export const DATA_VERSION = 'om-20261102-v493';
export const INDEX_CACHE = `open-melayu-index-${DATA_VERSION}`;
export const SHELL_CACHE = `open-melayu-shell-${DATA_VERSION}`;

export function normalizeWord(word) {
  return String(word ?? '').trim().toLowerCase();
}

export function shardFor(word) {
  const norm = normalizeWord(word);
  const first = norm.charAt(0);
  return /^[a-z]$/.test(first) ? first : 'other';
}
