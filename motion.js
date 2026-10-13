/* KEREK PLUS 3.6.0 — motion layer only. No purchases, storage writes, network or timers holding navigation. */
(function(){'use strict';
 const root=document.getElementById('app');
 if(!root)return;
 const reduced=()=>typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
 const canMove=()=>!reduced()&&document.visibilityState!=='hidden';
 const clock=()=>typeof performance!=='undefined'?performance.now():Date.now();
 let lastView='',lastGrid='',initialShown=false,pending=null,frame=0,lastSpark=0;
 const stats={routes:0,lists:0,cart:0,favorites:0,skipped:0};
 function animate(el,frames,options){
  if(!el||!canMove()||typeof el.animate!=='function'){stats.skipped++;return null;}
  try{return el.animate(frames,{fill:'none',...options});}catch{return null;}
 }
 function lift(el,delay=0,offset=8,duration=310){
  return animate(el,[{opacity:.62,transform:`translate3d(0,${offset}px,0)`},{opacity:1,transform:'translate3d(0,0,0)'}],{duration,delay,easing:'cubic-bezier(.2,.8,.2,1)'});
 }
 function routeIn(view,first=false){
  if(!canMove())return;
  const main=root.querySelector('main#main');if(!main)return;
  // Transforming <main> on the cart route would reposition its fixed checkout dock.
  if(view==='cart')animate(main,[{opacity:.62},{opacity:1}],{duration:260,easing:'ease-out'});
  else lift(main,0,first?11:9,first?380:300);stats.routes++;
  const candidates=main.querySelectorAll('.product, .category-tile, .recipe, .guide-step');
  // Animate only content near the visible viewport; no hidden content, delayed taps or huge stagger queues.
  let count=0;
  for(const el of candidates){if(count>=8)break;const rect=el.getBoundingClientRect();if(rect.top>innerHeight+80||rect.bottom<0)continue;lift(el,70+count*24,8,270);count++;}
  const active=document.querySelector('.bottom-nav button.active svg, .header-nav .active svg');
  animate(active,[{transform:'translateY(3px) scale(.91)'},{transform:'translateY(0) scale(1)'}],{duration:260,easing:'cubic-bezier(.2,.8,.2,1)'});
  if(view==='cart')lift(root.querySelector('.cart-dock'),70,12,300);
 }
 function gridSignature(view){
  if(view!=='catalog')return '';
  const els=root.querySelectorAll('.catalog-main .product[data-product]');
  return [...els].slice(0,100).map(el=>el.getAttribute('data-product')).join(',');
 }
 function gridRefresh(){
  if(!canMove())return;
  const els=root.querySelectorAll('.catalog-main .product');
  let i=0;for(const el of els){if(i>=8)break;const r=el.getBoundingClientRect();if(r.top>innerHeight+55||r.bottom<0)continue;lift(el,i++*20,5,220);}stats.lists++;
 }
 function pulse(el){animate(el,[{transform:'scale(.94)'},{transform:'scale(1.075)',offset:.52},{transform:'scale(1)'}],{duration:300,easing:'cubic-bezier(.2,.8,.2,1)'});}
 function playCart(p,view){
  const product=String(p.id);
  const qty=[...root.querySelectorAll('.qty')].find(x=>[...x.querySelectorAll('[data-id]')].some(b=>b.dataset.id===product))?.querySelector('span');
  if(qty)pulse(qty);
  for(const el of document.querySelectorAll('.nav-badge,.count'))pulse(el);
  const target=document.querySelector('.bottom-nav button[data-view="cart"], .header [data-view="cart"]');
  if(!p.rect||!target||!canMove()||view==='cart'||clock()-lastSpark<320)return;
  const end=target.getBoundingClientRect();if(!end.width)return;
  const fromX=p.rect.left+p.rect.width/2,fromY=p.rect.top+p.rect.height/2;
  const dx=end.left+end.width/2-fromX,dy=end.top+end.height/2-fromY;
  if(Math.hypot(dx,dy)<55||Math.hypot(dx,dy)>1400)return;
  lastSpark=clock();const dot=document.createElement('span');dot.className='km-cart-orb';dot.setAttribute('aria-hidden','true');
  dot.style.left=fromX+'px';dot.style.top=fromY+'px';document.body.append(dot);
  const a=animate(dot,[{opacity:0,transform:'translate3d(0,0,0) scale(.45)'},{opacity:.95,transform:`translate3d(${dx*.3}px,${dy*.25-12}px,0) scale(1)`,offset:.27},{opacity:0,transform:`translate3d(${dx}px,${dy}px,0) scale(.3)`}],{duration:450,easing:'cubic-bezier(.3,.05,.3,1)'});
  if(a){a.finished.catch(()=>{}).then(()=>dot.remove());}else dot.remove();
 }
 function feedback(p,view){
  if(!p||clock()-p.time>1200)return;
  const S=window.KerekApp?.state;if(!S)return;
  if(p.kind==='cart'){
   const now=Number(S.cart?.[p.id]||0);
   if(now===p.before+1||p.action==='minus'&&now===p.before-1){stats.cart++;playCart({...p,id:p.id},view);}
  }else if(p.kind==='favorite'){
   const isFavorite=S.favorites?.some(x=>String(x)===p.id)===true;
   if(isFavorite!==p.before){
    stats.favorites++;const b=[...root.querySelectorAll('[data-action="favorite"]')].find(x=>x.dataset.id===p.id);
    pulse(b?.querySelector('svg')||b);
   }
  }
 }
 function scan(){
  frame=0;
  const view=document.body.dataset.view||window.KerekApp?.view?.view||'';
  if(!view)return;
  const fresh=!lastView||view!==lastView;
  const prevView=lastView,grid=gridSignature(view),listChanged=view==='catalog'&&prevView==='catalog'&&lastGrid!==grid;
  lastView=view;lastGrid=grid;
  const p=pending;pending=null;
  if(document.body.classList.contains('kerek-starting')||!window.KEREK_BOOT_DONE)return;
  if(fresh&&initialShown)routeIn(view);
  else if(listChanged)gridRefresh();
  if(p)feedback(p,view);
  }
 function schedule(){if(frame)return;frame=requestAnimationFrame(scan);}
 const observer=new MutationObserver(schedule);observer.observe(root,{childList:true});
 // Capture click before the app handles it. Feedback only runs if the persisted state actually changes.
 document.addEventListener('click',e=>{
  const el=e.target?.closest?.('[data-action]');if(!el||el.disabled)return;
  const a=el.dataset.action,id=String(el.dataset.id||''),S=window.KerekApp?.state;
  if(!S||!id)return;
  if(a==='add'||a==='minus')pending={kind:'cart',action:a,id,before:Number(S.cart?.[id]||0),rect:(()=>{const r=el.getBoundingClientRect();return {left:r.left,top:r.top,width:r.width,height:r.height};})(),time:clock()};
  else if(a==='favorite')pending={kind:'favorite',id,before:S.favorites?.some(x=>String(x)===id)===true,time:clock()};
 },true);
 function firstReveal(){
  if(initialShown)return;initialShown=true;
  // Splash fades only once the real app is ready; motion stays decorative and can be skipped instantly.
  const view=document.body.dataset.view||lastView||'home';
  if(document.visibilityState!=='hidden')requestAnimationFrame(()=>routeIn(view,true));
 }
 // Modals and buttons use CSS only; neither touches focus management or form submission.
 window.KerekMotion=Object.freeze({firstReveal,get stats(){return {...stats};},get reduced(){return reduced();}});
})();
