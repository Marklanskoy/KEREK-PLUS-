"""Real Chromium DOM interactions, in-memory navigation harness; no live-provider claims.
The runner's enterprise policy blocks URL navigation, so HTML, scripts and CSS
are loaded into about:blank. Static shopping mode and photo fallbacks are tested.
"""
import json,os
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright,expect
from render_preview import load_page,ROOT

@pytest.fixture(scope='module')
def browser():
 with sync_playwright() as p:
  args={'headless':True,'args':['--no-sandbox']}
  if os.path.exists('/usr/bin/chromium'):args['executable_path']='/usr/bin/chromium'
  b=p.chromium.launch(**args)
  yield b
  b.close()
@pytest.fixture
def page(browser):
 p=browser.new_page(viewport={'width':1440,'height':1000});p.on('dialog',lambda d:d.accept());errors=[];p.on('pageerror',lambda er:errors.append(str(er)));load_page(p)
 yield p
 assert errors==[],errors
 p.close()
def act(p,action,extra=''):
 p.locator(f'[data-action="{action}"]{extra}:visible').first.click()
def nav(p,v):act(p,'nav',f'[data-view="{v}"]')
def state(p):return p.evaluate('JSON.parse(localStorage.getItem("kerek_v3"))')
def submit(p,form):p.locator(form+' button[type="submit"]').click()
def add(p,pid='0',n=1):
 nav(p,'catalog')
 for _ in range(n):act(p,'add',f'[data-id="{pid}"]')
def checkout(p):
 add(p,'0',2);nav(p,'cart');p.locator('[name="address"]').fill('Алматы, тестовый адрес 10');p.locator('[name="consent"]').check();p.locator('[form="checkout-form"]').click();expect(p.locator('main')).to_contain_text('LOCAL-')

def test_home_sections_and_demo_disclosure(page):
 expect(page.locator('.hero')).to_be_visible();expect(page.locator('.demo-bar')).to_contain_text('Реальных списаний');assert page.locator('.product').count()>5
@pytest.mark.parametrize('width',[320,390,768,1024,1440])
def test_no_horizontal_page_overflow(page,width):
 page.set_viewport_size({'width':width,'height':900})
 assert page.evaluate('document.documentElement.scrollWidth<=window.innerWidth+1')

def test_theme_and_language_are_real_and_persisted(page):
 act(page,'theme');assert state(page)['theme']=='dark';assert page.locator('body').get_attribute('data-theme')=='dark'
 act(page,'language');assert state(page)['language']=='kk';assert page.locator('html').get_attribute('lang')=='kk';expect(page.locator('.demo-bar')).to_contain_text('Сынақ дүкені')

def test_fuzzy_search_from_header(page):
 page.locator('#global-search').fill('молко');page.wait_for_timeout(350);assert page.locator('main .product').count()>=2;expect(page.locator('main')).to_contain_text('Молоко')

def test_cart_quantity_and_favorites(page):
 add(page,'0',2);assert state(page)['cart']['0']==2
 act(page,'favorite','[data-id="0"]');assert '0' in state(page)['favorites'];nav(page,'cart');assert page.locator('.cart-row').count()==1
 act(page,'minus','[data-id="0"]');assert state(page)['cart']['0']==1

def test_remove_undo_and_promo_do_not_lose_typed_address(page):
 add(page,'0',2);nav(page,'cart');page.locator('[name="address"]').fill('Алматы, Сохранённая 21');act(page,'remove','[data-id="0"]');act(page,'undo-cart');assert state(page)['cart']['0']==2
 expect(page.locator('[name="address"]')).to_have_value('Алматы, Сохранённая 21')
 page.locator('[name="promo"]').fill('KEREK10');submit(page,'[data-form="promo"]');assert state(page)['promo']=='KEREK10';expect(page.locator('.summary')).to_contain_text('138');expect(page.locator('[name="address"]')).to_have_value('Алматы, Сохранённая 21')

def test_invalid_coupon_is_not_accepted(page):
 add(page,'0',2);nav(page,'cart');page.locator('[name="promo"]').fill('INVALID');submit(page,'[data-form="promo"]');assert state(page)['promo']=='';expect(page.locator('#toast')).to_contain_text('Промокод не найден')

def test_local_order_create_repeat_cancel_is_explicitly_unpaid(page):
 checkout(page);o=state(page)['orders'][0];assert o['demo'] and o['paymentStatus']=='not_charged';assert state(page)['cart']=={}
 act(page,'repeat-order');assert state(page)['cart']['0']==2;nav(page,'orders');act(page,'cancel-order');assert state(page)['orders'][0]['status']=='cancelled'

