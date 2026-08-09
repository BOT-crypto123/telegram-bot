import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
T=os.getenv('TELE_TOKEN') or ''
A=Flask(__name__)
S='XRP'
E={}
ON=False
CID=None
F='/tmp/b222.json'
G='/tmp/a222.json'
if os.path.exists(F):
 E=json.load(open(F)).get('ENTS',{})
if os.path.exists(G):
 d=json.load(open(G))
 ON=d.get('ON',False)
 CID=d.get('CID',None)
def prc(s):
 u='https://api.coinbase.com/v2/prices/'+s+'-USD/spot'
 r=requests.get(u,timeout=8).json()
 return float(r.get('data',{}).get('amount','0') or 0)
def cnd(sym):
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
def snd(c,t):
 u='https://api.telegram.org/bot'+T+'/sendMessage'
 k={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR','VENDER'],['GRAF','AUTO']],'resize_keyboard':True}
 requests.post(u,json={'chat_id':c,'text':t,'reply_markup':k},timeout=10)
def loop():
 while True:
  time.sleep(600)
  if not ON or not CID:
   continue
  for s in ['BTC','ETH','SOL','XRP']:
   cl=cnd(s)
   if not cl:
    continue
   cs=[]
   for a in cl:
    cs.append(a[4])
   rr=rsi(cs)
   if rr<30 or rr>70:
    snd(CID,'🚨 AUTO '+s+' RSI:'+str(int(rr))+' 🚨')
    time.sleep(2)
threading.Thread(target=loop,daemon=True).start()
@A.route('/')
def home():
 return 'V222 LIVE',200
@A.route('/webhook',methods=['POST'])
def wh():
 global S,ON,CID
 d=request.get_json(force=True,silent=True)
 if not d or 'message' not in d:
  return 'ok',200
 cid=d['message']['chat']['id']
 txt=d['message'].get('text','').
