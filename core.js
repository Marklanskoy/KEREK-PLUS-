/* Pure, deterministic domain functions. No DOM, network or hidden AI prices. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.KerekCore=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
const norm=s=>String(s??'').toLowerCase().replace(/ё/g,'е').replace(/[^\p{L}\p{N}\s]/gu,' ').replace(/\s+/g,' ').trim();
const int=(v,min,max)=>Number.isInteger(Number(v))&&Number(v)>=min&&Number(v)<=max;
const clone=x=>JSON.parse(JSON.stringify(x));
function cleanCart(cart,products){const out={};if(!cart||typeof cart!=='object'||Array.isArray(cart))return out;for(const p of products){const n=Number(cart[p.id]);if(int(n,1,99)&&p.active&&p.stock>0)out[p.id]=Math.min(n,p.stock);}return out;}
function distance(a,b){a=norm(a);b=norm(b);let v=Array.from({length:b.length+1},(_,i)=>i);for(let i=0;i<a.length;i++){let w=[i+1];for(let j=0;j<b.length;j++)w[j+1]=Math.min(w[j]+1,v[j+1]+1,v[j]+(a[i]===b[j]?0:1));v=w;}return v[b.length];}
function search(products,query){const q=norm(query);if(!q)return {items:products,corrected:false};const words=q.split(' ');let direct=products.filter(p=>{let s=norm(p.name+' '+p.name_kk+' '+p.brand);return words.every(w=>s.includes(w));});if(direct.length)return {items:direct,corrected:false};return {items:products.filter(p=>{const ws=norm(p.name+' '+p.name_kk+' '+p.brand).split(' ');return words.every(w=>ws.some(x=>w.length>=4&&distance(x,w)<= (w.length>7?2:1)));}),corrected:true};}
function quote(cart,products,settings,{promo='',bonus=0,balance=0,zone='almaty'}={}){
 const errors=[],lines=[];let subtotal=0,savings=0;
 if(!cart||typeof cart!=='object'||Array.isArray(cart))return {errors:['invalid_cart'],lines:[],subtotal:0,discount:0,bonus:0,delivery:0,total:0,savings:0};
 for(const [id,qty] of Object.entries(cart)){
  const p=products.find(x=>x.id===id);
  if(!p||!p.active){errors.push('unknown_product:'+id);continue;}
  if(!int(qty,1,99)){errors.push('invalid_quantity:'+id);continue;}
  if(qty>p.stock)errors.push('stock:'+id);
  const amount=p.price*qty;subtotal+=amount;savings+=Math.max(0,p.oldPrice-p.price)*qty;lines.push({id,qty,name:p.name,name_kk:p.name_kk,price:p.price,amount});
 }
 let discount=0,promoError='';
 const code=String(promo).trim().toUpperCase();
 if(code){const p=settings.promos.find(p=>p.code===code&&p.active&&(!p.endsAt||p.endsAt>=new Date().toISOString().slice(0,10)));if(!p)promoError='promo_invalid';else if(subtotal<p.minSubtotal)promoError='promo_min';else discount=Math.min(p.maxDiscount,Math.floor(subtotal*p.percent/100));}
 const maxBonus=Math.max(0,Math.min(Math.floor(balance),Math.floor((subtotal-discount)*settings.maxBonusPercent/100)));
 const usedBonus=int(bonus,0,1e9)?Math.min(Number(bonus),maxBonus):0;
 const z=(settings.zones||[]).find(z=>z.id===zone&&z.enabled);
 if(lines.length&&!z)errors.push('zone_unavailable');
 const delivery=lines.length&&subtotal<settings.freeDeliveryFrom?(z?.fee??settings.deliveryFee):0;
 const total=Math.max(0,subtotal-discount-usedBonus)+delivery;
 return {lines,errors,subtotal,discount,bonus:usedBonus,maxBonus,delivery,total,savings:savings+discount+usedBonus,promoError,bonusEarned:Math.floor(Math.max(0,subtotal-discount-usedBonus)*settings.bonusRate/100),freeRemaining:Math.max(0,settings.freeDeliveryFrom-subtotal)};
}
function aggregate(recipeIds,people,recipes,products,pantry=[],overrides={}){
 const requirements={},byIngredient={};const missing=[];
 for(const rid of recipeIds){const r=recipes.find(r=>r.id===rid);if(!r){missing.push(rid);continue;}for(const i of r.ingredients){requirements[i.key]=(requirements[i.key]||0)+i.amount*people;byIngredient[i.key]=i.unit;}}
 const atHome={},today=new Date().toISOString().slice(0,10);
 for(const h of pantry){if(h.confirmed===false||h.expiresAt&&h.expiresAt<today||Number(h.amount)<=0||h.unit!==byIngredient[h.ingredient])continue;atHome[h.ingredient]=(atHome[h.ingredient]||0)+Number(h.amount);}
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
 const a=aggregate(ids,o.people,recipes,products,pantry);const q=quote(a.cart,products,settings);
 return {...a,quote:q,selected:ids,options:o,complete:ids.length===o.days,error:ids.length?'':'budget_too_low',partial:ids.length>0&&ids.length<o.days};
}
function cheaper(cart,products){const out=[];for(const [id,qty] of Object.entries(cart)){const p=products.find(x=>x.id===id);if(!p)continue;const needed=p.pack*qty;const choices=products.filter(x=>x.active&&x.id!==id&&x.ingredient===p.ingredient&&x.unit===p.unit).map(x=>({product:x,qty:Math.ceil(needed/x.pack)})).filter(x=>x.qty<=x.product.stock&&x.product.price*x.qty<p.price*qty).sort((a,b)=>a.product.price*a.qty-b.product.price*b.qty);if(choices.length)out.push({from:id,to:choices[0].product.id,qty:choices[0].qty,saving:p.price*qty-choices[0].product.price*choices[0].qty});}return out;}
return {norm,int,clone,cleanCart,distance,search,quote,aggregate,parseRequest,parseExclusions,makePlan,cheaper};
});
