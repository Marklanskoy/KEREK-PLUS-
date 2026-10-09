from pydantic import BaseModel,Field,ConfigDict,field_validator
from typing import Literal
import re
from datetime import date
class Model(BaseModel):
 model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
class Phone(Model):
 phone:str
 @field_validator('phone')
 @classmethod
 def valid(cls,v):
  p='+'+re.sub(r'\D','',v)
  if not re.fullmatch(r'\+7\d{10}',p):raise ValueError('Введите номер +7 и 10 цифр')
  return p
class Verify(Model):
 challengeId:str=Field(min_length=10,max_length=100)
 code:str=Field(pattern=r'^\d{6}$')
 referral:str=Field(default='',max_length=32)
class AdminLogin(Model):
 username:str=Field(min_length=2,max_length=80)
 password:str=Field(min_length=1,max_length=200)
class QuoteInput(Model):
 cart:dict[str,int]=Field(max_length=150)
 promo:str=Field(default='',max_length=40)
 bonus:int=Field(default=0,ge=0,le=1_000_000)
 zone:str=Field(default='almaty',max_length=40)
 @field_validator('cart',mode='before')
 @classmethod
 def quantities(cls,v):
  if not isinstance(v,dict) or any(isinstance(q,bool) or not isinstance(q,int) or not 1<=q<=99 for q in v.values()):raise ValueError('Количество должно быть целым: 1–99')
  return v
class OrderInput(QuoteInput):
 address:str=Field(min_length=6,max_length=300)
 slot:str=Field(min_length=5,max_length=100)
 comment:str=Field(default='',max_length=500)
 replacements:Literal['ask','skip','similar']='ask'
 payment:Literal['test']='test'
 expectedTotal:int=Field(ge=0,le=1_000_000_000)
 idempotencyKey:str=Field(min_length=12,max_length=100)
class ProfileInput(Model):
 name:str=Field(default='',max_length=80)
 language:Literal['ru','kk']='ru'
 notifications:bool=True
 addresses:list[dict]=Field(default_factory=list,max_length=10)
 favorites:list[str]=Field(default_factory=list,max_length=150)
 pantry:list[dict]=Field(default_factory=list,max_length=150)
 cart:dict[str,int]=Field(default_factory=dict,max_length=150)
 @field_validator('addresses')
 @classmethod
 def addresses_valid(cls,items):
  for x in items:
   if set(x)-{'id','label','text','zone'} or not isinstance(x.get('text'),str) or not 6<=len(x['text'])<=300:raise ValueError('Некорректный адрес')
  return items
 @field_validator('pantry')
 @classmethod
 def pantry_valid(cls,items):
  for x in items:
   if len(str(x))>1000 or not isinstance(x.get('amount'),(int,float)) or not 0<=x['amount']<=1e7 or x.get('unit') not in ['g','ml','pc']:raise ValueError('Некорректные запасы')
  return items
class TicketInput(Model):
 text:str=Field(min_length=5,max_length=3000)
 orderId:str=Field(default='',max_length=100)
 kind:Literal['support','return']='support'
class TicketReply(Model):
 reply:str=Field(default='',max_length=3000)
 status:Literal['open','answered','closed']
class StatusInput(Model):
 status:Literal['assembling','ready','delivering','delivered','cancelled']
class ProductInput(Model):
 id:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,50}$')
 name:str=Field(min_length=2,max_length=150)
 name_kk:str=Field(min_length=2,max_length=150)
 price:int=Field(ge=1,le=10_000_000)
 oldPrice:int=Field(default=0,ge=0,le=10_000_000)
 category:str=Field(min_length=1,max_length=50)
 subcategory:str=Field(default='',max_length=50)
 ingredient:str=Field(pattern=r'^[a-zA-Z0-9_-]{1,50}$')
 pack:int=Field(ge=1,le=100000)
 unit:Literal['g','ml','pc']
 image:str=Field(default='',max_length=500)
 emoji:str=Field(default='🛍️',max_length=10)
 stock:int=Field(ge=0,le=1000000)
 brand:str=Field(default='',max_length=80)
 popularity:int=Field(default=0,ge=0,le=1000000)
 active:bool=True
 demo:bool=True
 composition:str|None=Field(default=None,max_length=2000)
 storage:str|None=Field(default=None,max_length=1000)
 description:str=Field(default='',max_length=2000)
 allergens:list[str]=Field(default_factory=list,max_length=30)
 @field_validator('image')
 @classmethod
 def valid_image(cls,v):
  if v and not re.fullmatch(r'[\w-]+|assets/uploads/[\w.-]+|https://images\.unsplash\.com/[\w?=&%./-]+',v):raise ValueError('Use an uploaded image or an Unsplash image URL')
  return v
class Promo(Model):
 code:str=Field(pattern=r'^[A-Z0-9_-]{2,40}$')
 percent:int=Field(ge=0,le=90)
 maxDiscount:int=Field(ge=0,le=100000)
 minSubtotal:int=Field(ge=0,le=1000000)
 active:bool=True
 endsAt:str=Field(default='',pattern=r'^$|^\d{4}-\d{2}-\d{2}$')
 @field_validator('endsAt')
 @classmethod
 def real_expiry(cls,v):
  if v:date.fromisoformat(v)
  return v
class Zone(Model):
 id:str=Field(pattern=r'^[a-z0-9_-]{1,40}$')
 name:str=Field(min_length=2,max_length=100)
 fee:int=Field(ge=0,le=100000)
 enabled:bool=True
class SettingsInput(Model):
 deliveryFee:int=Field(ge=0,le=100000)
 freeDeliveryFrom:int=Field(ge=0,le=1000000)
 minOrder:int=Field(ge=0,le=1000000)
 bonusRate:int=Field(ge=0,le=30)
 maxBonusPercent:int=Field(ge=0,le=90)
 referralReward:int=Field(ge=0,le=100000)
 slots:list[str]=Field(min_length=1,max_length=30)
 zones:list[Zone]=Field(min_length=1,max_length=30)
 promos:list[Promo]=Field(max_length=100)
 @field_validator('slots')
 @classmethod
 def valid_slots(cls,slots):
  intervals=[]
  for slot in slots:
   m=re.fullmatch(r'([01]\d|2[0-3]):([0-5]\d)–([01]\d|2[0-3]):([0-5]\d)',slot)
   if not m:raise ValueError('Use HH:MM–HH:MM slots')
   h,mn,eh,em=map(int,m.groups());start=h*60+mn;end=eh*60+em
   if end<=start:raise ValueError('Slot end must follow start')
   if any(start<b and end>a for a,b in intervals):raise ValueError('Slots must not overlap')
   intervals.append((start,end))
  return slots
 @field_validator('zones','promos')
 @classmethod
 def unique_keys(cls,items):
  keys=[getattr(x,'id',None) or x.code for x in items]
  if len(keys)!=len(set(keys)):raise ValueError('Duplicate zone or promo identifier')
  return items
class Category(Model):
 id:str=Field(pattern=r'^[a-z0-9_-]{1,40}$')
 name:str=Field(min_length=2,max_length=80)
 name_kk:str=Field(min_length=2,max_length=80)
 icon:str=Field(default='bag',max_length=30)
 image:str=Field(default='hero',max_length=100)
class Categories(Model):
 categories:list[Category]=Field(min_length=1,max_length=30)
class UploadInput(Model):
 data:str=Field(min_length=20,max_length=4_000_000)
class ConfirmDelete(Model):
 confirm:Literal['DELETE']
