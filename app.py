"""KEREK 3.0 reference backend. All seeded goods and orders are explicitly DEMO.
Run: python -m uvicorn server.app:app --host 127.0.0.1 --port 8000
Production mode intentionally fails closed until real integrations are implemented.
"""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,secrets,hashlib,hmac,time,io,base64,uuid
from fastapi import FastAPI,HTTPException,Request,Response
from fastapi.responses import JSONResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from PIL import Image,UnidentifiedImageError
from .db import Database,dumps
from .pricing import quote
from .providers import CAPABILITIES
from .models import *

ROOT=Path(__file__).resolve().parents[1]
SEED=json.loads((ROOT/'server/seed.json').read_text('utf-8'))
def utc():return datetime.now(timezone.utc).isoformat()
def digest(v):return hashlib.sha256(v.encode()).hexdigest()
def password_hash(password):
 salt=secrets.token_hex(16)
 return salt+':'+hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()
def verify_password(password,stored):
 try:
  salt,value=stored.split(':');return hmac.compare_digest(value,hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex())
 except (ValueError,TypeError,AttributeError):return False

def create_app(db_path=None,mode=None):
 mode=mode or os.getenv('KEREK_MODE','demo')
 if mode!='demo':raise RuntimeError('Live mode is disabled: implement verified SMS, payments, fulfilment, supplier data and complete release checks first.')
 database=Database(db_path or os.getenv('KEREK_DB',str(ROOT/'server/data/kerek.sqlite3')),SEED)
 app=FastAPI(title='KEREK API',version='3.0.0',docs_url='/api/docs',openapi_url='/api/openapi.json',redoc_url=None)
 app.state.db=database
 allowed=os.getenv('KEREK_ALLOWED_HOSTS','localhost,127.0.0.1,testserver').split(',')
 app.add_middleware(TrustedHostMiddleware,allowed_hosts=allowed)
 secure=os.getenv('KEREK_SECURE_COOKIES','0')=='1'

 def session(req):
  token=req.cookies.get('kerek_session','')
  if not token:return None
  with database.connect() as db:
   s=db.execute('SELECT s.*,u.role,u.phone,u.username,u.state,u.balance,u.referral_code,u.referred_by FROM sessions s JOIN users u ON s.user_id=u.id WHERE token_hash=? AND expires>?',(digest(token),time.time())).fetchone()
   return dict(s) if s and s['role']!='deleted' else None
 def require(req,roles=None):
  s=session(req)
  if not s:raise HTTPException(401,'auth_required')
  if roles and s['role'] not in roles:raise HTTPException(403,'forbidden')
  return s
 def audit(db,actor,action,target,detail=''):
  db.execute('INSERT INTO audit(actor,action,target,detail,created_at) VALUES(?,?,?,?,?)',(actor,action,target,detail,utc()))
 def rate(bucket,maximum,window):
  with database.connect(write=True) as db:
   db.execute('DELETE FROM limits WHERE ts<?',(time.time()-86400,))
   n=db.execute('SELECT COUNT(*) FROM limits WHERE bucket=? AND ts>?',(bucket,time.time()-window)).fetchone()[0]
   if n>=maximum:raise HTTPException(429,'too_many_attempts')
   db.execute('INSERT INTO limits VALUES(?,?)',(bucket,time.time()))
 def ip(req):return req.client.host if req.client else 'unknown'
 def signin(response,user_id):
  token=secrets.token_urlsafe(40);csrf=secrets.token_urlsafe(32)
  with database.connect(write=True) as db:
   db.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
   db.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest(token),user_id,digest(csrf),time.time()+3600*24*7))
  response.set_cookie('kerek_session',token,httponly=True,secure=secure,samesite='strict',max_age=604800,path='/')
  return csrf
 def snapshot(db,uid):
  u=db.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
  return dict(id=uid,role=u['role'],phone=u['phone'],username=u['username'],balance=u['balance'],referralCode=u['referral_code'],state=json.loads(u['state']),ledger=[dict(r) for r in db.execute('SELECT delta,reason,order_id,created_at FROM ledger WHERE user_id=? ORDER BY created_at DESC LIMIT 200',(uid,))])
 def save_order(db,order):db.execute('UPDATE orders SET status=?,data=? WHERE id=?',(order['status'],dumps(order),order['id']))
 def do_cancel(db,order,actor):
  if order['status'] not in ['created','assembling','ready']:raise HTTPException(409,'cannot_cancel_at_this_stage')
  for line in order['items']:
   r=db.execute('SELECT data FROM products WHERE id=?',(line['id'],)).fetchone()
   if r:
    p=json.loads(r['data']);p['stock']+=line['qty'];db.execute('UPDATE products SET data=? WHERE id=?',(dumps(p),p['id']))
  bonus=order['quote']['bonus']
  if bonus:
   db.execute('UPDATE users SET balance=balance+? WHERE id=?',(bonus,order['userId']))
   db.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,order['userId'],bonus,'cancel_refund',order['id'],utc()))
  order['status']='cancelled';order['timeline'].append(dict(status='cancelled',at=utc()));save_order(db,order);audit(db,actor,'order.cancel',order['id'])
  return order

 @app.middleware('http')
 async def security(req,call_next):
  if req.url.path.startswith('/api/') and req.method not in ['GET','HEAD','OPTIONS']:
   # JSON-only write APIs + same-origin check + session-bound CSRF token.
   origin=req.headers.get('origin')
   expected=os.getenv('KEREK_ORIGIN',str(req.base_url).rstrip('/'))
   if origin and origin!=expected:return JSONResponse({'detail':'origin_rejected'},403)
   if 'application/json' not in req.headers.get('content-type',''):return JSONResponse({'detail':'json_required'},415)
   try:
    if int(req.headers.get('content-length','0'))>4_100_000:return JSONResponse({'detail':'request_too_large'},413)
   except ValueError:return JSONResponse({'detail':'invalid_content_length'},400)
   # Read at most 4 MB even when no Content-Length was supplied.
   body=await req.body()
   if len(body)>4_100_000:return JSONResponse({'detail':'request_too_large'},413)
   exempt=req.url.path in ['/api/auth/request-code','/api/auth/verify','/api/auth/admin']
   s=session(req)
   if s and not exempt and not hmac.compare_digest(s['csrf_hash'],digest(req.headers.get('x-csrf-token',''))):return JSONResponse({'detail':'csrf_rejected'},403)
  res=await call_next(req)
  res.headers['X-Content-Type-Options']='nosniff';res.headers['Referrer-Policy']='strict-origin-when-cross-origin';res.headers['X-Frame-Options']='DENY'
  res.headers['Permissions-Policy']='geolocation=(),camera=(),microphone=()'
  if req.url.path.startswith('/api/'):res.headers['Cache-Control']='no-store'
  # API docs use their own inline tooling; store pages never execute inline JS.
  if not req.url.path.startswith('/api/docs'):
   res.headers['Content-Security-Policy']="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https://images.unsplash.com; connect-src 'self'; font-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
  return res

 @app.get('/api/health')
 def health():return dict(service='kerek',version='3.0.0',mode='demo',capabilities=CAPABILITIES)
 @app.get('/api/bootstrap')
 def bootstrap():
  with database.connect() as db:
   return dict(products=database.products(db),settings=database.config(db,'settings'),categories=database.config(db,'categories'),recipes=database.config(db,'recipes'),photoIds=database.config(db,'photoIds'),mode='demo',capabilities=CAPABILITIES)
 @app.post('/api/auth/request-code')
 def request_code(body:Phone,req:Request):
  rate('otp-phone:'+body.phone,3,300);rate('otp-ip:'+ip(req),12,600)
  challenge=secrets.token_urlsafe(24);code=str(secrets.randbelow(1000000)).zfill(6)
  with database.connect(write=True) as db:
   db.execute('DELETE FROM otp WHERE phone=? OR expires<?',(body.phone,time.time()))
   db.execute('INSERT INTO otp(id,phone,hash,expires) VALUES(?,?,?,?)',(challenge,body.phone,password_hash(code),time.time()+300))
  return dict(challengeId=challenge,expiresIn=300,demoCode=code,mode='demo',message='SMS не отправлялось. Код только для тестового входа.')
 @app.post('/api/auth/verify')
 def verify(body:Verify,req:Request,response:Response):
  rate('verify-ip:'+ip(req),30,600)
  # Persist failed attempts before raising, to avoid transaction rollback of the counter.
  uid=None;error=None
  with database.connect(write=True) as db:
   o=db.execute('SELECT * FROM otp WHERE id=?',(body.challengeId,)).fetchone()
   if not o or o['expires']<time.time() or o['attempts']>=5:error='code_expired'
   else:
    db.execute('UPDATE otp SET attempts=attempts+1 WHERE id=?',(body.challengeId,))
    if not verify_password(body.code,o['hash']):error='wrong_code'
    else:
     db.execute('DELETE FROM otp WHERE id=?',(body.challengeId,))
     user=db.execute('SELECT id FROM users WHERE phone=?',(o['phone'],)).fetchone()
     if user:uid=user['id']
     else:
      uid=uuid.uuid4().hex;ref=db.execute('SELECT id FROM users WHERE referral_code=? AND role="customer"',(body.referral,)).fetchone() if body.referral else None
      db.execute('INSERT INTO users(id,phone,role,state,referral_code,referred_by,created_at) VALUES(?,?,?,?,?,?,?)',(uid,o['phone'],'customer','{}','KR'+secrets.token_hex(4).upper(),ref['id'] if ref else None,utc()))
  if error:raise HTTPException(400,error)
  csrf=signin(response,uid)
  with database.connect() as db:return dict(user=snapshot(db,uid),csrf=csrf)
 @app.post('/api/auth/admin')
 def admin_login(body:AdminLogin,req:Request,response:Response):
  rate('admin-ip:'+ip(req),5,300);rate('admin-user:'+body.username,8,600)
  with database.connect() as db:
   u=db.execute('SELECT * FROM users WHERE username=?',(body.username,)).fetchone()
   if not u or u['role'] not in ['admin','manager'] or not verify_password(body.password,u['password']):raise HTTPException(401,'invalid_credentials')
  csrf=signin(response,u['id'])
  with database.connect() as db:return dict(user=snapshot(db,u['id']),csrf=csrf)
 @app.get('/api/me')
 def me(req:Request):
  s=require(req)
  with database.connect() as db:return snapshot(db,s['user_id'])
 @app.post('/api/auth/logout')
 def logout(req:Request,response:Response):
  s=require(req)
  with database.connect(write=True) as db:db.execute('DELETE FROM sessions WHERE token_hash=?',(s['token_hash'],))
  response.delete_cookie('kerek_session',path='/');return {'ok':True}
 @app.put('/api/me')
 def update_me(body:ProfileInput,req:Request):
  s=require(req)
  with database.connect(write=True) as db:
   ids={p['id'] for p in database.products(db)}
   if any(i not in ids for i in body.cart) or any(not 1<=q<=99 for q in body.cart.values()):raise HTTPException(400,'invalid_cart')
   state=body.model_dump();state['favorites']=[i for i in state['favorites'] if i in ids]
   db.execute('UPDATE users SET state=? WHERE id=?',(dumps(state),s['user_id']))
   return snapshot(db,s['user_id'])
 @app.get('/api/me/export')
 def export(req:Request):
  s=require(req)
  with database.connect() as db:
   return dict(user=snapshot(db,s['user_id']),orders=[json.loads(r['data']) for r in db.execute('SELECT data FROM orders WHERE user_id=?',(s['user_id'],))],tickets=[json.loads(r['data']) for r in db.execute('SELECT data FROM tickets WHERE user_id=?',(s['user_id'],))])
 @app.delete('/api/me')
 def delete_me(body:ConfirmDelete,req:Request,response:Response):
  s=require(req,['customer'])
  with database.connect(write=True) as db:
   active=db.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status NOT IN ('delivered','cancelled')",(s['user_id'],)).fetchone()[0]
   if active:raise HTTPException(409,'cancel_active_orders_first')
   for r in db.execute('SELECT data FROM orders WHERE user_id=?',(s['user_id'],)).fetchall():
    o=json.loads(r['data']);o['address']='[удалено]';o['comment']='';save_order(db,o)
   for r in db.execute('SELECT id,data FROM tickets WHERE user_id=?',(s['user_id'],)).fetchall():
    t=json.loads(r['data']);t.update(text='[удалено]',reply='[удалено]');db.execute('UPDATE tickets SET data=? WHERE id=?',(dumps(t),r['id']))
   db.execute("UPDATE users SET phone=NULL,username=NULL,password=NULL,state='{}',role='deleted',balance=0,referral_code=NULL,referred_by=NULL WHERE id=?",(s['user_id'],))
   db.execute('DELETE FROM sessions WHERE user_id=?',(s['user_id'],));audit(db,s['user_id'],'account.anonymize',s['user_id'])
  response.delete_cookie('kerek_session',path='/');return {'ok':True,'retained':'Обезличенные записи заказов и финансовых операций сохранены.'}
 @app.post('/api/quote')
 def get_quote(body:QuoteInput,req:Request):
  s=session(req)
  with database.connect() as db:
   try:return quote(body.cart,database.products(db),database.config(db,'settings'),body.promo,body.bonus,s['balance'] if s else 0,body.zone)
   except ValueError as e:raise HTTPException(409,str(e))
 @app.get('/api/orders')
 def orders(req:Request):
  s=require(req)
  with database.connect() as db:return [json.loads(r['data']) for r in db.execute('SELECT data FROM orders WHERE user_id=? ORDER BY rowid DESC',(s['user_id'],))]
 @app.post('/api/orders')
 def create_order(body:OrderInput,req:Request):
  s=require(req,['customer','admin','manager']);rate('order:'+s['user_id'],20,600)
  data=body.model_dump();fingerprint=digest(dumps(data))
  with database.connect(write=True) as db:
   prior=db.execute('SELECT data FROM orders WHERE user_id=? AND idempotency=?',(s['user_id'],body.idempotencyKey)).fetchone()
   if prior:
    prev=json.loads(prior['data'])
    if prev['requestFingerprint']!=fingerprint:raise HTTPException(409,'idempotency_conflict')
    return prev
   settings=database.config(db,'settings');products=database.products(db)
   balance=db.execute('SELECT balance FROM users WHERE id=?',(s['user_id'],)).fetchone()[0]
   try:q=quote(body.cart,products,settings,body.promo,body.bonus,balance,body.zone)
   except ValueError as e:raise HTTPException(409,str(e))
   if not q['lines']:raise HTTPException(400,'empty_cart')
   if q['subtotal']<settings['minOrder']:raise HTTPException(400,'min_order')
   if q['promoError']:raise HTTPException(400,q['promoError'])
   if q['total']!=body.expectedTotal:raise HTTPException(409,'price_changed')
   try:
    day,interval=body.slot.split(' ',1);d=datetime.fromisoformat(day).date()
    # Almaty delivery slots use UTC+05, not the server's timezone.
    now=datetime.now(timezone(timedelta(hours=5)))
    if d<now.date() or d>now.date()+timedelta(days=7) or interval not in settings['slots']:raise ValueError()
    if d==now.date() and int(interval.split(':')[0])<=now.hour:raise ValueError()
   except (ValueError,IndexError):raise HTTPException(400,'invalid_slot')
   order=dict(id='KR-'+secrets.token_hex(4).upper(),userId=s['user_id'],createdAt=utc(),status='created',items=q['lines'],quote=q,address=body.address,slot=body.slot,comment=body.comment,replacements=body.replacements,zone=body.zone,paymentStatus='not_charged',demo=True,timeline=[dict(status='created',at=utc())],requestFingerprint=fingerprint)
   db.execute('INSERT INTO orders(id,user_id,status,data,idempotency) VALUES(?,?,?,?,?)',(order['id'],s['user_id'],'created',dumps(order),body.idempotencyKey))
   for l in q['lines']:
    p=next(p for p in products if p['id']==l['id']);p['stock']-=l['qty'];db.execute('UPDATE products SET data=? WHERE id=?',(dumps(p),p['id']))
   if q['bonus']:
    db.execute('UPDATE users SET balance=balance-? WHERE id=?',(q['bonus'],s['user_id']))
    db.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,s['user_id'],-q['bonus'],'redeem',order['id'],utc()))
   state=json.loads(db.execute('SELECT state FROM users WHERE id=?',(s['user_id'],)).fetchone()[0]);state['cart']={};db.execute('UPDATE users SET state=? WHERE id=?',(dumps(state),s['user_id']))
   audit(db,s['user_id'],'order.create',order['id']);return order
 @app.post('/api/orders/{oid}/cancel')
 def cancel(oid:str,req:Request):
  s=require(req)
  with database.connect(write=True) as db:
   r=db.execute('SELECT data FROM orders WHERE id=? AND user_id=?',(oid,s['user_id'])).fetchone()
   if not r:raise HTTPException(404,'not_found')
   return do_cancel(db,json.loads(r['data']),s['user_id'])
 @app.post('/api/payments/session')
 def no_payments(req:Request):require(req);raise HTTPException(503,'payment_provider_not_connected')
 @app.get('/api/orders/{oid}/tracking')
 def tracking(oid:str,req:Request):
  s=require(req)
  with database.connect() as db:
   if not db.execute('SELECT id FROM orders WHERE id=? AND user_id=?',(oid,s['user_id'])).fetchone():raise HTTPException(404,'not_found')
  raise HTTPException(503,'courier_provider_not_connected')
 @app.get('/api/support')
 def support(req:Request):
  s=require(req)
  with database.connect() as db:return [json.loads(r['data']) for r in db.execute('SELECT data FROM tickets WHERE user_id=? ORDER BY rowid DESC',(s['user_id'],))]
 @app.post('/api/support')
 def ticket(body:TicketInput,req:Request):
  s=require(req);rate('support:'+s['user_id'],10,600)
  with database.connect(write=True) as db:
   if body.orderId and not db.execute('SELECT id FROM orders WHERE id=? AND user_id=?',(body.orderId,s['user_id'])).fetchone():raise HTTPException(404,'not_found')
   t=dict(id='T-'+secrets.token_hex(4).upper(),userId=s['user_id'],**body.model_dump(),reply='',status='open',createdAt=utc(),demo=True)
   db.execute('INSERT INTO tickets VALUES(?,?,?)',(t['id'],s['user_id'],dumps(t)));return t
 @app.get('/api/admin/overview')
 def overview(req:Request):
  require(req,['admin','manager'])
  with database.connect() as db:
   orders=[json.loads(r['data']) for r in db.execute('SELECT data FROM orders ORDER BY rowid DESC')]
   return dict(orders=orders,tickets=[json.loads(r['data']) for r in db.execute('SELECT data FROM tickets ORDER BY rowid DESC')],users=db.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],demoSales=sum(o['quote']['total'] for o in orders if o['status']=='delivered'),mode='demo')
 @app.put('/api/admin/products/{pid}')
 def update_product(pid:str,body:ProductInput,req:Request):
  s=require(req,['admin','manager'])
  if pid!=body.id:raise HTTPException(400,'id_mismatch')
  if body.oldPrice and body.oldPrice<body.price:raise HTTPException(400,'invalid_old_price')
  with database.connect(write=True) as db:
   cats=database.config(db,'categories')
   if body.category not in [c['id'] for c in cats if c['id']!='all']:raise HTTPException(400,'invalid_category')
   p=body.model_dump();p['demo']=True # This server must not pass demo goods off as live.
   db.execute('INSERT INTO products(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',(pid,dumps(p)));audit(db,s['user_id'],'product.save',pid,dumps({'price':p['price'],'stock':p['stock']}));return p
 @app.put('/api/admin/settings')
 def settings(body:SettingsInput,req:Request):
  s=require(req,['admin'])
  with database.connect(write=True) as db:
   db.execute('UPDATE config SET data=? WHERE key="settings"',(dumps(body.model_dump()),));audit(db,s['user_id'],'settings.save','settings');return body
 @app.put('/api/admin/categories')
 def categories(body:Categories,req:Request):
  s=require(req,['admin'])
  vals=[x.model_dump() for x in body.categories];ids={x['id'] for x in vals}
  if len(ids)!=len(vals) or 'all' not in ids:raise HTTPException(400,'invalid_categories')
  with database.connect(write=True) as db:
   if any(p['active'] and p['category'] not in ids for p in database.products(db)):raise HTTPException(409,'category_in_use')
   db.execute('UPDATE config SET data=? WHERE key="categories"',(dumps(vals),));audit(db,s['user_id'],'categories.save','categories');return vals
 @app.post('/api/admin/orders/{oid}/status')
 def change_status(oid:str,body:StatusInput,req:Request):
  s=require(req,['admin','manager'])
  with database.connect(write=True) as db:
   r=db.execute('SELECT data FROM orders WHERE id=?',(oid,)).fetchone()
   if not r:raise HTTPException(404,'not_found')
   o=json.loads(r['data'])
   if o['status']==body.status:return o
   if body.status=='cancelled':return do_cancel(db,o,s['user_id'])
   transitions={'created':'assembling','assembling':'ready','ready':'delivering','delivering':'delivered'}
   if transitions.get(o['status'])!=body.status:raise HTTPException(409,'invalid_transition')
   o['status']=body.status;o['timeline'].append(dict(status=body.status,at=utc()))
   if body.status=='delivered':
    b=o['quote']['bonusEarned']
    if b:
     db.execute('UPDATE users SET balance=balance+? WHERE id=?',(b,o['userId']))
     db.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,o['userId'],b,'earned',oid,utc()))
    u=db.execute('SELECT referred_by FROM users WHERE id=?',(o['userId'],)).fetchone()
    previous=db.execute("SELECT COUNT(*) FROM orders WHERE user_id=? AND status='delivered'",(o['userId'],)).fetchone()[0]
    if u['referred_by'] and previous==0:
     reward=database.config(db,'settings')['referralReward'];ref=u['referred_by']
     db.execute('UPDATE users SET balance=balance+? WHERE id=? AND role="customer"',(reward,ref))
     if db.execute('SELECT role FROM users WHERE id=?',(ref,)).fetchone()['role']=='customer':db.execute('INSERT INTO ledger VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,ref,reward,'referral',oid,utc()))
   save_order(db,o);audit(db,s['user_id'],'order.status',oid,body.status);return o
 @app.put('/api/admin/tickets/{tid}')
 def reply(tid:str,body:TicketReply,req:Request):
  s=require(req,['admin','manager'])
  with database.connect(write=True) as db:
   r=db.execute('SELECT data FROM tickets WHERE id=?',(tid,)).fetchone()
   if not r:raise HTTPException(404,'not_found')
   t=json.loads(r['data']);t.update(body.model_dump());t['updatedAt']=utc();db.execute('UPDATE tickets SET data=? WHERE id=?',(dumps(t),tid));audit(db,s['user_id'],'ticket.reply',tid);return t
 @app.get('/api/admin/audit')
 def get_audit(req:Request):
  require(req,['admin'])
  with database.connect() as db:return [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 200')]
 @app.post('/api/admin/upload')
 def upload(body:UploadInput,req:Request):
  s=require(req,['admin','manager']);rate('upload:'+s['user_id'],20,600)
  try:
   raw=base64.b64decode(body.data,validate=True)
   if len(raw)>2_500_000:raise ValueError()
   Image.MAX_IMAGE_PIXELS=12_000_000
   im=Image.open(io.BytesIO(raw));im.verify()
   im=Image.open(io.BytesIO(raw))
   if im.format not in ['JPEG','PNG','WEBP'] or im.width*im.height>12_000_000:raise ValueError()
   im=im.convert('RGB');im.thumbnail((1000,1000))
  except (ValueError,UnidentifiedImageError,OSError,Image.DecompressionBombError,Image.DecompressionBombWarning):raise HTTPException(400,'invalid_image')
  folder=ROOT/'public/assets/uploads';folder.mkdir(parents=True,exist_ok=True)
  name=secrets.token_hex(16)+'.webp';im.save(folder/name,'WEBP',quality=82)
  with database.connect(write=True) as db:audit(db,s['user_id'],'image.upload',name)
  return {'image':'assets/uploads/'+name}
 @app.get('/admin')
 def admin_page():return FileResponse(ROOT/'public/admin.html')
 app.mount('/',StaticFiles(directory=ROOT/'public',html=True),name='storefront')
 return app
app=create_app()
