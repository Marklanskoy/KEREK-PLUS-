"""Render in a controlled about:blank harness (container Chromium blocks URL navigation)."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import base64
ROOT=Path(__file__).resolve().parents[1]
def load_page(page, initial_storage=None):
 page.route('https://images.unsplash.com/**',lambda r:r.abort())
 page.set_content('<!doctype html><html lang="ru"><head><meta name="viewport" content="width=device-width,initial-scale=1"></head><body><div id="app"></div><dialog id="modal" aria-labelledby="modal-title"></dialog><div id="toast" role="status"></div></body></html>')
 page.add_style_tag(content=(ROOT/'public/styles.css').read_text())
 page.evaluate('''() => {
 const store={}; Object.defineProperty(window,'localStorage',{value:{getItem:k=>store[k]??null,setItem:(k,v)=>store[k]=String(v),removeItem:k=>delete store[k]}});
 window.KEREK_STANDALONE=true;
 }''')
 page.evaluate('(entries)=>Object.entries(entries).forEach(([k,v])=>localStorage.setItem(k,v))',initial_storage or {})
 page.evaluate('(data)=>window.KEREK_ICON_DATA=data','data:image/svg+xml;base64,'+base64.b64encode((ROOT/'public/assets/icon.svg').read_bytes()).decode())
 for name in ['data','core','api','app']:page.add_script_tag(content=(ROOT/f'public/js/{name}.js').read_text())
 page.wait_for_selector('.hero',timeout=10000)
if __name__=='__main__':
 with sync_playwright() as p:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
  pg=b.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
  errors=[];pg.on('pageerror',lambda er:errors.append(str(er)))
  load_page(pg);pg.screenshot(path='/mnt/data/kerek-desktop-initial.png',full_page=True)
  pg.set_viewport_size({'width':390,'height':844});pg.screenshot(path='/mnt/data/kerek-mobile-initial.png',full_page=True)
  print('errors:',errors)
  b.close()
