/* KEREK PLUS 3.5: actual startup readiness + polished entry. No financial/product data changed. */
window.KEREK_BOOT_DONE=false;
(function(){'use strict';
 let state='loading',watchdog=null,waiter=null,cleanupTimer=null;
 const started=typeof performance!=='undefined'?performance.now():Date.now();
 const root=()=>document.getElementById('kerek-splash');
 const app=()=>document.getElementById('app')||document.getElementById('admin');
 const phrases={records:['Открываем ваши списки…','Тізімдер ашылуда…'],catalog:['Подготавливаем каталог…','Каталог дайындалуда…'],ready:['Всё готово','Барлығы дайын']};
 const reduce=()=>typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches;
 function stage(key){if(state==='failed'||state==='closed')return;const t=document.getElementById('splash-status');if(t&&phrases[key])t.textContent=phrases[key][document.documentElement.lang==='kk'?1:0];}
 function cleanup(){clearTimeout(watchdog);clearTimeout(waiter);clearTimeout(cleanupTimer);const box=app();if(box)box.removeAttribute('aria-busy');document.body.classList.remove('kerek-starting');}
 function fail(){if(state==='closed'||state==='failed')return;state='failed';cleanup();root()?.remove();}
 function completeExit(){const el=root();el?.remove();cleanup();state='closed';}
 function exit(){if(state!=='ready')return;const el=root();if(!el){completeExit();return;}
  el.setAttribute('aria-hidden','true');el.style.pointerEvents='none';document.body.classList.remove('kerek-starting');
  if(reduce()){completeExit();return;}
  // Reveal the rendered page under the fading splash. A listener plus timeout
  // prevents the overlay getting stuck when backgrounded or transitions disabled.
  const done=()=>completeExit();el.addEventListener('transitionend',e=>{if(e.target===el&&e.propertyName==='opacity')done();},{once:true});
  requestAnimationFrame(()=>el.classList.add('splash-leaving'));
  cleanupTimer=setTimeout(done,550);
 }
 function finish(){if(state!=='loading')return;state='ready';clearTimeout(watchdog);stage('ready');root()?.classList.add('splash-ready');
  // A brief, real entrance beat; never invent a progress percent. Immediate
  // on reduced-motion systems. Slow actual loading never gets an extra wait.
  const elapsed=(typeof performance!=='undefined'?performance.now():Date.now())-started;
  const remaining=reduce()?0:Math.max(0,950-elapsed);
  if(remaining)waiter=setTimeout(exit,remaining);else exit();
 }
 function showFailure(){if(window.KEREK_BOOT_DONE||state!=='loading')return;fail();const box=app();if(!box)return;
  const panel=document.createElement('section');panel.className='boot brand-recovery';
  const image=document.createElement('img');image.src=window.KEREK_ICON_DATA||'icon-ref-192-350.png';image.alt='KEREK PLUS';image.className='brand-recovery-icon';
  const title=document.createElement('h1');title.textContent='KEREK PLUS';
  const p=document.createElement('p');p.className='note';p.textContent='Запуск не завершился. Не очищайте данные браузера. Проверьте подключение и обновите файлы; ваши записи не удаляются.';
  const a=document.createElement('a');a.className='btn primary';a.href='update.html';a.textContent='Открыть страницу обновления';
  panel.append(image,title,p,a);box.append(panel);
 }
 window.KerekSplash=Object.freeze({stage,finish,fail});
 window.addEventListener('error',e=>{if(!window.KEREK_BOOT_DONE&&!(e.target instanceof HTMLImageElement))showFailure();});
 window.addEventListener('unhandledrejection',()=>{if(!window.KEREK_BOOT_DONE)showFailure();});
 watchdog=setTimeout(showFailure,12000);
 stage('records');
})();
