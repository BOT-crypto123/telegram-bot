import os,requests,re,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
TOKEN=os.getenv('TELE_TOKEN') or os.getenv('BOT_TOKEN') or ''
app=Flask(__name__)
SEL='XRP'
ENTS={}
FILE='/tmp/bot.json'
CONFIG={'AUTO':False,'LAST_CID':0}
def load():
 try:
  for old in ['/tmp/bot95.json','/tmp/bot93.json','/tmp/bot99.json','/tmp/bot.json']:
   if os.path.exists(old):
    d=json.load(open(old))
    ENTS.update(d.get('ENTS',{}))
    CONFIG.update(d.get('CONFIG',{}))
 except: pass
def save():
 try:
  open(FILE,'w').write(json.dumps({'ENTS':ENTS,'CONFIG':CONFIG}))
 except: pass
load()
def price(s):
 try:
  r=requests.get('https://api.coinbase.com/v2/prices/'+s+'-USD/spot',timeout=8).json()
  return float(r['data']['amount'])
 except: return 0
def get_candles(sym):
 try:
  url='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=60'
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=10).json()
  return sorted(r)[-50:]
 except: return []
def ema_calc(prices,period):
 if len(prices)<period: return []
 k=2/(period+1)
 ema=[sum(prices[:period])/period]
 for p in prices[period:]:
  ema.append(p*k+ema[-1]*(1-k))
 return ema
def rsi_calc(prices):
 if len(prices)<15: return 50
 gains=0;losses=0
 for i in range(1,15):
  d=prices[i]-prices[i-1]
  if d>=0: gains+=d
  else: losses-=d
 if losses==0: return 79
 return 100-100/(1+gains/losses)
def send_text(cid,txt):
 try:
  url='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
  kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR 100','VENDER'],['GRAF','PRO'],['AUTO ON','AUTO OFF']],'resize_keyboard':True}
  requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=15)
 except: pass
def check_signal(sym):
 try:
  candles=get_candles(sym)
  if not candles: return None
  closes=[c[4] for c in candles]
  p=price(sym) or closes[-1]
  ema9=ema_calc(closes,9);ema21=ema_calc(closes,21);rsi=rsi_calc(closes)
  if not ema9 or not ema21: return None
  e9=ema9[-1];e21=ema21[-1]
  senial=None;score=0
  if p>e9 and e9>e21 and rsi<30: senial='COMPRA FUERTE';score=85
  if p<e9 and e9<e21 and rsi>70: senial='VENTA FUERTE';score=82
  if senial:
   return {'sym':sym,'price':p,'rsi':rsi,'senial':senial,'score':score}
 except: return None
 return None
def auto_loop():
 while True:
  try:
   time.sleep(300)
   if not CONFIG.get('AUTO'): continue
   cid=CONFIG.get('LAST_CID')
   if not cid: continue
   for sym in ['BTC','ETH','SOL','XRP']:
    sig=check_signal(sym)
    if sig:
     txt='ALERTA V99 '+sig['sym']+' '+sig['senial']+'\n'
     txt=txt+'Precio:'+str(round(sig['price'],2))+' RSI:'+str(round(sig['rsi'],1))+' '+str(sig['score'])+'%\n'
     txt=txt+'Manda GRAF '+sig['sym']
     send_text(cid,txt)
     time.sleep(3)
  except: time.sleep(60)
threading.Thread(target=auto_loop,daemon=True).start()
@app.route('/')
def home(): return 'V99.1 OK',200
@app.route('/webhook',methods=['POST'])
def wh():
 global SEL
 d=request.get_json(force=True,silent=True)
 if not d or 'message' not in d: return 'ok',200
 msg=d.get('message');cid=msg.get('chat').get('id');t=msg.get('text','').upper().strip()
 CONFIG['LAST_CID']=cid;save()
 if 'AUTO ON' in t:
  CONFIG['AUTO']=True;save();send_text(cid,'V99.1 AUTO ON - Revisando cada 5min SENALES FUERTES');return 'ok',200
 if 'AUTO OFF' in t:
  CONFIG['AUTO']=False;save();send_text(cid,'V99.1 AUTO OFF');return 'ok',200
 for s in ['BTC','ETH','SOL','XRP']:
  if s in t: SEL=s
 p=price(SEL)
 if p==0 and SEL in ENTS: p=ENTS[SEL]['entry']
 if 'GRAF' in t:
  from PIL import Image,ImageDraw
  candles=get_candles(SEL)
  W=900;H=520
  img=Image.new('RGB',(W,H),'#0b0e14')
  dr=ImageDraw.Draw(img)
  closes=[c[4] for c in candles] if candles else [p]
  mn=p;mx=p
  if candles:
   for c in candles:
    if c[1]<mn: mn=c[1]
    if c[2]>mx: mx=c[2]
  if mn==mx: mn=mn*0.999;mx=mx*1.001
  ema9=ema_calc(closes,9);ema21=ema_calc(closes,21);rsi=rsi_calc(closes)
  pred='NEUTRAL';score=50;senial='ESPERAR'
  if ema9 and ema21:
   e9=ema9[-1];e21=ema21[-1]
   if p>e9 and e9>e21: pred='SUBIDA';score=68;senial='COMPRA'
   elif p<e9 and e9<e21: pred='BAJADA';score=65;senial='VENTA'
   if rsi
