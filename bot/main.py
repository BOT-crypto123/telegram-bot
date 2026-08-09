import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
T=os.getenv('TELE_TOKEN') or ''
print('V220 TOKEN',len(T),flush=True)
A=Flask(__name__)
S='XRP'
E={}
F='/tmp/b220.json'
G='/tmp/a220.json'
ON=False
CID=None
if os.path.exists(F):
 E.update(json.load(open(F)).get('ENTS',{}))
if os.path.exists(G):
 d=json.load(open(G))
 ON=d.get('ON',False)
 CID=d.get('CID',None)
print('V220 LOADED',ON,flush=True)
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
def trd(sym,auto=False):
 cl=cnd(sym)
 if not cl:
  return None
 cs=[]
 for a in cl:
  cs.append(a[4])
 p=prc(sym)
 if p==0:
  p=cs[-1]
 rr=rsi(cs)
 if rr<30 and sym not in E:
  E[sym]={'entry':p}
  open(F,'w').write(json.dumps({'ENTS':E}))
  return 'AUTO COMPRA '+sym+' '+str(round(p,4))
 if rr>70 and sym in E:
  pnl=(p/E[sym]['entry']-1)*100
  del E[sym]
  open(F,'w').write(json.dumps({'ENTS':E}))
  return 'AUTO VENTA '+sym+' '+str(round(pnl,2))+'%'
 return None
def loop():
 while True:
  time.sleep(600)
  if not ON or not CID:
   continue
  for s in ['BTC','ETH','SOL','XRP']:
   m=trd(s,True)
   if m:
    snd(CID,'🚨🚨🚨 '+m+' 🚨🚨🚨 AUTO ON')
    time.sleep(2)
threading.Thread(target=loop,daemon=True).start()
@A.route('/')
def home():
 return 'V220 LIVE ON:'+str(ON),200
@A.route('/webhook',methods=['POST'])
def wh():
 global S,ON,CID
 d=request.get_json(force=True,silent=True)
 if not d or 'message' not in d:
  return 'ok',200
 cid=d['message']['chat']['id']
 txt=d['message'].get('text','').upper().strip()
 if 'BTC' in txt:
  S='BTC'
 if 'ETH' in txt:
  S='ETH'
 if 'SOL' in txt:
  S='SOL'
 if 'XRP' in txt:
  S='XRP'
 pn=prc(S)
 if 'AUTO' in txt:
  ON=not ON
  CID=cid
  open(G,'w').write(json.dumps({'ON':ON,'CID':cid}))
  snd(cid,'AUTO '+('ON 🤖 COMPRAS AUTO ACTIVAS' if ON else 'OFF 🔕 MANUAL'))
  return 'ok',200
 if 'GRAF' in txt:
  from PIL import Image,ImageDraw
  cl=cnd(S)
  cs=[]
  for a in cl:
   cs.append(a[4])
  p=prc(S)
  if p==0:
   p=cs[-1]
  rr=rsi(cs)
  mn=min(cs)
  mx=max(cs)
  if mn==mx:
   mn*=0.998
   mx*=1.002
  im=Image.new('RGB',(1000,560),(10,14,21))
  dr=ImageDraw.Draw(im)
  i=0
  for c in cl:
   x=20+i*13
   y1=490-(c[1]-mn)/(mx-mn)*460
   y2=490-(c[2]-mn)/(mx-mn)*460
   yo=490-(c[3]-mn)/(mx-mn)*460
   yc=490-(c[4]-mn)/(mx-mn)*460
   yt=min(yo,yc)
   yb=max(yo,yc)
   col=(0,230,118) if c[4]>=c[3] else (255,61,87)
   dr.line([x+3,y1,x+3,y2],fill=col)
   dr.rectangle([x,yt,x+6,yb],fill=col)
   i+=1
  cap=S+' '+str(round(p,4))+' RSI:'+str(int(rr))+' AUTO:'+str(ON)+' V220'
  bio=io.BytesIO()
  bio.name='g.png'
  im.save(bio,'PNG')
  bio.seek(0)
  requests.post('https://api.telegram.org/bot'+T+'/sendPhoto',data={'chat_id':cid,'caption':cap},files={'photo':bio},timeout=12)
  m=trd(S,ON)
  if m:
   snd(cid,'🚨 '+m+' 🚨')
  return 'ok',200
 if 'COMPRAR' in txt:
  E[S]={'entry':pn}
  open(F,'w').write(json.dumps({'ENTS':E}))
  snd(cid,'COMPRA OK')
  return 'ok',200
 if 'VENDER' in txt:
  if S in E:
   del E[S]
   open(F,'w').write(json.dumps({'ENTS':E}))
   snd(cid,'VENTA OK')
  return 'ok',200
 snd(cid,S+' '+str(round(pn,4)))
 return 'ok',200
print('V220 START BIND',flush=True)
A.run(host='0.0.0.0',port=int(os.getenv('PORT','10000')),debug=False,use_reloader=False)
