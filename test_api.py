from pathlib import Path
from datetime import datetime,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
import base64,io,json,time,uuid
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from server.app import create_app,password_hash,utc
from server.db import dumps
from server.pricing import quote

@pytest.fixture
def client(tmp_path):
 app=create_app(tmp_path/'test.sqlite3')
 with app.state.db.connect(write=True) as db:
  for role in ['admin','manager']:
   db.execute('INSERT INTO users(id,username,password,role,created_at) VALUES(?,?,?,?,?)',(role,role,password_hash('Test-only-password-2026!'),role,utc()))
 with TestClient(app) as c:yield c

def login(c,phone='+77000000001',referral=''):
 r=c.post('/api/auth/request-code',json={'phone':phone});assert r.status_code==200,r.text
 d=r.json();r=c.post('/api/auth/verify',json={'challengeId':d['challengeId'],'code':d['demoCode'],'referral':referral});assert r.status_code==200,r.text
 c.headers['x-csrf-token']=r.json()['csrf'];return r.json()['user']
def admin(c,role='admin'):
 r=c.post('/api/auth/admin',json={'username':role,'password':'Test-only-password-2026!'});assert r.status_code==200,r.text
 c.headers['x-csrf-token']=r.json()['csrf'];return r.json()['user']
def order_body(c,cart=None,**kw):
 cart=cart or {'0':2,'1':1}
 inp=dict(cart=cart,promo='',bonus=0,zone='almaty');inp.update({k:v for k,v in kw.items() if k in inp})
 q=c.post('/api/quote',json=inp);assert q.status_code==200,q.text
 tomorrow=(datetime.now(timezone(timedelta(hours=5))).date()+timedelta(days=1)).isoformat()
 body=dict(**inp,address='Алматы, тестовая улица 10',slot=tomorrow+' 10:00–12:00',comment='',replacements='ask',payment='test',expectedTotal=q.json()['total'],idempotencyKey=uuid.uuid4().hex)
 body.update(kw);return body
def create_order(c,**kw):
 r=c.post('/api/orders',json=order_body(c,**kw));assert r.status_code==200,r.text;return r.json()
def stock(c,pid='0'):
 return next(p['stock'] for p in c.get('/api/bootstrap').json()['products'] if p['id']==pid)

def test_health_and_disabled_providers(client):
 d=client.get('/api/health').json();assert d['service']=='kerek' and d['mode']=='demo';assert not any(d['capabilities'].values())
def test_seed_preserves_original_ids(client):
 p=client.get('/api/bootstrap').json()['products'];assert len(p)==32;assert p[0]['id']=='0' and p[0]['ingredient']=='milk';assert p[13]['ingredient']=='carrot'
def test_session_cookie_is_httponly_samesite(client):
 login(client);c=client.cookies.get('kerek_session');assert c and len(c)>30
 # Explicitly inspect the response Set-Cookie header via a new login.
 r=client.post('/api/auth/admin',json={'username':'admin','password':'Test-only-password-2026!'});cookie=r.headers['set-cookie'];assert 'HttpOnly' in cookie and 'SameSite=strict' in cookie

def test_otp_replay_is_rejected(client):
 d=client.post('/api/auth/request-code',json={'phone':'+77000000001'}).json();b={'challengeId':d['challengeId'],'code':d['demoCode']};assert client.post('/api/auth/verify',json=b).status_code==200;assert client.post('/api/auth/verify',json=b).status_code==400

def test_failed_code_attempts_persist(client):
 d=client.post('/api/auth/request-code',json={'phone':'+77000000001'}).json();wrong='111111' if d['demoCode']!='111111' else '222222'
 for _ in range(5):assert client.post('/api/auth/verify',json={'challengeId':d['challengeId'],'code':wrong}).status_code==400
 r=client.post('/api/auth/verify',json={'challengeId':d['challengeId'],'code':d['demoCode']});assert r.status_code==400 and r.json()['detail']=='code_expired'

def test_expired_code(client):
 d=client.post('/api/auth/request-code',json={'phone':'+77000000001'}).json()
 with client.app.state.db.connect(write=True) as db:db.execute('UPDATE otp SET expires=?',(time.time()-10,))
 assert client.post('/api/auth/verify',json={'challengeId':d['challengeId'],'code':d['demoCode']}).status_code==400

