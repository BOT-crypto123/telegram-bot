import os,requests,threading,time,re,io,json
from flask import Flask,request
from datetime import datetime,timedelta
TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot93.json'
CONFIG={'AUTO':False,'LAST_CID':0}
def load():
 try:
  if os.path.exists(FILE):
   with open(FILE,'r') as f:
    d=json.load(f)
    ENTS.update(d.get('ENTS',{}))
    CONFIG.update(d.get('CONFIG',{}))
 except: pass
def save():
 try:
  with open(FILE,'w') as f: json.dump({'ENTS':ENTS,'CONFIG':CONFIG},f)
 except: pass
load()
def price(s):
 try:
  r=requests.get('https://api.coinbase.com/v2/prices/'+s+'-USD/spot',timeout=8).json()
  return float(r['data']['amount'])
 except: return 0
def get_candles(sym,n=50):
 try:
  url='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=60'
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=10).json()
  return sorted(r)[-n:]
 except: return []
def ema_calc(prices,period):
 if len(prices)<period: return []
 k=2/(period+1)
 ema=[sum(prices[:period])/period]
 for p in prices[period:]:
  ema.append(p*k+ema[-1]*(1-k))
 return ema
def rsi_calc(prices,period=14):
 if len(prices)<period+1: return 50
 gains=0;losses=0
 for i in range(1,period+1):
  d=prices[i]-prices[i-1]
  if d>=0: gains+=d
  else: losses+=-d
 if losses==0: return 75
 rs=gains/losses
 return 100-(100/(1+rs))
def send_text(cid,txt):
 try:
  url='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
  kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR 100','VENDER'],['GRAF','PRO'],['AUTO ON','AUTO OFF']],'resize_keyboard':True}
  requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=15)
 except: pass
@app.route('/')
def home(): return 'V93 OK',200
@app.route('/webhook',methods=['POST'])
def wh():
 global SEL
 d=request.get_json(force=True,silent=True)
 if not d or 'message' not in d: return 'ok',200
 msg=d.get('message');cid=msg.get('chat').get('id')
 t=msg.get('text','').upper().strip()
 CONFIG['LAST_CID']=cid;save()
 if 'AUTO ON' in t:
  CONFIG['AUTO']=True;save();send_text(cid,'V93 AUTO ON');return 'ok',200
 if 'AUTO OFF' in t:
  CONFIG['AUTO']=False;save();send_text(cid,'V93 AUTO OFF');return 'ok',200
 for s in ['BTC','ETH','SOL','XRP']:
  if s in t: SEL=s
 p=price(SEL)
 if p==0 and SEL in ENTS:
  p=ENTS.get(SEL).get('entry')
 if 'GRAF' in t:
  from PIL import Image,ImageDraw
  candles=get_candles(SEL,50)
  W=900;H=520
  img=Image.new('RGB',(W,H),'#0b0e14')
  dr=ImageDraw.Draw(img)
  closes=[c[4] for c in candles] if candles else [p]
  mn=mx=p
  if candles:
   lows=[c[1] for c in candles]
   highs=[c[2] for c in candles]
   mn=min(min(lows),p)*0.9995
   mx=max(max(highs),p)*1.0005
  def yf(v):
   return H-70-(v-mn)/(mx-mn)*(H-110) if mx!=mn else H//2
  def xf(i):
   return 20+i*(W-
