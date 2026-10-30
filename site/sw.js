// 코어 지표 service worker — 온라인이면 항상 새로 받아 캐시 갱신, 오프라인이면 마지막으로 받은 페이지를 보여 준다.
const CACHE = 'core-app-v1';
const PRECACHE = ['./', './index.html', './manifest.json', './icon-192.png', './icon-512.png',
  'https://unpkg.com/lightweight-charts@4.2.0/dist/lightweight-charts.standalone.production.js'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.allSettled(PRECACHE.map(u => c.add(u)))).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(fetch(e.request).then(r => {
    if (r && (r.ok || r.type === 'opaque')) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); }
    return r;
  }).catch(() => caches.match(e.request, {ignoreSearch: true}).then(m => m ||
    (e.request.mode === 'navigate' ? caches.match('./index.html') : Response.error()))));
});