def test_otp_rate_limit(client):
 for _ in range(3):assert client.post('/api/auth/request-code',json={'phone':'+77000000001'}).status_code==200
 assert client.post('/api/auth/request-code',json={'phone':'+77000000001'}).status_code==429

@pytest.mark.parametrize('phone',['123','+18005550100','<script>','+7 123'])
def test_phone_validation(client,phone):assert client.post('/api/auth/request-code',json={'phone':phone}).status_code==422

def test_guest_cannot_read_admin(client):assert client.get('/api/admin/overview').status_code==401

def test_customer_cannot_read_admin(client):login(client);assert client.get('/api/admin/overview').status_code==403

def test_csrf_protection(client):
 login(client);client.headers['x-csrf-token']='bad';assert client.post('/api/support',json={'text':'Hello support','kind':'support'}).status_code==403

def test_cross_origin_rejected(client):
 assert client.post('/api/auth/request-code',json={'phone':'+77000000001'},headers={'origin':'https://evil.invalid'}).status_code==403

def test_non_json_rejected(client):assert client.post('/api/auth/request-code',content='phone=1',headers={'content-type':'text/plain'}).status_code==415

def test_security_headers(client):
 r=client.get('/');assert r.status_code==200;assert r.headers['x-frame-options']=='DENY';assert "script-src 'self'" in r.headers['content-security-policy']

def test_me_does_not_expose_password_or_session(client):
 login(client);d=client.get('/api/me').json();assert not {'password','token_hash','csrf_hash'}&set(d)

def test_profile_cannot_escalate_role(client):
 login(client);assert client.put('/api/me',json={'name':'test','role':'admin'}).status_code==422;assert client.get('/api/me').json()['role']=='customer'

def test_server_rejects_forged_total(client):
 login(client);body=order_body(client);body['expectedTotal']=1;before=stock(client);r=client.post('/api/orders',json=body);assert r.status_code==409;assert stock(client)==before;assert client.get('/api/orders').json()==[]

@pytest.mark.parametrize('qty',[0,-1,1.5,True,'2',100])
def test_invalid_cart_quantities(client,qty):
 login(client);r=client.post('/api/quote',json={'cart':{'0':qty}});assert r.status_code in [409,422]

def test_rejects_unknown_product(client):
 assert client.post('/api/quote',json={'cart':{'does-not-exist':1}}).status_code==409

def test_empty_order(client):
 login(client);b=order_body(client);b['cart']={};b['expectedTotal']=0;assert client.post('/api/orders',json=b).status_code==400

def test_old_price_not_accepted_from_client(client):
 login(client);b=order_body(client);b['price']=1;assert client.post('/api/orders',json=b).status_code==422

def test_idempotent_order_and_inventory(client):
 login(client);before=stock(client);b=order_body(client);a=client.post('/api/orders',json=b);z=client.post('/api/orders',json=b);assert a.status_code==z.status_code==200;assert a.json()['id']==z.json()['id'];assert stock(client)==before-2;assert len(client.get('/api/orders').json())==1

def test_idempotency_key_cannot_change_payload(client):
 login(client);b=order_body(client);assert client.post('/api/orders',json=b).status_code==200;b['comment']='another';assert client.post('/api/orders',json=b).status_code==409

def test_order_remains_unpaid_demo(client):
 login(client);o=create_order(client);assert o['demo'] is True and o['paymentStatus']=='not_charged';assert o['status']=='created'

def test_order_payment_provider_unavailable(client):
 login(client);assert client.post('/api/payments/session',json={}).status_code==503

def test_tracking_unavailable_not_fake_coordinates(client):
 login(client);o=create_order(client);assert client.get('/api/orders/'+o['id']+'/tracking').status_code==503

def test_cancel_restores_stock_exactly_once(client):
 login(client);before=stock(client);o=create_order(client);assert client.post('/api/orders/'+o['id']+'/cancel',json={}).status_code==200;assert stock(client)==before;assert client.post('/api/orders/'+o['id']+'/cancel',json={}).status_code==409;assert stock(client)==before

def test_another_user_cannot_cancel_or_attach_order(client):
 login(client);o=create_order(client)
 with TestClient(client.app) as other:
  login(other,'+77000000002');assert other.get('/api/orders').json()==[]
  assert other.post('/api/orders/'+o['id']+'/cancel',json={}).status_code==404
  assert other.post('/api/support',json={'text':'Return this order','kind':'return','orderId':o['id']}).status_code==404

