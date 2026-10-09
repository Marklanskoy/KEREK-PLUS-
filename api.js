/* Same-origin transport. Static browsing is explicit; server failures never silently become local orders. */
(function(){'use strict';
let enabled=false,csrf='';try{csrf=localStorage.getItem('kerek_csrf_v3')||'';}catch(_){}
async function request(path,{method='GET',body,timeout=12000}={}){
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
 try{
  const response=await fetch('api/'+path,{method,credentials:'same-origin',headers:{'Content-Type':'application/json',...(csrf?{'X-CSRF-Token':csrf}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{}),signal:controller.signal});
  let data;try{data=await response.json();}catch(_){throw new Error('server_unavailable');}
  if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:'validation_error');error.status=response.status;throw error;}
  return data;
 }catch(e){if(e.name==='AbortError')throw new Error('server_timeout');throw e;}finally{clearTimeout(timer);}
}
window.KerekAPI={
 get enabled(){return enabled;},
 async init(){if(!/^https?:$/.test(location.protocol))return null;try{const h=await request('health',{timeout:1700});if(h.service!=='kerek')return null;enabled=true;return await request('bootstrap');}catch(e){if(enabled)throw e;return null;}},
 request,
 setSession(value){csrf=value||'';try{if(csrf)localStorage.setItem('kerek_csrf_v3',csrf);else localStorage.removeItem('kerek_csrf_v3');}catch(_){}},
};})();
