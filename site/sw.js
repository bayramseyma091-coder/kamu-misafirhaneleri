// Çevrimdışı kullanım: sayfa ve veriler önce ağdan, ağ yoksa önbellekten gelir.
const ONBELLEK = "misafirhane-v1";
const TEMEL = ["./", "index.html", "iller.html", "degisiklikler.html", "stil.css", "uygulama.js", "sayfa.js",
  "misafirhaneler.geojson", "degisiklikler.json", "simge.svg", "simge-192.png"];
const CDN = /cdnjs\.cloudflare\.com|fonts\.(googleapis|gstatic)\.com/;

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(ONBELLEK).then((c) => c.addAll(TEMEL)).then(() => self.skipWaiting()));
});
self.addEventListener("activate", (e) => {
  e.waitUntil(caches.keys().then((k) => Promise.all(k.filter((a) => a !== ONBELLEK).map((a) => caches.delete(a))))
    .then(() => self.clients.claim()));
});
self.addEventListener("fetch", (e) => {
  const istek = e.request;
  if (istek.method !== "GET") return;
  const url = new URL(istek.url);
  if (CDN.test(url.hostname)) {
    // Kütüphaneler ve yazı tipleri değişmez: önce önbellek
    e.respondWith(caches.match(istek).then((y) => y || fetch(istek).then((r) => {
      const kopya = r.clone();
      caches.open(ONBELLEK).then((c) => c.put(istek, kopya));
      return r;
    })));
    return;
  }
  if (url.origin !== location.origin) return; // harita karoları vb. tarayıcıya bırakılır
  e.respondWith(fetch(istek).then((r) => {
    if (r.ok) {
      const kopya = r.clone();
      caches.open(ONBELLEK).then((c) => c.put(istek, kopya));
    }
    return r;
  }).catch(() => caches.match(istek, { ignoreSearch: true })
    .then((y) => y || (istek.mode === "navigate" ? caches.match("index.html") : Response.error()))));
});
