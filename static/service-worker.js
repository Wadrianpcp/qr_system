self.addEventListener('install', event => {
  event.waitUntil(
    caches.open('qr-cache').then(cache => {
      return cache.addAll([
        '/',
        '/static/style.css',  // ajuste conforme seu projeto
        '/static/script.js'
      ]);
    })
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request).then(response => {
      return response || fetch(event.request);
    })
  );
});
