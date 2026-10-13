/* Explicit static or server mode. A failed server never creates a local order. */
(function(){'use strict';
let enabled=false,csrf='';try{csrf=sessionStorage.getItem('kerek_csrf_v32')||localStorage.getItem('kerek_csrf_v3')||'';}catch{}
async function request(path,{method='GET',body,timeout=12000}={}){
 if(!/^[a-z0-9_/-]+$/i.test(path))throw new Error('invalid_api_path');
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),timeout);
 try{
  const response=await fetch('api/'+path,{method,credentials:'same-origin',cache:'no-store',redirect:'error',headers:{'Content-Type':'application/json',...(csrf?{'X-CSRF-Token':csrf}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{}),signal:controller.signal});
  let data;try{data=await response.json();}catch{throw new Error('server_unavailable');}
  if(!response.ok){const error=new Error(typeof data.detail==='string'?data.detail:'validation_error');error.status=response.status;throw error;}
  return data;
 }catch(e){if(e.name==='AbortError')throw new Error('server_timeout');throw e;}finally{clearTimeout(timer);}
}
window.KerekAPI={get enabled(){return enabled;},
 async init(){if(window.KEREK_CONFIG?.mode!=='server')return null;
  const h=await request('health',{timeout:6000});if(h.service!=='kerek')throw new Error('server_unavailable');enabled=true;return request('bootstrap');},
 request,setSession(value){csrf=value||'';try{if(csrf)sessionStorage.setItem('kerek_csrf_v32',csrf);else sessionStorage.removeItem('kerek_csrf_v32');localStorage.removeItem('kerek_csrf_v3');}catch{}}
};})();
