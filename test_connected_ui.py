"""Actual UI + FastAPI integration via a test bridge, not a live HTTP browser session.
The bridge exists ONLY in this test file. It is not shipped in public JS.
"""
import base64,json
from pathlib import Path
import pytest
from playwright.sync_api import expect
from render_preview import ROOT
from test_api import client,login,create_order,admin
from test_ui import browser,act,nav,submit

def connected_page(browser,client,is_admin=False):
 page=browser.new_page(viewport={'width':1440,'height':1000});page.on('dialog',lambda d:d.accept());page.route('https://images.unsplash.com/**',lambda r:r.abort())
 page.set_content('<html><body><div id="'+('admin' if is_admin else 'app')+'"></div><dialog id="'+('admin-modal' if is_admin else 'modal')+'"></dialog><div id="toast"></div></body></html>')
 page.add_style_tag(content=(ROOT/'public/styles.css').read_text())
 page.evaluate('''()=>{const s={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>s[k]??null,setItem:(k,v)=>s[k]=String(v),removeItem:k=>delete s[k]}});}''')
 def bridge(payload):
  opts={}
  if payload.get('body') is not None:opts['json']=payload['body']
  if payload.get('csrf'):opts['headers']={'x-csrf-token':payload['csrf']}
  r=client.request(payload.get('method','GET'),'/api/'+payload['path'],**opts)
  return {'status':r.status_code,'data':r.json()}
 page.expose_function('testApiBridge',bridge)
 page.evaluate('''()=>{let csrf='';window.KerekAPI={enabled:true,setSession:v=>{csrf=v||''},async init(){return await this.request('bootstrap')},async request(path,opts={}){const r=await window.testApiBridge({path,...opts,csrf});if(r.status>=400){const e=new Error(typeof r.data.detail==='string'?r.data.detail:'validation_error');e.status=r.status;throw e;}return r.data;}};}''')
 page.evaluate('(v)=>window.KEREK_ICON_DATA=v','data:image/svg+xml;base64,'+base64.b64encode((ROOT/'public/assets/icon.svg').read_bytes()).decode())
 for name in (['admin'] if is_admin else ['data','core','app']):page.add_script_tag(content=(ROOT/f'public/js/{name}.js').read_text())
 page.set_default_timeout(5000)
 page.wait_for_selector('main',timeout=10000)
 return page

def sign_admin(p):
 p.locator('[name="username"]').fill('admin');p.locator('[name="password"]').fill('Test-only-password-2026!');submit(p,'form');expect(p.locator('main h1')).to_have_text('Управление магазином')

def test_connected_storefront_phone_login_checkout_and_server_persistence(browser,client):
 p=connected_page(browser,client);p.set_default_timeout(4000);nav(p,'profile');act(p,'login');p.locator('#modal [name="phone"]').fill('+77000000001');p.locator('#modal input[type=checkbox]').check();submit(p,'#modal form')
 code=p.locator('#demo-code').inner_text();p.locator('[name="code"]').fill(code);submit(p,'#modal form');expect(p.locator('#modal')).not_to_be_visible()
 nav(p,'catalog');act(p,'add','[data-id="0"]');act(p,'add','[data-id="0"]');nav(p,'cart');p.locator('[name="address"]').fill('Алматы, тестовая улица 20');p.locator('[name="consent"]').check();p.locator('[form="checkout-form"]').click()
 expect(p.locator('.order-card')).to_have_count(1);rows=client.get('/api/orders').json();assert len(rows)==1 and rows[0]['paymentStatus']=='not_charged';assert rows[0]['quote']['total']==2370
 p.close()

def test_admin_ui_edits_products_and_audit_is_persisted(browser,client):
 p=connected_page(browser,client,True);sign_admin(p);act(p,'tab','[data-id="products"]');act(p,'edit-product','[data-id="0"]')
 p.locator('#admin-modal [name="price"]').fill('701');p.locator('#admin-modal [name="stock"]').fill('33');submit(p,'#admin-modal form');expect(p.locator('#admin-modal')).not_to_be_visible()
 product=next(x for x in client.get('/api/bootstrap').json()['products'] if x['id']=='0');assert product['price']==701 and product['stock']==33
 act(p,'tab','[data-id="audit"]');expect(p.locator('main')).to_contain_text('product');p.close()

def test_admin_ui_order_progresses_only_after_explicit_manager_action(browser,client):
 login(client);o=create_order(client);client.cookies.clear();client.headers.pop('x-csrf-token',None)
 p=connected_page(browser,client,True);sign_admin(p);act(p,'tab','[data-id="orders"]');act(p,'order');act(p,'order-status','[data-status="assembling"]')
 expect(p.locator('#admin-modal')).to_contain_text('Собирается');overview=client.get('/api/admin/overview',headers={'x-csrf-token':'not-needed-for-get'}).json();assert overview['orders'][0]['status']=='assembling';p.close()

def test_admin_ui_rules_persist_to_live_test_catalog(browser,client):
 p=connected_page(browser,client,True);sign_admin(p);act(p,'tab','[data-id="settings"]');p.locator('[name="bonusRate"]').fill('4');submit(p,'[data-form="settings"]');expect(p.locator('#toast')).to_contain_text('Правила сохранены');assert client.get('/api/bootstrap').json()['settings']['bonusRate']==4;p.close()
