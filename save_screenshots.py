from pathlib import Path
import os
from playwright.sync_api import sync_playwright
from render_preview import ROOT,load_page
OUT=ROOT/'docs/screenshots';OUT.mkdir(parents=True,exist_ok=True)
def act(p,a,more=''):p.locator(f'[data-action="{a}"]{more}:visible').first.click()
def nav(p,v):act(p,'nav',f'[data-view="{v}"]')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1);page.on('dialog',lambda d:d.accept());load_page(page)
 page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
 page.screenshot(path='/mnt/data/KEREK_preview.png')
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
 page.set_viewport_size({'width':1440,'height':1050});nav(page,'smart');page.locator('[data-form="plan"] button[type=submit]').click();page.evaluate("document.documentElement.style.scrollBehavior='auto';window.scrollTo(0,0)");page.wait_for_timeout(200);page.screenshot(path=str(OUT/'planner.png'),full_page=True)
 act(page,'accept-plan');page.locator('[name="address"]').fill('Алматы, тестовый адрес');page.evaluate('window.scrollTo(0,0)');page.wait_for_timeout(200);page.screenshot(path=str(OUT/'cart.png'),full_page=True)
 nav(page,'home');act(page,'theme');page.screenshot(path=str(OUT/'dark.png'),full_page=True)
 b.close()
print('Saved five actual UI screenshots, using offline illustration fallbacks.')
