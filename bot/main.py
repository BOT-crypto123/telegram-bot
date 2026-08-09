import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
TOKEN=os.getenv('TELE_TOKEN') or ''
print('V217 TOKEN',len(TOKEN),flush=True)
app=Flask(__name__)
SEL='XRP'
ENTS={}
AUTO=False
CID=None
F1='/tmp/b217.json'
F2='/tmp/a217.json'
if os.path.exists(F1):
 ENTS.update(json.load(open(F1)).get('ENTS',{}))
if os.path.exists(F2):
 d=json.load(open(F2))
 AUTO=d.get('ON',False)
 CID=d.get('CID',None)
print('V217 LOADED',AUTO,flush=True)
def price(s):
 u='https://api.coinbase.com/v2/prices/'
 u+=s+'-USD/spot'
 r=requests.get(u,timeout=8).json()
 v=r.get('data',{}).get('amount','0')
 return float(v or 0)
def candles(sym):
 u='https://api.exchange.coinbase.com/products/'
 u+=sym+'-USD/candles?granularity=60'
 r=requests.get(u,headers={'User-Agent':'M'},timeout=10).json()
 if isinstance(r,list):
  r=sorted(r)
  return r[-60:]
 return []
def ema(p,n):
 if len(p)<n:
  return []
 k=2/(n+1)
 m=sum(p[:n])/n
 o=[]
 o.append(m)
 for x in p[n:]:
  y=x*k+o[-1]*(1-k)
  o.append(y)
 return o
def rsi(p):
 if len(p)<15:
  return 50
 g=0
 l=0
 for i in range(1,15):
  d=p[i]-p[i-1]
  if d>0:
   g+=d
  if d<0:
   l+=-d
 if l==0:
  return 88
 if g==0:
  return 12
 return 100-100/(1+g/l)
def send(c,t):
 u='https://api.telegram.org/bot'
 u+=TOKEN+'/sendMessage'
 k={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR','VENDER'],['GRAF','AUTO']],'resize_keyboard':True}
 requests.post(u,json={'chat_id':c,'text':t,'reply_markup':k},timeout=10)
def trade(sym,auto=False):
 cl=candles(sym)
 if not cl:
  return None
 cs=[]
 for a in cl:
  cs.append(a[4])
 p=price(sym)
 if p==0:
  p=cs[-1]
 e9=ema(cs,9)
 e21=ema(cs,21)
 rr=rsi(cs)
 if not e9:
  return None
 if not e21:
  return None
 if rr<30:
  if sym not in ENTS:
   ENTS[sym]={'entry':p}
   open(F1,'w').write(json.dumps({'ENTS':ENTS}))
   return 'AUTO COMPRA '+sym
 if rr>70:
  if sym in ENTS:
   del ENTS[sym]
   open(F1,'w').write(json.dumps({'ENTS':ENTS}))
   return 'AUTO VENTA '+sym
 return None
def loop():
 while True:
  time.sleep(600)
  if not AUTO:
   continue
  if not CID:
   continue
  for s in ['BTC','ETH','SOL','XRP']:
   m=trade(s,True)
   if m:
    send(CID,'🚨 '+m+' 🚨 AUTO ON')
    time.sleep(2)
threading.Thread(target=loop,daemon=True).start()
@app.route('/')
def home():
 return 'V217 LIVE',200
@app.route('/webhook',methods=['POST'])
def wh():
 global SEL,AUTO,CID
 d=request.get_json(force=True,silent=True)
 if not d:
  return 'ok',200
 if 'message' not in d:
  return 'ok',200
 cid=d['message']['chat']['id']
 txt=d['message'].get('text','').upper().strip()
 if 'BTC' in txt:
  SEL='BTC'
 if 'ETH' in txt:
  SEL='ETH'
 if 'SOL' in txt:
  SEL='SOL'
 if 'XRP' in txt:
  SEL='XRP'
 pn=price(SEL)
 if 'AUTO' in txt:
  AUTO=not AUTO
  CID=cid
  open(F2,'w').write(json.dumps({'ON':AUTO,'CID':cid}))
  if AUTO:
   send(cid,'AUTO ON COMPRAS AUTO')
  else:
   send(cid,'AUTO OFF MANUAL')
  return 'ok',200
 if 'GRAF' in txt:
  from PIL import Image,ImageDraw
  cl=candles(SEL)
  cs=[]
  for a in cl:
   cs.append(a[4])
  p=price(SEL)
  if p==0:
   p=cs[-1]
  rr=rsi(cs)
  e9=ema(cs,9)
  e21=ema(cs,21)
  mn=min(cs)
  mx=max(cs)
  if mn==mx:
   mn=mn*0.998
   mx=mx*1.002
  W=1000
  H=560
  im=Image.new('RGB',(W,H),(10,14,21))
  dr=ImageDraw.Draw(im)
  i=0
  for c in cl:
   x=20+i*13
   lo=c[1]
   hi=c[2]
   o=c[3]
   cc=c[4]
