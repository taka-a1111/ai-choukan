// AIトレンド朝刊 service worker ver1.0 — 常に最新を取りに行き、電波がないときだけ前回の内容を出す
const CACHE = "aichoukan-v1";
self.addEventListener("install", e => self.skipWaiting());
self.addEventListener("activate", e => e.waitUntil(
  caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim())
));
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== location.origin) return;
  e.respondWith(
    fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); const key = req.url.replace(/[?&]t=\d+/, ""); caches.open(CACHE).then(c => c.put(key, copy)); }
      return res;
    }).catch(() => caches.match(req.url.replace(/[?&]t=\d+/, "")))
  );
});
