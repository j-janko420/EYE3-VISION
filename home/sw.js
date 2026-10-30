// EYE3 Home service worker: cache the app shell so it opens instantly and even offline.
// Live streams and the web/YouTube frames still need the network; this only caches the UI.
var CACHE = "eye3-home-v20";
var SHELL = ["./", "./index.html", "./manifest.webmanifest", "./icon-192.png", "./icon-512.png", "./i18n-fr.js", "./i18n-ar.js"];
self.addEventListener("install", function (e) {
  e.waitUntil(caches.open(CACHE).then(function (c) { return c.addAll(SHELL); }).then(function () { return self.skipWaiting(); }));
});
self.addEventListener("activate", function (e) {
  e.waitUntil(caches.keys().then(function (keys) {
    return Promise.all(keys.map(function (k) { if (k !== CACHE) return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});
self.addEventListener("fetch", function (e) {
  var url = new URL(e.request.url);
  // Only handle same-origin GETs for the app shell; never touch streams or cross-origin frames.
  if (e.request.method !== "GET" || url.origin !== self.location.origin || !url.pathname.indexOf) return;
  var inScope = url.pathname.indexOf("/home/") !== -1;
  if (!inScope) return;
  e.respondWith(
    caches.match(e.request).then(function (hit) {
      return hit || fetch(e.request).then(function (res) {
        if (res && res.status === 200 && res.type === "basic") {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(e.request, copy); });
        }
        return res;
      }).catch(function () { return caches.match("./index.html"); });
    })
  );
});
