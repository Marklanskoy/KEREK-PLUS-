/* Startup watchdog: visible recovery instead of an eternal skeleton. */
window.KEREK_BOOT_DONE=false;
(function(){'use strict';let failed=false;
function show(){if(window.KEREK_BOOT_DONE||failed)return;failed=true;const box=document.getElementById('app');if(!box)return;const p=document.createElement('p');p.className='note';p.textContent='Запуск не завершился. Не очищайте данные браузера. Обновите файлы через страницу обновления; старые записи останутся для восстановления.';const a=document.createElement('a');a.className='btn primary';a.href='update.html';a.textContent='Открыть страницу обновления';box.append(p,a);}
window.addEventListener('error',e=>{if(!window.KEREK_BOOT_DONE&&!(e.target instanceof HTMLImageElement))show();});setTimeout(show,12000);
})();
