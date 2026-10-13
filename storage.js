/* KEREK 3.2 — a single writer per app, revision checks and explicit recovery.
 * Local browser storage is NOT encrypted. Never clear all origin storage.
 * A new key prevents an older 3.0 client from overwriting migrated records.
 */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory;else root.KerekStorageFactory=factory;})(typeof globalThis!=='undefined'?globalThis:this,function(storage,locks,scope){
'use strict';
const legacyKeys=['kerek_v3','kerek_autopilot_v1','kerek_autopilot_manual_v1','kerek_basket','kerek_fav','kerek_pantry','kerek_orders','kerek_profile','kerek_support','kerek_csrf_v3'];
const key='kerek_3_2:'+scope,original=key+':before-update',preImport=key+':before-import';
let writable=false,lastRaw=null,release=null,opened=false;
const error=(code)=>{const e=new Error(code);e.storage=true;return e;};
function read(){const raw=storage.getItem(key);lastRaw=raw;if(!raw)return null;let value;try{value=JSON.parse(raw);}catch{throw error('storage_corrupt');}if(!value||Array.isArray(value)||typeof value!=='object'||value.version!==32||!Number.isSafeInteger(value.revision)||value.revision<0)throw error('storage_corrupt');return value;}
function acquire(){return new Promise((resolve,reject)=>{
 if(!locks?.request){resolve(false);return;}
 let announced=false;
 locks.request(key+':writer',{ifAvailable:true},lock=>{
  if(!lock){announced=true;resolve(false);return;}
  writable=true;announced=true;resolve(true);return new Promise(r=>release=()=>{writable=false;r();});
 }).catch(e=>{if(!announced)reject(e);writable=false;});
});}
async function open(){if(!opened){await acquire();opened=true;}return read();}
function assertWritable(){if(!writable)throw error('storage_readonly');}
function write(value){assertWritable();const live=storage.getItem(key);if(live!==lastRaw)throw error('storage_conflict');const prev=lastRaw?JSON.parse(lastRaw):null;
 const next={...value,version:32,revision:(prev?.revision||0)+1};const raw=JSON.stringify(next);storage.setItem(key,raw);lastRaw=raw;return JSON.parse(raw);
}
function backup(kind='migration'){assertWritable();const k=kind==='import'?preImport:original;if(kind!=='import'&&storage.getItem(k))return;
 const values={};if(lastRaw)values[key]=lastRaw;else for(const k of legacyKeys.filter(k=>k!=='kerek_csrf_v3')){const raw=storage.getItem(k);if(raw!==null)values[k]=raw;}
 if(Object.keys(values).length)storage.setItem(k,JSON.stringify({at:new Date().toISOString(),values}));
}
function erase(empty){assertWritable();if(storage.getItem(key)!==lastRaw)throw error('storage_conflict');
 // Write an empty tombstone first. Interrupted cleanup cannot re-import old personal data.
 const clean=write(empty);for(const k of [...legacyKeys,original,preImport])storage.removeItem(k);return clean;
}
function recovery(){const out={};for(const k of [key,original,preImport,...legacyKeys]){const raw=storage.getItem(k);if(raw!==null&&k!=='kerek_csrf_v3')out[k]=raw;}return out;}
function latest(){return lastRaw?JSON.parse(lastRaw):null;}
return {key,original,preImport,legacyKeys,open,read,write,backup,erase,recovery,latest,assertWritable,get writable(){return writable;},get serialized(){return lastRaw;},close(){release?.();release=null;}};
});
