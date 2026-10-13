/* KEREK 3.6.0; complete bundle eb5ebcd90e685209 */
const VERSION='3.6.0',BUILD='eb5ebcd90e685209';
const PREFIX='kerek-release:'+self.registration.scope+':',CACHE=PREFIX+BUILD;
const ASSETS=["./index.html", "./manifest.webmanifest", "./icon-ref-32-350.png", "./icon-ref-180-350.png", "./icon-ref-192-350.png", "./icon-ref-512-350.png"],HASHES={"./index.html": "eb5ebcd90e685209030b03544c0883fcf3cd1797ac22235e3ec57081daff74b9", "./manifest.webmanifest": "9a14da06154c649f1f2f204b8bae8eb928bb9bfb37ed21ab6cec6d82ba4e8b17", "./icon-ref-32-350.png": "f68eec1446f70b6db497b66f189e8beef7068491ee6e814eec3af11fae64c3da", "./icon-ref-180-350.png": "87c3a46edbf1438720b98502b61127e1eab7f5e43f7e287600f85681fbe0b558", "./icon-ref-192-350.png": "f0a6d066b8e9d08ab90868cdd26b5614e0049bb1cbe2f338e90440c0cf7e407d", "./icon-ref-512-350.png": "458e23788e49a884b7933f11ee8cd7de708be3a8e123609b2f4e0e900a9f595d"};
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
