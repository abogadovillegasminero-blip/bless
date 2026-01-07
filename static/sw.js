/* static/sw.js */
const CACHE_VERSION = "v2";
const STATIC_CACHE = `bless-static-${CACHE_VERSION}`;
const RUNTIME_CACHE = `bless-runtime-${CACHE_VERSION}`;

// Solo precachea cosas 100% estáticas
const STATIC_ASSETS = [
  "/static/manifest.json",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
];

// Instalación: guardar estáticos
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

// Activación: limpiar caches viejos
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((k) => {
          if (![STATIC_CACHE, RUNTIME_CACHE].includes(k)) return caches.delete(k);
          return null;
        })
      )
    )
  );
  self.clients.claim();
});

// Fetch: NO cachear POST/PUT/etc, solo GET
self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const url = new URL(event.request.url);

  // Solo manejar mismo dominio
  if (url.origin !== self.location.origin) return;

  // 1) Archivos estáticos: cache-first
  if (
    url.pathname.startsWith("/static/") ||
    url.pathname.endsWith(".css") ||
    url.pathname.endsWith(".js") ||
    url.pathname.endsWith(".png") ||
    url.pathname.endsWith(".jpg") ||
    url.pathname.endsWith(".jpeg") ||
    url.pathname.endsWith(".svg") ||
    url.pathname.endsWith(".ico") ||
    url.pathname.endsWith(".woff") ||
    url.pathname.endsWith(".woff2")
  ) {
    event.respondWith(cacheFirst(event.request));
    return;
  }

  // 2) Navegación (HTML): network-first (evita “sesión vieja”)
  if (event.request.mode === "navigate") {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // 3) Lo demás: network-first suave
  event.respondWith(networkFirst(event.request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  const res = await fetch(request);
  const cache = await caches.open(RUNTIME_CACHE);
  cache.put(request, res.clone());
  return res;
}

async function networkFirst(request) {
  try {
    const res = await fetch(request);
    const cache = await caches.open(RUNTIME_CACHE);
    cache.put(request, res.clone());
    return res;
  } catch (e) {
    const cached = await caches.match(request);
    if (cached) return cached;

    // fallback mínimo: si se cae internet, al menos abre login si existe cacheado
    const fallback = await caches.match("/login");
    if (fallback) return fallback;

    throw e;
  }
}
