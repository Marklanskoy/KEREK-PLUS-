/* KEREK 3.4 — bounded state validation before import/write. No HTML, no I/O.
   Reject damaged records instead of silently filtering personal history. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./core.js'),require('./autopilot-core.js'));else root.KerekSafety=factory(root.KerekCore,root.KerekAutopilotCore);})(typeof globalThis!=='undefined'?globalThis:this,function(C,A){
'use strict';
const MAX_BYTES=10000000,MAX_MONEY=1000000000000;
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const fail=(path)=>{const e=new Error('invalid_backup');e.field=path;e.storage=true;throw e;};
const string=(x,max,path,empty=true)=>{if(typeof x!=='string'||x.length>max||(!empty&&!x.trim()))fail(path);};
const number=(x,max,path,min=0,integer=true)=>{if(typeof x!=='number'||!Number.isFinite(x)||x<min||x>max||(integer&&!Number.isSafeInteger(x)))fail(path);};
const identifier=(x,path)=>{string(x,100,path,false);if(['__proto__','prototype','constructor'].includes(x))fail(path);};
function array(x,max,path){if(!Array.isArray(x)||x.length>max)fail(path);return x;}
function unique(xs,path){const ids=new Set();for(const x of xs){if(!object(x))fail(path);identifier(x.id,path+'.id');if(ids.has(x.id))fail(path+'.duplicate');ids.add(x.id);}return xs;}
function validateState(s){
 if(!object(s)||![3,32].includes(s.version))fail('version');
 if(s.revision!==undefined)number(s.revision,Number.MAX_SAFE_INTEGER-1,'revision');
 for(const [k,max] of Object.entries({name:80,phone:30,promo:40}))if(s[k]!==undefined)string(s[k],max,k);
 if(s.language!==undefined&&!['ru','kk'].includes(s.language))fail('language');
 if(s.theme!==undefined&&!['light','dark'].includes(s.theme))fail('theme');
 for(const k of ['balance','bonus'])if(s[k]!==undefined)number(s[k],MAX_MONEY,k);
 if(!object(s.cart)||Object.keys(s.cart).length>500)fail('cart');
 for(const [id,qty] of Object.entries(s.cart)){identifier(id,'cart.id');number(qty,99,'cart.'+id,1);}
 for(const k of ['favorites','seen']){if(s[k]!==undefined){for(const id of array(s[k],10000,k))identifier(id,k);}}
 if(s.pantry!==undefined)for(const x of unique(array(s.pantry,150,'pantry'),'pantry')){
  string(x.ingredient,100,'pantry.ingredient',false);number(x.amount,1000000,'pantry.amount',0,false);
  if(!['g','ml','pc'].includes(x.unit))fail('pantry.unit');
  if(x.unit==='pc'&&!Number.isInteger(x.amount))fail('pantry.amount');
  for(const k of ['expiresAt','checkedAt'])if(x[k]!==undefined&&x[k]!==''&&!C.validDate(x[k]))fail('pantry.'+k);
  if(x.confirmed!==undefined&&typeof x.confirmed!=='boolean')fail('pantry.confirmed');
 }
 if(s.addresses!==undefined)for(const x of unique(array(s.addresses,10,'addresses'),'addresses')){string(x.text,300,'address.text');for(const k of ['label','zone'])if(x[k]!==undefined)string(x[k],80,'address.'+k);}
 if(s.orders!==undefined)for(const o of unique(array(s.orders,10000,'orders'),'orders')){
  if(!object(o.quote))fail('order.quote');number(o.quote.total,MAX_MONEY,'order.total');
  for(const k of ['subtotal','discount','bonus','delivery','bonusEarned','savings'])if(o.quote[k]!==undefined)number(o.quote[k],MAX_MONEY,'order.quote.'+k);
  for(const k of ['status','createdAt','created_at','slot','paymentStatus'])if(o[k]!==undefined)string(o[k],150,'order.'+k);
  for(const k of ['address','comment'])if(o[k]!==undefined)string(o[k],500,'order.'+k);
  for(const x of array(o.items,500,'order.items')){if(!object(x))fail('order.item');string(x.name,300,'item.name');number(x.qty,99,'item.qty',1);if(x.id!==undefined)string(x.id,100,'item.id');if(x.price!==undefined)number(x.price,MAX_MONEY,'item.price');}
  if(o.timeline!==undefined)for(const x of array(o.timeline,1000,'order.timeline')){if(!object(x))fail('timeline');string(x.status,100,'timeline.status');if(x.at!==undefined)string(x.at,100,'timeline.at');}
 }
 if(s.tickets!==undefined)for(const x of unique(array(s.tickets,10000,'tickets'),'tickets')){string(x.text,3000,'ticket.text');for(const k of ['reply','kind','orderId','status','createdAt'])if(x[k]!==undefined)string(x[k],k==='reply'?10000:150,'ticket.'+k);}
 if(s.ledger!==undefined)for(const x of array(s.ledger,10000,'ledger')){if(!object(x))fail('ledger');number(x.delta,MAX_MONEY,'ledger.delta',-MAX_MONEY);}
 if(s.autopilot!==undefined)A.validate(s.autopilot);
 if(s.cartBudget!==undefined&&s.cartBudget!==null){if(!object(s.cartBudget))fail('cartBudget');number(s.cartBudget.amount,10000000,'cartBudget.amount',1);}
 if(s.pendingOrder!==undefined&&s.pendingOrder!==null){if(!object(s.pendingOrder))fail('pendingOrder');identifier(s.pendingOrder.key,'pendingOrder.key');string(s.pendingOrder.fingerprint,200000,'pendingOrder.fingerprint');}
 // Expired drafts are intentionally not restored, but other history is never discarded here.
 for(const k of ['checkoutDraft','supportDraft'])if(s[k]!==undefined&&s[k]!==null&&!object(s[k]))fail(k);
 return s;
}
function parseJSON(text){if(typeof text!=='string'||text.length>MAX_BYTES)fail('file.size');let x;try{x=JSON.parse(text);}catch{fail('json');}if(!object(x))fail('json');return x;}
function summary(s){validateState(s);return {orders:(s.orders||[]).length,cart:Object.values(s.cart).reduce((a,b)=>a+b,0),favorites:(s.favorites||[]).length,pantry:(s.pantry||[]).length,expenses:s.autopilot?.expenses.length||0,expenseTotal:(s.autopilot?.expenses||[]).reduce((a,b)=>a+b.amount,0)};}
return {MAX_BYTES,MAX_MONEY,validateState,parseJSON,summary};
});
