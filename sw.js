/* KEREK 3.3.0; complete bundle a84173f814d644b4 */
const PREFIX='kerek-release:'+self.registration.scope+':',CACHE=PREFIX+'a84173f814d644b4';
const ASSETS=["./index.html", "./manifest.webmanifest", "./icon-32.png", "./icon-180.png", "./icon-192.png", "./icon-512.png"];
const HOME=new URL('./index.html',self.registration.scope).href;
self.addEventListener('install',e=>e.waitUntil(caches.open(CACHE).then(c=>c.addAll(ASSETS))));
self.addEventListener('message',e=>{if(e.data?.type==='ACTIVATE')self.skipWaiting();});
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>(k.startsWith(PREFIX)&&k!==CACHE)||k==='kerek-shell-v3.1-autopilot').map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url),scope=new URL(self.registration.scope);
 if(e.request.method!=='GET'||u.origin!==scope.origin||!u.pathname.startsWith(scope.pathname))return;
 const rel=u.pathname.slice(scope.pathname.length);
 if(rel.startsWith('api/')||rel.startsWith('admin')||['update.html','sw.js','release.json'].includes(rel))return;
 // All executable code is inside the index bundle. Never cache private API responses.
 if(e.request.mode==='navigate'&&(rel===''||rel==='index.html')){
  e.respondWith(fetch(e.request).then(async r=>{if(r.ok)return r;return (await caches.match(HOME))||r;}).catch(async()=> (await caches.match(HOME))||new Response('Нет сети. Откройте KEREK онлайн один раз.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}})));return;
 }
 if(ASSETS.some(a=>new URL(a,scope).pathname===u.pathname))e.respondWith(caches.open(CACHE).then(async c=>(await c.match(e.request))||fetch(e.request)));
});