def test_form_validation_blocks_order_without_address_or_consent(page):
 add(page,'0',2);nav(page,'cart');page.locator('[form="checkout-form"]').click();assert state(page)['orders']==[]

def test_recipe_one_click_whole_packages(page):
 nav(page,'recipes');act(page,'recipe');expect(page.locator('#modal')).to_be_visible();act(page,'add-recipe');assert len(state(page)['cart'])>=2;assert all(isinstance(v,int) for v in state(page)['cart'].values())

def test_pantry_default_milk_units_and_actual_quantity(page):
 nav(page,'pantry');expect(page.locator('select[name="unit"]')).to_have_value('ml');page.locator('[name="confirmed"]').check();submit(page,'[data-form="pantry"]');assert state(page)['pantry'][0]['unit']=='ml';assert state(page)['pantry'][0]['confirmed'];assert state(page)['pantry'][0]['amount']==500
 act(page,'edit-pantry');page.locator('#modal [name="amount"]').fill('250');page.locator('#modal [name="confirm"]').check();submit(page,'#modal form');assert state(page)['pantry'][0]['amount']==250

def test_budget_planner_makes_actionable_cart(page):
 nav(page,'smart');page.locator('[name="budget"]').fill('25000');page.locator('[name="people"]').fill('4');submit(page,'[data-form="plan"]');expect(page.locator('#plan-result')).to_contain_text('₸');act(page,'accept-plan');assert len(state(page)['cart'])>=3;expect(page.locator('main')).to_contain_text('Ваша корзина')

def test_request_parser_does_not_treat_days_as_people(page):
 nav(page,'smart');page.locator('#plan-request').fill('Недорогие завтраки на пять дней');act(page,'parse-request');expect(page.locator('[name="people"]')).to_have_value('2');expect(page.locator('[name="days"]')).to_have_value('5');expect(page.locator('[name="meal"]')).to_have_value('breakfast')

def test_support_local_ticket_is_not_sent_claim(page):
 nav(page,'support');page.locator('[name="text"]').fill('Подскажите, как изменить состав корзины?');submit(page,'[data-form="support"]');assert len(state(page)['tickets'])==1;expect(page.locator('#toast')).to_contain_text('не отправлено')

def test_profile_untrusted_html_is_escaped(page):
 nav(page,'profile');payload='<img src=x onerror="window.PWNED=1">';page.locator('[name="name"]').fill(payload);submit(page,'[data-form="profile"]');nav(page,'club');assert not page.evaluate('window.PWNED');expect(page.locator('.club-card')).to_contain_text(payload)

def test_logout_does_not_retain_pantry_or_personal_profile(page):
 nav(page,'pantry');page.locator('[name="confirmed"]').check();submit(page,'[data-form="pantry"]');nav(page,'profile');page.locator('[name="name"]').fill('Тестовый покупатель');submit(page,'[data-form="profile"]');act(page,'logout');s=state(page);assert s['name']=='' and s['pantry']==[] and s['orders']==[] and s['addresses']==[]

def test_import_original_basket_and_favorites_without_old_keys_destroyed(browser):
 p=browser.new_page();p.on('dialog',lambda d:d.accept());load_page(p,{'kerek_basket':'{"0":2,"5":1}','kerek_fav':'[0,5]','kerek_profile':'{"name":"Алия"}','kerek_pantry':'[5]'})
 s=state(p);assert s['cart']=={'0':2,'5':1};assert s['name']=='Алия';assert s['favorites']==['0','5'];assert s['pantry'][0]['confirmed'] is False;assert p.evaluate('localStorage.getItem("kerek_basket")') is not None;p.close()

def test_corrupt_storage_entries_are_filtered_without_crash(browser):
 p=browser.new_page();load_page(p,{'kerek_v3':json.dumps({'orders':[None,{'items':None}],'pantry':[None],'addresses':[None],'tickets':[1,None],'ledger':[None],'favorites':None,'cart':{'0':-1}})})
 s=state(p);assert s['orders']==[] and s['pantry']==[] and s['tickets']==[] and s['cart']=={};p.close()

def test_keyboard_modal_escape_closes_dialog(page):
 act(page,'address');expect(page.locator('#modal')).to_be_visible();page.keyboard.press('Escape');expect(page.locator('#modal')).not_to_be_visible()
