<<<<<<< HEAD
const CACHE_VERSION = "v3";
const STATIC_CACHE = `bless-static-${CACHE_VERSION}`;

const STATIC_ASSETS = [
=======
const CACHE_NAME = "bless-v1";
const ASSETS = [
  "/",
  "/dashboard",
  "/login",
>>>>>>> 6b4abd0 (Fix static paths for PWA)
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
<<<<<<< HEAD
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS)).catch(() => {})
=======
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).catch(() => {})
>>>>>>> 6b4abd0 (Fix static paths for PWA)
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
<<<<<<< HEAD
      Promise.all(keys.map((k) => (k !== STATIC_CACHE ? caches.delete(k) : null)))
=======
      Promise.all(keys.map((k) => (k !== CACHE_NAME ? caches.delete(k) : null)))
>>>>>>> 6b4abd0 (Fix static paths for PWA)
    )
  );
  self.clients.claim();
});

<<<<<<< HEAD
// NO cachear POST/PUT. Solo GET.
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

=======
self.addEventListener("fetch", (event) => {
>>>>>>> 6b4abd0 (Fix static paths for PWA)
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
