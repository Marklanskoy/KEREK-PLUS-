/* KEREK Autopilot 2.2: explicit regular quantities; draft quote covers the WHOLE basket. */
(function(root,factory){if(typeof module==='object'&&module.exports)module.exports=factory(require('./core.js'));else root.KerekAutopilotCore=factory(root.KerekCore);})(typeof globalThis!=='undefined'?globalThis:this,function(C){
'use strict';
const LIMIT=10000000;
const defaults=()=>({schema:2,monthly:100000,weekly:20000,regular:[],expenses:[]});
function validate(x){
 if(!x||x.schema!==2||!Number.isSafeInteger(x.monthly)||!Number.isSafeInteger(x.weekly)||!C.int(x.monthly,1,LIMIT)||!C.int(x.weekly,1,LIMIT)||!Array.isArray(x.regular)||!Array.isArray(x.expenses)||x.regular.length>150||x.expenses.length>5000)throw new Error('invalid_autopilot');
 const ids=new Set();for(const r of x.regular){if(typeof r.id!=='string'||!r.id||r.id.length>100||['__proto__','constructor','prototype'].includes(r.id)||ids.has(r.id)||!Number.isSafeInteger(r.qty)||!C.int(r.qty,1,99))throw new Error('invalid_regular');ids.add(r.id);}
 ids.clear();for(const r of x.expenses){if(!r||typeof r.id!=='string'||!r.id||r.id.length>100||['__proto__','constructor','prototype'].includes(r.id)||ids.has(r.id)||!Number.isSafeInteger(r.amount)||!C.int(r.amount,1,LIMIT)||(!C.validDate(r.date)||r.date>C.localDate())||typeof r.note!=='string'||r.note.length>160)throw new Error('invalid_expense');ids.add(r.id);}
 return x;
}
function migrate(settings={},manual=[]){
 const x=defaults();
 if(!settings||typeof settings!=='object'||Array.isArray(settings)||!Array.isArray(manual)||manual.length>5000)throw new Error('invalid_autopilot');
 for(const key of ['monthly','weekly']){if(settings[key]!==undefined){if(!C.int(settings[key],1,LIMIT))throw new Error('invalid_autopilot');x[key]=Number(settings[key]);}}
 manual.forEach((r,i)=>{
  if(!r||typeof r.date!=='string'||!C.int(r.amount,1,LIMIT))throw new Error('invalid_expense');
  // Old records were timestamps. Preserve the user's local expense day, not the UTC day.
  const d=C.validDate(r.date)?r.date:Number.isFinite(Date.parse(r.date))?C.localDate(new Date(r.date)):'';
  if(!C.validDate(d))throw new Error('invalid_expense');
  x.expenses.push({id:'legacy-'+i,amount:Number(r.amount),date:d,note:'Импортированный расход'});
 });
 return validate(x);
}
function spend(x,orders=[],month=C.localDate().slice(0,7)){
 const real=x.expenses.filter(r=>r.date.startsWith(month)).reduce((s,r)=>s+r.amount,0);
 // Test and unpaid orders NEVER reduce the personal budget, regardless of order status.
 const demo=orders.filter(o=>!['cancelled','canceled'].includes(o.status)&&String(o.createdAt||o.created_at||'').startsWith(month)).reduce((s,o)=>s+(Number(o.quote?.total)||0),0);
 return {real,demo,remaining:x.monthly-real,overrun:Math.max(0,real-x.monthly)};
}
function candidates(products,orders=[],favorites=[]){const latest=new Map();const valid=orders.filter(o=>!['cancelled','canceled'].includes(o.status)).sort((a,b)=>String(b.createdAt||b.created_at).localeCompare(String(a.createdAt||a.created_at)));
 for(const o of valid)for(const l of o.items||[]){if(!latest.has(String(l.id))&&C.int(l.qty,1,99))latest.set(String(l.id),Number(l.qty));}
 return products.filter(p=>p.active&&p.stock>0).map(p=>({p,qty:latest.get(p.id)||1,reason:latest.has(p.id)?'history':favorites.includes(p.id)?'favorite':'catalog'})).sort((a,b)=>({history:0,favorite:1,catalog:2}[a.reason]-{history:0,favorite:1,catalog:2}[b.reason])||Number(b.p.popularity||0)-Number(a.p.popularity||0));
}
function propose({cart={},regular=[],pantry=[],products=[],settings,options={},mode='merge',budget}){
 if(!Number.isSafeInteger(budget)||budget<0||budget>LIMIT)throw new Error('invalid_budget');
 if(!['merge','replace'].includes(mode)||!Array.isArray(regular)||regular.length>150||new Set(regular.map(x=>x?.id)).size!==regular.length)throw new Error('invalid_regular');
 const base=mode==='replace'?{}:{...cart},next={...base},home=new Map(),notes=[],items=[],missing=[];
 for(const x of C.usablePantry(pantry)){const k=x.ingredient+'|'+x.unit;home.set(k,(home.get(k)||0)+Number(x.amount));}
 for(const line of regular){const p=products.find(p=>p.id===line.id);if(!p||!p.active){missing.push({id:line.id,reason:'unavailable'});continue;}
  if(!C.int(line.qty,1,99)||!(p.pack>0)){missing.push({id:p.id,reason:'quantity'});continue;}
  const wanted=p.pack*Number(line.qty),k=p.ingredient+'|'+p.unit,owned=Math.min(wanted,home.get(k)||0);home.set(k,(home.get(k)||0)-owned);
  const need=Math.ceil(Math.max(0,wanted-owned)/p.pack),inCart=Number(base[p.id]||0),target=Math.max(inCart,need),added=Math.max(0,target-inCart);
  if(target>0)next[p.id]=target;
  if(target>p.stock||target>99)missing.push({id:p.id,reason:'stock',wanted:target,available:p.stock});
  if(!added)notes.push({id:p.id,reason:owned>=wanted?'pantry':'in_cart'});
  items.push({id:p.id,wanted:Number(line.qty),owned,inCart,target,added});
 }
 const before=C.quote(cart,products,settings,options),order=C.orderReadiness(next,products,settings,options),quote=order.quote,overrun=Math.max(0,quote.total-budget),shortMinimum=Math.max(0,Number(settings.minOrder||0)-quote.subtotal);
 const changed=JSON.stringify(Object.entries(next).sort())!==JSON.stringify(Object.entries(cart).sort());
 const ready=changed&&items.length>0&&Object.keys(next).length>0&&!missing.length&&order.canOrder&&!overrun;
 return {cart:next,items,notes,missing,quote,order,before,budget,overrun,shortMinimum,changed,ready,mode};
}
return {defaults,validate,migrate,spend,candidates,propose};
});
