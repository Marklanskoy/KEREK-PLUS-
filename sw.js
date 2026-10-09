/* App shell only. Never cache authentication, profiles, admin, APIs or purchases. */
const CACHE='kerek-shell-v3.0.0';
const ASSETS=['./','./index.html','./styles.css','./js/photos.js','./js/data.js','./js/core.js','./js/api.js','./js/app.js','./assets/icon.svg'];
self.addEventListener('install',event=>{event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)));});
self.addEventListener('activate',event=>{event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('kerek-shell-')&&k!==CACHE).map(k=>caches.delete(k)))));});
self.addEventListener('fetch',event=>{
 const u=new URL(event.request.url),scope=new URL(self.registration.scope);
 if(event.request.method!=='GET'||u.origin!==scope.origin)return;
 const relative=u.pathname.slice(scope.pathname.length);
 if(relative.startsWith('api/')||relative.startsWith('admin')||relative==='js/admin.js')return;
 if(event.request.mode==='navigate'){
  event.respondWith(fetch(event.request).catch(()=>caches.match('./index.html')));return;
 }
 if(ASSETS.some(a=>new URL(a,scope).pathname===u.pathname))event.respondWith(caches.match(event.request).then(cached=>cached||fetch(event.request)));
});
