/* HeavyMusix app helper: lets fans install HeavyMusix Radio on their phone or computer.
   It only steps in when there is no internet: then it shows the last saved home page.
   Everything else (pages, news, the player) always comes fresh from the site. */
var CACHE = 'hmx-offline-1';
self.addEventListener('install', function(e){
  e.waitUntil(caches.open(CACHE).then(function(c){ return c.add('/'); }).then(function(){ return self.skipWaiting(); }));
});
self.addEventListener('activate', function(e){
  e.waitUntil(caches.keys().then(function(keys){
    return Promise.all(keys.filter(function(k){ return k !== CACHE; }).map(function(k){ return caches.delete(k); }));
  }).then(function(){ return self.clients.claim(); }));
});
self.addEventListener('fetch', function(e){
  if (e.request.mode !== 'navigate') return;
  e.respondWith(fetch(e.request).catch(function(){ return caches.match('/'); }));
});
