"""SQLite repository. One connection per operation; write transactions serialize stock changes."""
import json, sqlite3
from pathlib import Path
from contextlib import contextmanager

SCHEMA='''
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,phone TEXT UNIQUE,username TEXT UNIQUE,password TEXT,role TEXT NOT NULL DEFAULT 'customer',state TEXT NOT NULL DEFAULT '{}',balance INTEGER NOT NULL DEFAULT 0 CHECK(balance>=0),referral_code TEXT UNIQUE,referred_by TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,csrf_hash TEXT NOT NULL,expires REAL NOT NULL);
CREATE TABLE IF NOT EXISTS otp(id TEXT PRIMARY KEY,phone TEXT NOT NULL,hash TEXT NOT NULL,expires REAL NOT NULL,attempts INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS limits(bucket TEXT NOT NULL,ts REAL NOT NULL);
CREATE INDEX IF NOT EXISTS limits_idx ON limits(bucket,ts);
CREATE TABLE IF NOT EXISTS products(id TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS config(key TEXT PRIMARY KEY,data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),status TEXT NOT NULL,data TEXT NOT NULL,idempotency TEXT NOT NULL,UNIQUE(user_id,idempotency));
CREATE TABLE IF NOT EXISTS tickets(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),data TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledger(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),delta INTEGER NOT NULL,reason TEXT NOT NULL,order_id TEXT,created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor TEXT NOT NULL,action TEXT NOT NULL,target TEXT NOT NULL,detail TEXT NOT NULL,created_at TEXT NOT NULL);
'''
def dumps(obj):return json.dumps(obj,ensure_ascii=False,separators=(',',':'))
class Database:
 def __init__(self,path,seed):
  self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True)
  with self.connect() as db:
   db.executescript(SCHEMA)
   for p in seed['products']: db.execute('INSERT OR IGNORE INTO products VALUES(?,?)',(p['id'],dumps(p)))
   for k in ['settings','categories','recipes','photoIds']:
    db.execute('INSERT OR IGNORE INTO config VALUES(?,?)',(k,dumps(seed[k])))
 @contextmanager
 def connect(self,write=False):
  db=sqlite3.connect(self.path,timeout=15,isolation_level=None);db.row_factory=sqlite3.Row;db.execute('PRAGMA foreign_keys=ON')
  try:
   if write:db.execute('BEGIN IMMEDIATE')
   yield db
   if write:db.commit()
  except Exception:
   if write:db.rollback()
   raise
  finally:db.close()
 @staticmethod
 def products(db):return [json.loads(r['data']) for r in db.execute('SELECT data FROM products')]
 @staticmethod
 def config(db,key):
  r=db.execute('SELECT data FROM config WHERE key=?',(key,)).fetchone();return json.loads(r['data']) if r else None
