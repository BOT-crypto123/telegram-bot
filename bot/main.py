import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
TOKEN=os.getenv('TELE_TOKEN') or ''
print('V216 TOKEN',len(TOKEN),flush=True)
app=Flask(__name__)
SEL='XRP'
ENTS={}
AUTO=False
CID=None
F1='/tmp/b216.json'
F2='/tmp/a216.json'
if os.path.exists(F1):
 ENTS.update(json.load(open(F1)).get('ENTS',{}))
if os.path.exists(F2):
 d=json.load(open(F2))
 AUTO=d.get('ON',False)
 CID=d.get('CID',None)
print('V216 LOADED',AUTO,flush=True)
def price(s):
 u='https://api.coinbase.com/v2/prices/'+s+'-USD/spot'
 r=requests.get(u,timeout=8).json()
 return float(r.get('data',{}).get('amount','0') or 0)
def candles(sym):
 u='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=60'
 r=requests.get(u,headers={'User-Agent':'M'},timeout=10).json()
 return sorted(r)[-60:] if isinstance(r,list) else []
def ema(p,n):
 if len(p)<n:
  return []
 k=2/(n+1)
 m=sum(p[:n])/n
 o=[m]
 for x in p[n:]:
  o.append(x*k+o[-1]*(1-k))
 return o
def rsi(p):
 if len(p)<15:
  return 50
 g=l=0
 for i in range(1,15):
  d=p[i]-p[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
def send(c,t):
 u='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
 k={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR','VENDER'],['GRAF','AUTO']],'resize_keyboard':True}
 requests.post(u,json={'chat_id':c,'text':t,'reply_markup':k},timeout=10)
def trade(sym,auto=False):
 try:
  cl=candles(sym)
  if not cl:
   return None
  cs=
