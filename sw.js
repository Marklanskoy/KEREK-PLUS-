/* KEREK 3.4.0; complete bundle 7c8c66926d56d3eb */
const VERSION='3.4.0',BUILD='7c8c66926d56d3eb';
const PREFIX='kerek-release:'+self.registration.scope+':',CACHE=PREFIX+BUILD;
const ASSETS=["./index.html", "./manifest.webmanifest", "./icon-32.png", "./icon-180.png", "./icon-192.png", "./icon-512.png"],HASHES={"./index.html": "7c8c66926d56d3ebc22590f826e4e6977f10113c94303186f3e2b690e159a705", "./manifest.webmanifest": "052570a02dd45f016bb51652a80dd742d230ef4707647e4785f92ed39fcc03c4", "./icon-32.png": "9325023a929a50a37618592fcc8624b1deb2e658b0b1a7977aec2db1aeb59114", "./icon-180.png": "78213d68dbc3df94fe52da1e931dbee47901a8364065a6349377ba5dbdd14af5", "./icon-192.png": "a014d7d5593b9dab2b71854a379b637748b427a7d7267047bcb73571a288ca40", "./icon-512.png": "f511c8ab538169a36e58948d9c7c34de98a08180e09df8cefe03692302f26818"};
/* Cache is a versioned set, not a mix of independently fetched scripts.
   Hashes check build consistency, not a signature against a compromised host. */
const HOME=new URL('./index.html',self.registration.scope).href;
async function verified(response,expected){
 if(!response||!response.ok||response.redirected)throw new Error('asset_unavailable');
 const digest=await crypto.subtle.digest('SHA-256',await response.clone().arrayBuffer());
 const hash=Array.from(new Uint8Array(digest),n=>n.toString(16).padStart(2,'0')).join('');
 if(hash!==expected)throw new Error('asset_mismatch');return response;
}
async function network(request){const abort=new AbortController(),timer=setTimeout(()=>abort.abort(),8000);try{return await fetch(request,{cache:'no-store',redirect:'error',signal:abort.signal});}finally{clearTimeout(timer);}}
self.addEventListener('install',e=>e.waitUntil((async()=>{
 // Validate the whole public bundle before starting any cache writes.
 const responses=await Promise.all(ASSETS.map(async path=>verified(await network(new URL(path,self.registration.scope).href),HASHES[path])));
 const cache=await caches.open(CACHE);
 await Promise.all(ASSETS.map((path,i)=>cache.put(new URL(path,self.registration.scope).href,responses[i])));
})()));
self.addEventListener('message',e=>{if(e.data?.type==='ACTIVATE')self.skipWaiting();if(e.data?.type==='GET_BUILD')e.ports?.[0]?.postMessage({version:VERSION,bundle:BUILD});});
self.addEventListener('activate',e=>e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>(k.startsWith(PREFIX)&&k!==CACHE)||k==='kerek-shell-v3.1-autopilot').map(k=>caches.delete(k)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',e=>{
 const u=new URL(e.request.url),scope=new URL(self.registration.scope);
 if(e.request.method!=='GET'||u.origin!==scope.origin||!u.pathname.startsWith(scope.pathname))return;
 const rel=u.pathname.slice(scope.pathname.length);
 if(rel.startsWith('api/')||rel.startsWith('admin')||['update.html','sw.js','release.json'].includes(rel))return;
 const navigation=e.request.mode==='navigate'&&(rel===''||rel==='index.html');
 const asset=navigation?'./index.html':ASSETS.find(a=>new URL(a,scope).pathname===u.pathname);
 if(!asset)return;
 e.respondWith((async()=>{const cache=await caches.open(CACHE),key=new URL(asset,scope).href;
  if(!navigation){const hit=await cache.match(key);if(hit)return hit;}
  try{const response=await verified(await network(e.request),HASHES[asset]);await cache.put(key,response.clone());return response;}
  catch{const cached=await cache.match(key);return cached||new Response('Файлы этой версии недоступны. Откройте update.html с интернетом. Записи не удалены.',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8'}});}
 })());
});