def test_promo_cap_and_free_delivery(client):
 r=client.post('/api/quote',json={'cart':{'10':8},'promo':'KEREK10'}).json();assert r['discount']==2000 and r['delivery']==0

def test_promo_threshold(client):
 r=client.post('/api/quote',json={'cart':{'0':1},'promo':'KEREK10'}).json();assert r['promoError']=='promo_min' and r['discount']==0

def test_minimum_order(client):
 login(client);b=order_body(client,cart={'2':1});assert client.post('/api/orders',json=b).status_code==400

def test_unknown_zone(client):assert client.post('/api/quote',json={'cart':{'0':2},'zone':'moon'}).status_code==409

def test_invalid_delivery_slot(client):
 login(client);b=order_body(client,slot='2020-01-01 10:00–12:00');assert client.post('/api/orders',json=b).status_code==400

def test_stock_shortage_transaction_has_no_partial_reservation(client):
 login(client);before=stock(client);b=order_body(client);b['cart']={'0':2,'10':99};r=client.post('/api/orders',json=b);assert r.status_code==409;assert stock(client)==before

def test_manager_limited_permissions(client):
 admin(client,'manager');assert client.get('/api/admin/overview').status_code==200;assert client.get('/api/admin/audit').status_code==403
 b=client.get('/api/bootstrap').json();assert client.put('/api/admin/settings',json=b['settings']).status_code==403
 p=b['products'][0];p['stock']=99;assert client.put('/api/admin/products/0',json=p).status_code==200

def test_admin_product_validation_and_audit(client):
 admin(client);p=client.get('/api/bootstrap').json()['products'][0];p['price']=650;p['oldPrice']=790;r=client.put('/api/admin/products/0',json=p);assert r.status_code==200;assert client.get('/api/admin/audit').json()[0]['action']=='product.save';p['price']=-1;assert client.put('/api/admin/products/0',json=p).status_code==422

def test_product_js_image_url_rejected(client):
 admin(client);p=client.get('/api/bootstrap').json()['products'][0];p['image']='javascript:alert(1)';assert client.put('/api/admin/products/0',json=p).status_code==422

def test_settings_authoritatively_change_delivery(client):
 admin(client);s=client.get('/api/bootstrap').json()['settings'];s['zones'][0]['fee']=123;s['bonusRate']=4;assert client.put('/api/admin/settings',json=s).status_code==200;r=client.post('/api/quote',json={'cart':{'0':2}}).json();assert r['delivery']==123 and r['bonusEarned']==55

def test_cannot_remove_category_in_use(client):
 admin(client);cats=client.get('/api/bootstrap').json()['categories'];cats=[c for c in cats if c['id']!='dairy'];assert client.put('/api/admin/categories',json={'categories':cats}).status_code==409

def test_image_upload_validates_bytes(client):
 admin(client);assert client.post('/api/admin/upload',json={'data':base64.b64encode(b'<svg><script>bad</script></svg>').decode()}).status_code==400
 im=Image.new('RGB',(10,10));buf=io.BytesIO();im.save(buf,'PNG');r=client.post('/api/admin/upload',json={'data':base64.b64encode(buf.getvalue()).decode()});assert r.status_code==200;path=r.json()['image'];assert path.endswith('.webp');assert client.get('/'+path).status_code==200

def test_support_reply_saved_and_visible(client):
 login(client);r=client.post('/api/support',json={'text':'Please help with my test','kind':'support'});assert r.status_code==200
 with TestClient(client.app) as staff:
  admin(staff);tid=r.json()['id'];assert staff.put('/api/admin/tickets/'+tid,json={'reply':'Ответ сохранён','status':'answered'}).status_code==200
 assert client.get('/api/support').json()[0]['reply']=='Ответ сохранён'

def test_invalid_order_stage_rejected(client):
 login(client);o=create_order(client)
 with TestClient(client.app) as staff:
  admin(staff);assert staff.post('/api/admin/orders/'+o['id']+'/status',json={'status':'delivered'}).status_code==409

def complete(c,oid):
 for s in ['assembling','ready','delivering','delivered']:
  r=c.post('/api/admin/orders/'+oid+'/status',json={'status':s});assert r.status_code==200,r.text

