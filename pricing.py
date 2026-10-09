"""Authoritative integer-tenge pricing. Client totals are never trusted."""
from datetime import datetime,timezone

def quote(cart,products,settings,promo='',bonus=0,balance=0,zone='almaty'):
 if not isinstance(cart,dict) or len(cart)>150:raise ValueError('invalid_cart')
 indexed={p['id']:p for p in products};subtotal=0;savings=0;lines=[]
 for pid,qty in cart.items():
  p=indexed.get(pid)
  if not p or not p['active']:raise ValueError('unknown_product:'+str(pid))
  if isinstance(qty,bool) or not isinstance(qty,int) or not 1<=qty<=99:raise ValueError('invalid_quantity:'+pid)
  if qty>p['stock']:raise ValueError('stock:'+pid)
  amount=p['price']*qty;subtotal+=amount;savings+=max(0,p.get('oldPrice',0)-p['price'])*qty
  lines.append(dict(id=pid,name=p['name'],name_kk=p['name_kk'],qty=qty,price=p['price'],amount=amount))
 discount=0;promo_error='';today=datetime.now(timezone.utc).date().isoformat()
 code=promo.strip().upper()
 if code:
  p=next((p for p in settings['promos'] if p['code']==code and p['active'] and (not p.get('endsAt') or p['endsAt']>=today)),None)
  if not p:promo_error='promo_invalid'
  elif subtotal<p['minSubtotal']:promo_error='promo_min'
  else:discount=min(p['maxDiscount'],subtotal*p['percent']//100)
 max_bonus=max(0,min(balance,(subtotal-discount)*settings['maxBonusPercent']//100))
 used_bonus=min(max(0,bonus),max_bonus)
 z=next((z for z in settings['zones'] if z['id']==zone and z['enabled']),None)
 if lines and not z:raise ValueError('zone_unavailable')
 delivery=(z['fee'] if z else 0) if lines and subtotal<settings['freeDeliveryFrom'] else 0
 return dict(lines=lines,errors=[],subtotal=subtotal,discount=discount,bonus=used_bonus,maxBonus=max_bonus,delivery=delivery,total=max(0,subtotal-discount-used_bonus)+delivery,savings=savings+discount+used_bonus,promoError=promo_error,bonusEarned=max(0,subtotal-discount-used_bonus)*settings['bonusRate']//100,freeRemaining=max(0,settings['freeDeliveryFrom']-subtotal))
