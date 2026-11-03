import { SHELL_CACHE } from './data.js';

// Shell revision: 5. Network-first updates with current-shell offline fallback.

const SHELL = [
  './',
  './index.html',
  './styles.css',
  './app.js',
  './db.js',
  './data.js',
  './worker.js',
  './entry-format.js'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then(cache => cache.addAll(SHELL))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k.startsWith('open-melayu-shell-') && k !== SHELL_CACHE)
            .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

  // Data has its own storage layer; API responses do not belong in the shell.
  if (url.pathname.includes('/data/') || url.pathname.startsWith('/api/')) return;

  const known = SHELL.some(path => new URL(path, self.registration.scope).pathname === url.pathname);
  if (!known && event.request.mode !== 'navigate') return;

  const network = fetch(event.request);
  // Cache writes must survive the response, but storage failures must not hide it.
  event.waitUntil(network.then(async response => {
    if (response.ok && response.type === 'basic') {
      const copy = response.clone();
      const cache = await caches.open(SHELL_CACHE);
      await cache.put(event.request, copy);
    }
  }).catch(() => {}));

  event.respondWith(
    network.catch(async () => {
      try {
        const cache = await caches.open(SHELL_CACHE);
        const cached = await cache.match(event.request);
        if (cached) return cached;
        if (event.request.mode === 'navigate') {
          const page = await cache.match(new URL('./index.html', self.registration.scope));
          if (page) return page;
        }
      } catch {
        // Storage can be unavailable in private mode or under quota pressure.
      }
      return Response.error();
    })
  );
});