def test_loyalty_awarded_once_and_redeem_cancel_refund(client):
 login(client);o=create_order(client)
 assert client.get('/api/me').json()['balance']==0
 with TestClient(client.app) as staff:
  admin(staff);complete(staff,o['id']);assert staff.post('/api/admin/orders/'+o['id']+'/status',json={'status':'delivered'}).status_code==200
 balance=client.get('/api/me').json()['balance'];assert balance==o['quote']['bonusEarned']
 assert len(client.get('/api/me').json()['ledger'])==1
 second=create_order(client,bonus=balance);assert client.get('/api/me').json()['balance']==0
 assert client.post('/api/orders/'+second['id']+'/cancel',json={}).status_code==200;assert client.get('/api/me').json()['balance']==balance

def test_referral_once_on_first_completed_order(client):
 u=login(client)
 with TestClient(client.app) as other, TestClient(client.app) as staff:
  login(other,'+77000000002',u['referralCode']);admin(staff)
  for _ in range(2):o=create_order(other);complete(staff,o['id'])
 assert client.get('/api/me').json()['balance']==300

def test_delete_data_requires_no_active_orders_and_anonymizes(client):
 login(client);o=create_order(client);assert client.request('DELETE','/api/me',json={'confirm':'DELETE'}).status_code==409
 assert client.post('/api/orders/'+o['id']+'/cancel',json={}).status_code==200
 assert client.request('DELETE','/api/me',json={'confirm':'DELETE'}).status_code==200
 assert client.get('/api/me').status_code==401
 with client.app.state.db.connect() as db:
  saved=json.loads(db.execute('SELECT data FROM orders WHERE id=?',(o['id'],)).fetchone()[0]);assert saved['address']=='[удалено]';assert saved['comment']==''

def test_export_excludes_secrets(client):
 login(client);r=client.get('/api/me/export').json();assert 'user' in r and 'orders' in r and 'sessions' not in r;assert 'password' not in r['user']

def test_expired_session_is_rejected(client):
 login(client)
 with client.app.state.db.connect(write=True) as db:db.execute('UPDATE sessions SET expires=?',(time.time()-1,))
 assert client.get('/api/me').status_code==401

def test_production_mode_fails_closed(tmp_path):
 with pytest.raises(RuntimeError):create_app(tmp_path/'never.sqlite3',mode='live')

def test_concurrent_orders_do_not_oversell(client):
 # One remaining unit; two different customers race for it.
 with client.app.state.db.connect(write=True) as db:
  p=json.loads(db.execute('SELECT data FROM products WHERE id="0"').fetchone()[0]);p['stock']=1;db.execute('UPDATE products SET data=? WHERE id="0"',(dumps(p),))
  s=client.app.state.db.config(db,'settings');s['minOrder']=0;db.execute('UPDATE config SET data=? WHERE key="settings"',(dumps(s),))
 with TestClient(client.app) as a,TestClient(client.app) as b:
  login(a,'+77000000003');login(b,'+77000000004');bodies=[order_body(c,cart={'0':1}) for c in [a,b]]
  def buy(pair):c,payload=pair;return c.post('/api/orders',json=payload).status_code
  with ThreadPoolExecutor(2) as pool:results=list(pool.map(buy,[(a,bodies[0]),(b,bodies[1])]))
  assert sorted(results)==[200,409]
 assert stock(client)==0

@pytest.mark.parametrize('slots',[['25:00–26:00'],['15:00–14:00'],['10:00–12:00','11:00–13:00'],['10:00–12:00','10:00–12:00']])
def test_invalid_slot_configuration_rejected(client,slots):
 admin(client);s=client.get('/api/bootstrap').json()['settings'];s['slots']=slots;assert client.put('/api/admin/settings',json=s).status_code==422

def test_duplicate_coupon_configuration_rejected(client):
 admin(client);s=client.get('/api/bootstrap').json()['settings'];s['promos'].append(s['promos'][0]);assert client.put('/api/admin/settings',json=s).status_code==422

def test_coupon_expiry_must_be_real_date(client):
 admin(client);s=client.get('/api/bootstrap').json()['settings'];s['promos'][0]['endsAt']='2027-99-99';assert client.put('/api/admin/settings',json=s).status_code==422
