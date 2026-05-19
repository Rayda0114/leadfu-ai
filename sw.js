/* 領富 AI · Service Worker
 * 策略：
 *   1. CSS / JS → network-first（避免用戶卡在舊版，特別是手機板 layout fix）
 *   2. 圖示 / manifest → stale-while-revalidate（變動少，快取優先）
 *   3. 即時資料 data/*.json → network-first（永遠拿最新）
 *   4. HTML 頁面 → network-first
 */

const VERSION = "v3.15.7";
const STATIC_CACHE  = "leadfu-static-"  + VERSION;
const DATA_CACHE    = "leadfu-data-"    + VERSION;

// 安裝時預載的核心資產
const CORE_ASSETS = [
  "/",
  "/index.html",
  "/manifest.json",
  "/css/style.css",
  "/js/main.js",
  "/icons/icon.svg",
  "/icons/icon-192.png",
  "/icons/icon-512.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then((cache) => cache.addAll(CORE_ASSETS).catch(() => null))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((k) => k !== STATIC_CACHE && k !== DATA_CACHE)
            .map((k) => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  // 只處理 GET（POST / 表單不走 SW）
  if (req.method !== "GET") return;

  const url = new URL(req.url);

  // 跨網域資源不攔截（讓瀏覽器自己處理）
  if (url.origin !== self.location.origin) return;

  // data/*.json 用 network-first
  if (url.pathname.startsWith("/data/") && url.pathname.endsWith(".json")) {
    event.respondWith(networkFirst(req));
    return;
  }

  // 🛠 CSS / JS 也用 network-first — 避免用戶卡在舊版（手機板 layout fix 時很關鍵）
  if (url.pathname.endsWith(".css") || url.pathname.endsWith(".js")) {
    event.respondWith(networkFirst(req));
    return;
  }

  // 導覽請求（HTML 頁面）也用 network-first
  if (req.mode === "navigate" ||
      (req.destination === "document") ||
      url.pathname.endsWith(".html") ||
      url.pathname === "/" ||
      !url.pathname.includes(".")) {
    event.respondWith(networkFirst(req));
    return;
  }

  // 其餘（圖片 / manifest / svg）：stale-while-revalidate
  event.respondWith(staleWhileRevalidate(req));
});

async function networkFirst(req) {
  try {
    const fresh = await fetch(req);
    if (fresh && fresh.ok) {
      const cache = await caches.open(DATA_CACHE);
      cache.put(req, fresh.clone());
    }
    return fresh;
  } catch (e) {
    const cached = await caches.match(req);
    if (cached) return cached;
    throw e;
  }
}

async function staleWhileRevalidate(req) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(req);
  const fetchPromise = fetch(req).then((resp) => {
    if (resp && resp.ok) cache.put(req, resp.clone());
    return resp;
  }).catch(() => null);
  return cached || fetchPromise || new Response("", { status: 504 });
}
