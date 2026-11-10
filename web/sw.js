/* ============================================================
   EC-Cam — Service worker de la app instalable
   - No guarda páginas, video ni datos: todo se pide al servidor.
   - Nunca toca /stream/, /audio/, /api/ ni /recordings/ (video en vivo).
   - Solo guarda la página «Sin conexión» y su logo.
   Para publicar cambios en este archivo, sube VERSION.
   ============================================================ */
const VERSION = 'eccam-v2';
const OFFLINE = '/offline.html';
const PRECARGA = [OFFLINE, '/img/pwa-192.png'];

self.addEventListener('install', (e) => {
    e.waitUntil(caches.open(VERSION).then((c) => c.addAll(PRECARGA)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys()
            .then((ks) => Promise.all(ks.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', (e) => {
    const req = e.request;
    if (req.method !== 'GET') return;
    const url = new URL(req.url);
    if (url.origin !== location.origin) return;
    // Páginas: siempre del servidor; sin red, la página «Sin conexión»
    if (req.mode === 'navigate') {
        e.respondWith(fetch(req).catch(() => caches.match(OFFLINE)));
        return;
    }
    // Logo de la página «Sin conexión»
    if (url.pathname === '/img/pwa-192.png') {
        e.respondWith(fetch(req).catch(() => caches.match(req, { ignoreSearch: true })));
    }
});
