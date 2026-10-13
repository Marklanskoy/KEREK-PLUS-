/* Pure, deterministic domain functions. No DOM, network or hidden AI prices. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.KerekCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const norm=s=>String(s??'').toLowerCase().replace(/ё/g,'е').replace(/[^\p{L}\p{N}\s]/gu,' ').replace(/\s+/g,' ').trim();
const int=(v,min,max)=>Number.isInteger(Number(v))&&Number(v)>=min&&Number(v)<=max;
const clone=x=>JSON.parse(JSON.stringify(x));
function cleanCart(cart,products){const out={};if(!cart||typeof cart!=='object'||Array.isArray(cart))return out;for(const p of products){const n=Number(cart[p.id]);if(int(n,1,99)&&p.active&&p.stock>0)out[p.id]=Math.min(n,p.stock);}return out;}
function distance(a,b){a=norm(a);b=norm(b);let v=Array.from({length:b.length+1},(_,i)=>i);for(let i=0;i<a.length;i++){let w=[i+1];for(let j=0;j<b.length;j++)w[j+1]=Math.min(w[j]+1,v[j+1]+1,v[j]+(a[i]===b[j]?0:1));v=w;}return v[b.length];}
function search(products,query){const q=norm(String(query??'').slice(0,160));if(!q)return {items:products,corrected:false};const words=q.split(' ');let direct=products.filter(p=>{let s=norm(p.name+' '+p.name_kk+' '+p.brand);return words.every(w=>s.includes(w));});if(direct.length)return {items:direct,corrected:false};return {items:products.filter(p=>{const ws=norm(p.name+' '+p.name_kk+' '+p.brand).split(' ');return words.every(w=>ws.some(x=>w.length>=4&&distance(x,w)<= (w.length>7?2:1)));}),corrected:true};}
// All money here is integer KZT in this demo catalogue; corrupt input fails closed.
const MAX_MONEY=1000000000000;
const validMoney=n=>typeof n==='number'&&Number.isSafeInteger(n)&&n>=0&&n<=MAX_MONEY;
function businessDate(now=new Date()){
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Almaty',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now),get=k=>parts.find(p=>p.type===k).value;
 return get('year')+'-'+get('month')+'-'+get('day');
}
function quote(cart,products,settings,{promo='',bonus=0,balance=0,zone='almaty'}={}){
 const errors=[],lines=[];let subtotal=0,savings=0;
 const failed=code=>({errors:[code],lines:[],subtotal:0,discount:0,bonus:0,delivery:0,total:0,savings:0,maxBonus:0,bonusEarned:0,freeRemaining:0,promoError:''});
 if(!cart||typeof cart!=='object'||Array.isArray(cart)||Object.keys(cart).length>500)return failed('invalid_cart');
 if(!Array.isArray(products)||!settings||!['deliveryFee','freeDeliveryFrom','minOrder'].every(k=>validMoney(settings[k]))||!['bonusRate','maxBonusPercent'].every(k=>typeof settings[k]==='number'&&Number.isFinite(settings[k])&&settings[k]>=0&&settings[k]<=100)||!Array.isArray(settings.promos)||!Array.isArray(settings.zones))return failed('invalid_settings');
 if(!validMoney(balance)||!validMoney(bonus))errors.push('invalid_bonus');
 for(const [id,value] of Object.entries(cart)){
  const p=products.find(x=>x&&x.id===id),qty=Number(value);
  if(!p||!p.active){errors.push('unknown_product:'+id);continue;}
  if(!int(value,1,99)||typeof value==='boolean'){errors.push('invalid_quantity:'+id);continue;}
  if(!validMoney(p.price)||!Number.isSafeInteger(p.stock)||p.stock<0||!(Number.isFinite(p.pack)&&p.pack>0)||!['g','ml','pc'].includes(p.unit)){errors.push('invalid_product:'+id);continue;}
  if(qty>p.stock)errors.push('stock:'+id);
  const amount=p.price*qty;if(!validMoney(amount)||!validMoney(subtotal+amount)){errors.push('amount_overflow');continue;}
  subtotal+=amount;const old=validMoney(p.oldPrice)?p.oldPrice:p.price;const difference=Math.max(0,old-p.price)*qty;
  if(validMoney(savings+difference))savings+=difference;
  lines.push({id,qty,name:p.name,name_kk:p.name_kk,price:p.price,amount});
 }
 let discount=0,promoError='';
 const code=String(promo).trim().toUpperCase();
 if(code){const p=settings.promos.find(p=>p&&p.code===code&&p.active&&(!p.endsAt||validDate(p.endsAt)&&p.endsAt>=businessDate()));
  if(!p)promoError='promo_invalid';
  else if(!validMoney(p.minSubtotal)||!validMoney(p.maxDiscount)||typeof p.percent!=='number'||!Number.isFinite(p.percent)||p.percent<0||p.percent>100)errors.push('invalid_settings');
  else if(subtotal<p.minSubtotal)promoError='promo_min';
  else discount=Math.min(subtotal,p.maxDiscount,Math.floor(subtotal*p.percent/100));
 }
 const maxBonus=Math.max(0,Math.min(validMoney(balance)?balance:0,Math.floor((subtotal-discount)*settings.maxBonusPercent/100)));
 const usedBonus=validMoney(bonus)?Math.min(bonus,maxBonus):0;
 const z=settings.zones.find(z=>z&&z.id===zone&&z.enabled);
 if(lines.length&&!z)errors.push('zone_unavailable');
 if(z&&!validMoney(z.fee))errors.push('invalid_settings');
 const delivery=lines.length&&subtotal<settings.freeDeliveryFrom?(validMoney(z?.fee)?z.fee:settings.deliveryFee):0;
 const total=Math.max(0,subtotal-discount-usedBonus)+delivery;if(!validMoney(total))return failed('amount_overflow');
 return {lines,errors,subtotal,discount,bonus:usedBonus,maxBonus,delivery,total,savings:savings+discount+usedBonus,promoError,bonusEarned:Math.floor(Math.max(0,subtotal-discount-usedBonus)*settings.bonusRate/100),freeRemaining:Math.max(0,settings.freeDeliveryFrom-subtotal)};
}

// One shared rule for recipes and Autopilot. Unknown dates are not fresh confirmation.
function localDate(now=new Date()){return now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')+'-'+String(now.getDate()).padStart(2,'0');}
function validDate(s){if(typeof s!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(s))return false;const d=new Date(s+'T12:00:00');return Number.isFinite(+d)&&localDate(d)===s;}
function pantryStatus(x,today=localDate()){
 if(!x||!Number.isFinite(Number(x.amount))||Number(x.amount)<=0||!['g','ml','pc'].includes(x.unit))return 'invalid';
 if(x.expiresAt&&(!validDate(x.expiresAt)||x.expiresAt<today))return 'expired';
 if(x.confirmed!==true||!validDate(x.checkedAt)||x.checkedAt>today)return 'unconfirmed';
 const age=(new Date(today+'T12:00:00')-new Date(x.checkedAt+'T12:00:00'))/86400000;
 return age>14?'stale':'available';
}
function usablePantry(xs,today=localDate()){return (Array.isArray(xs)?xs:[]).filter(x=>pantryStatus(x,today)==='available');}
function substitute(cart,products,fromId,toId){
 const from=products.find(p=>p.id===fromId),to=products.find(p=>p.id===toId),qty=Number(cart[fromId]);
 if(!from||!to||!to.active||fromId===toId||!int(qty,1,99)||from.ingredient!==to.ingredient||from.unit!==to.unit||!(from.pack>0&&to.pack>0))return null;
 const added=Math.ceil(from.pack*qty/to.pack),merged=Number(cart[toId]||0)+added;
 if(!int(merged,1,99)||merged>to.stock)return null;
 const next={...cart};delete next[fromId];next[toId]=merged;
 return {cart:next,qty:added};
}

function aggregate(recipeIds,people,recipes,products,pantry=[],overrides={}){
 const requirements=Object.create(null),byIngredient=Object.create(null);const missing=[];
 if(!int(people,1,8)||!Array.isArray(recipeIds)||recipeIds.length>100)return {cart:{},details:[],missing:['invalid_plan']};
 for(const rid of recipeIds){const r=recipes.find(r=>r.id===rid);if(!r){missing.push(rid);continue;}for(const i of r.ingredients){requirements[i.key]=(requirements[i.key]||0)+i.amount*people;byIngredient[i.key]=i.unit;}}
 const atHome=Object.create(null);
 for(const h of usablePantry(pantry)){if(h.unit!==byIngredient[h.ingredient])continue;atHome[h.ingredient]=(atHome[h.ingredient]||0)+Number(h.amount);}
 const cart={},details=[];
 for(const [key,required] of Object.entries(requirements)){
  const fromHome=Math.min(required,atHome[key]||0),needed=Math.max(0,Math.round((required-fromHome)*100)/100);
  const candidates=products.filter(p=>p.active&&p.stock>0&&p.ingredient===key&&p.unit===byIngredient[key]).map(p=>({p,qty:Math.ceil(needed/p.pack)})).filter(x=>x.qty<=x.p.stock&&x.qty<=99).sort((a,b)=>a.qty*a.p.price-b.qty*b.p.price||a.p.pack-b.p.pack);
  const chosen=overrides[key]?candidates.find(x=>x.p.id===overrides[key]):candidates[0];
  if(needed>0&&!chosen){missing.push(key);details.push({ingredient:key,required,fromHome,needed,unit:byIngredient[key],missing:true});continue;}
  if(chosen&&needed>0)cart[chosen.p.id]=(cart[chosen.p.id]||0)+chosen.qty;
  details.push({ingredient:key,required,fromHome,needed,unit:byIngredient[key],id:chosen?.p.id,qty:needed>0?chosen?.qty||0:0,leftover:needed>0?Math.round((chosen.p.pack*chosen.qty-needed)*100)/100:0});
 }
 return {cart,details,missing};
}
const exclusions={молоко:'milk',молока:'milk',сүт:'milk',сүтсіз:'milk',сыр:'cheese',сыра:'cheese',ірімшік:'cheese',яйца:'egg',яиц:'egg',жұмыртқа:'egg',глютен:'gluten',глютена:'gluten',мясо:'meat',мяса:'meat',ет:'meat',етсіз:'meat',помидоры:'tomato',помидоров:'tomato',қызанақ:'tomato',бананы:'banana',бананов:'banana',овсянка:'oats',авокадо:'avocado',грибы:'mushroom',грибов:'mushroom',саңырауқұлақ:'mushroom'};
function parseRequest(text,defaults={}){
 const s=norm(text),out={people:2,days:5,budget:15000,minutes:45,meal:'dinner',vegetarian:false,exclude:[],...defaults};
 const numberWords={одного:1,один:1,двух:2,двоих:2,два:2,двое:2,трех:3,троих:3,три:3,четырех:4,четверых:4,четыре:4,пяти:5,пять:5,шести:6,шесть:6,семи:7,семь:7,бір:1,екі:2,үш:3,төрт:4,бес:5,алты:6,жеті:7};
 let sn=s;for(const [w,n] of Object.entries(numberWords))sn=sn.replace(new RegExp('(?<![\\p{L}])'+w+'(?![\\p{L}])','gu'),String(n));
 const money=text.match(/(?:за|до|бюджет(?:ом)?|бюджетім|на сумму)?\s*(\d[\d\s\u00a0]{1,10})\s*(?:₸|тенге|тг|теңге)/i)||text.match(/(?:за|до|бюджет)\s+(\d[\d\s]{2,10})/i);if(money)out.budget=Number(money[1].replace(/\s/g,''));
 const pe=sn.match(/(\d+)\s*(?:человек|чел|адам|персон)/)||sn.match(/(?:семь[яию]\s*(?:из)?\s*|нас\s+)(\d+)(?:\s|$)/)||sn.match(/на\s+(\d+)(?!\d)(?!\s*(?:дн|день|күн|₸|тенге|теңге|тг))(?:\s|$)/);if(pe&&Number(pe[1])<=8)out.people=Number(pe[1]);
 const day=sn.match(/(\d+)\s*(?:дней|дня|день|күн)/);if(day)out.days=Number(day[1]);else if(/недел|апта/.test(sn))out.days=7;
 const mins=sn.match(/(\d+)\s*(?:минут|мин|минуттан)/);if(mins)out.minutes=Number(mins[1]);
 if(/завтрак|таңғы/.test(s))out.meal='breakfast';if(/без мяса|етсіз|вегетариан/.test(s))out.vegetarian=true;
 delete out.recipe;
 if(/плов|палау/.test(s)){out.recipe='plov';out.days=1;out.minutes=Math.max(45,out.minutes);}
 const excludeText=s.match(/(?:без|не едим|исключить|алып таста)\s+(.+)/)?.[1]||'';
 out.exclude=[...new Set([...(out.exclude||[]),...Object.entries(exclusions).filter(([w])=>excludeText.includes(w)||w.endsWith('сіз')&&s.includes(w)).map(([,v])=>v)])];
 return out;
}
function parseExclusions(text){const s=norm(text);return [...new Set(s.split(/[ ,]+/).map(x=>exclusions[x]||x).filter(Boolean))];}
function makePlan(options,products,recipes,settings,pantry=[]){
 const o={people:2,days:5,budget:15000,minutes:45,meal:'dinner',exclude:[],...options};
 if(!int(o.people,1,8)||!int(o.days,1,7)||!int(o.budget,500,500000)||!int(o.minutes,5,180))return {error:'invalid_plan',selected:[],cart:{}};
 const excluded=new Set(o.exclude||[]),ids=[];
 const allowed=recipes.filter(r=>(!o.recipe?r.meal===o.meal:r.id===o.recipe)&&r.minutes<=o.minutes&&(!o.vegetarian||r.vegetarian)&&!r.ingredients.some(i=>excluded.has(i.key)||excluded.has('meat')&&['chicken','beef','fish'].includes(i.key)||excluded.has('gluten')&&['pasta','bread','oats','flour'].includes(i.key)||excluded.has('milk')&&['milk','cheese','butter','yogurt'].includes(i.key)));
 if(!allowed.length)return {error:'no_recipes',selected:[],cart:{}};
 for(let day=0;day<o.days;day++){
  const candidates=allowed.map(r=>{const a=aggregate([...ids,r.id],o.people,recipes,products,pantry);const q=quote(a.cart,products,settings);return {r,a,q,score:q.total+ids.filter(id=>id===r.id).length*1500};}).filter(v=>!v.a.missing.length&&!v.q.errors.length&&v.q.total<=o.budget).sort((a,b)=>a.score-b.score||a.r.id.localeCompare(b.r.id));
  if(!candidates.length)break;ids.push(candidates[0].r.id);
 }
 const a=aggregate(ids,o.people,recipes,products,pantry);const order=orderReadiness(a.cart,products,settings),q=order.quote;
 return {...a,quote:q,order,orderable:order.canOrder,allAtHome:ids.length>0&&!a.missing.length&&order.empty,selected:ids,options:o,complete:ids.length===o.days,error:ids.length?'':'budget_too_low',partial:ids.length>0&&ids.length<o.days};
}
function cheaper(cart,products,settings,options={}){
 // No fallback to a product-only comparison: a delivery rule is required.
 if(!settings)return [];
 const before=quote(cart,products,settings,options);if(before.errors.length||before.promoError)return [];
 const out=[];
 for(const [id,qty] of Object.entries(cart)){
  const from=products.find(x=>x.id===id);if(!from)continue;
  const choices=[];
  for(const to of products){
   const replacement=substitute(cart,products,id,to.id);if(!replacement)continue;
   const after=quote(replacement.cart,products,settings,options);
   if(after.errors.length||after.promoError||after.subtotal<Number(settings.minOrder||0)||after.total>=before.total)continue;
   choices.push({from:id,to:to.id,qty:replacement.qty,cart:replacement.cart,saving:before.total-after.total,productSaving:before.subtotal-after.subtotal,before,after});
  }
  choices.sort((a,b)=>b.saving-a.saving||a.to.localeCompare(b.to));if(choices.length)out.push(choices[0]);
 }
 return out;
}
// Shared order eligibility. Recipe completion and eligibility for checkout are different facts.
function orderReadiness(cart,products,settings,options={}){
 const q=quote(cart,products,settings,options),rows=[];
 for(const [id,value] of Object.entries(cart&&typeof cart==='object'&&!Array.isArray(cart)?cart:{})){
  const product=products.find(p=>p.id===id),qty=Number(value);
  const available=product&&product.active?Math.max(0,Math.min(99,Math.floor(Number(product.stock)||0))):0;
  const issue=!product||!product.active?'unavailable':!int(qty,1,99)?'quantity':qty>available?'stock':'';
  rows.push({id,qty,product:product||null,available,issue});
 }
 const empty=rows.length===0,minimum=Number(settings.minOrder||0),shortMinimum=empty?0:Math.max(0,minimum-q.subtotal);
 const issues=[...q.errors];if(empty)issues.push('empty_cart');if(shortMinimum)issues.push('min_order');if(q.promoError)issues.push(q.promoError);
 return {quote:q,rows,issues:[...new Set(issues)],empty,minimum,shortMinimum,canOrder:!issues.length};
}
// An inverse patch returns removed lines only. Later edits (even of the same SKU) always win.
function removalPatch(cart,ids){return {kind:'restore-lines',entries:ids.filter(id=>Object.hasOwn(cart,id)).map(id=>({id,qty:Number(cart[id]),expected:0}))};}
function restoreRemoved(cart,patch,products){
 const next={...cart},restored=[],skipped=[];
 if(!patch||patch.kind!=='restore-lines'||!Array.isArray(patch.entries))return {cart:next,restored,skipped};
 for(const x of patch.entries){
  if(Number(next[x.id]||0)!==x.expected){skipped.push({id:x.id,reason:'changed'});continue;}
  const p=products.find(p=>p.id===x.id);
  if(!p||!p.active||!int(x.qty,1,99)||x.qty>Math.min(99,p.stock)){skipped.push({id:x.id,reason:'unavailable'});continue;}
  next[x.id]=x.qty;restored.push(x.id);
 }
 return {cart:next,restored,skipped};
}
const DRAFT_DAYS=7;
function readDraft(raw,type,now=Date.now()){
 if(!raw||typeof raw!=='object'||!Number.isFinite(raw.updatedAt)||raw.updatedAt>now+60000||now-raw.updatedAt>DRAFT_DAYS*86400000)return null;
 const str=(key,max)=>typeof raw[key]==='string'?raw[key].slice(0,max):'';
 if(type==='checkout')return {address:str('address',300),comment:str('comment',500),zone:str('zone',80),slot:str('slot',100),replacements:['ask','skip','similar'].includes(raw.replacements)?raw.replacements:'ask',updatedAt:raw.updatedAt};
 if(type==='support')return {text:str('text',3000),kind:['support','return'].includes(raw.kind)?raw.kind:'support',orderId:str('orderId',100),updatedAt:raw.updatedAt};
 return null;
}

return {MAX_MONEY,validMoney,businessDate,orderReadiness,removalPatch,restoreRemoved,DRAFT_DAYS,readDraft,localDate,validDate,pantryStatus,usablePantry,substitute,norm,int,clone,cleanCart,distance,search,quote,aggregate,parseRequest,parseExclusions,makePlan,cheaper};
});
