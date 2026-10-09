"""Provision privileged users from a local terminal, never from the browser."""
import argparse,getpass,uuid,sqlite3
from .app import app,password_hash,utc

def main():
 p=argparse.ArgumentParser();p.add_argument('command',choices=['create-admin','create-manager']);p.add_argument('--username',default='admin');a=p.parse_args()
 pw=getpass.getpass('New password (minimum 14 characters): ')
 if len(pw)<14:raise SystemExit('Password must have at least 14 characters.')
 if pw!=getpass.getpass('Repeat password: '):raise SystemExit('Passwords do not match.')
 try:
  with app.state.db.connect(write=True) as db:
   db.execute('INSERT INTO users(id,username,password,role,state,created_at) VALUES(?,?,?,?,?,?)',(uuid.uuid4().hex,a.username,password_hash(pw),'admin' if a.command=='create-admin' else 'manager','{}',utc()))
 except sqlite3.IntegrityError:raise SystemExit('Username already exists. Choose a different username.')
 print('Account created. Sign in at /admin. Never publish your database or password.')
if __name__=='__main__':main()
