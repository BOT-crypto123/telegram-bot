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
 except:
  pass
def save():
 try:
  open(FILE,'w').write(json.dumps({'ENTS':ENTS,'CONFIG':CONFIG}))
 except:
  pass
load()
def price(s):
 try:
  r=requests.get('https://api.coinbase.com/v2/prices/'+s+'-USD/spot',timeout=8).json()
  return float(r['data']['amount'])
 except:
  return 0
def get_candles(sym):
 try:
  url='https://api.exchange.coinbase.com/products/'+sym+'-USD/candles?granularity=60'
  r=requests.get(url,headers={'User-Agent':'Mozilla/5.0'},timeout=10).json()
  return sorted(r)[-50:]
 except:
  return []
def ema_calc(prices,period):
 if len(prices)<period:
  return []
 k=2/(period+1)
 ema=[sum(prices[:period])/period]
 for p in prices[period:]:
  ema.append(p*k+ema[-1]*(1-k))
 return ema
def rsi_calc(prices):
 if len(prices)<15:
  return 50
 gains=0
 losses=0
 for i in range(1,15):
  d=prices[i]-prices[i-1]
  if d>=0:
   gains+=d
  else:
   losses-=d
 if losses==0:
  return 79
 return 100-100/(1+gains/losses)
def send_text(cid,txt):
 try:
  url='https://api.telegram.org/bot'+TOKEN+'/sendMessage'
  kb={'keyboard':[['BTC','ETH'],['SOL','XRP'],['COMPRAR 100','VENDER'],['GRAF','PRO'],['AUTO ON','AUTO OFF']],'resize_keyboard':True}
  requests.post(url,json={'chat_id':cid,'text':txt,'reply_markup':kb},timeout=15)
 except:
  pass
def check_signal(sym):
 try:
  candles=get_candles(sym)
  if not candles:
   return None
  closes=[]
  for c in candles:
   closes.append(c[4])
  p=price(sym)
  if p==0:
   p=closes[-1]
  ema9=ema_calc(closes,9)
  ema21=ema_calc(closes,21)
  rsi=rsi_calc(closes)
  if len(ema9)==0:
   return None
  if len(ema21)==0:
   return None
  e9=ema9[-1]
  e21=ema21[-1]
  if p>e9 and e9>e21 and rsi<30:
   return {'sym':sym,'price':p,'rsi':rsi,'senial':'COMPRA FUERTE','score':85}
  if p<e9 and e9<e21 and rsi>70:
   return {'sym':sym,'price':p,'rsi':rsi,'senial':'VENTA FUERTE','score':82}
 except:
  return None
 return None
def auto_loop():
 while True:
  try:
   time.sleep(300)
   if CONFIG.get('AUTO')==False:
    continue
   cid=CONFIG.get('LAST_CID')
   if cid==0:
    continue
   for sym in ['BTC','ETH','SOL','XRP']:
    sig=check_signal(sym)
    if sig:
     txt='ALERTA V99 '+sig['sym']+' '+sig['senial']+'\n'
     txt=txt+'Precio:'+str(round(sig['price'],2))+' RSI:'+str(round(sig['rsi'],1))+' '+str(sig['score'])+'%\n'
     txt=txt+'Manda GRAF '+sig['sym']
     send_text(cid,txt)
     time.sleep(3)
  except:
   time.sleep(60)
threading.Thread(target=auto_loop,daemon=True).start()
@app.route('/')
def home():
 return 'V99.2 OK',200
@app.route('/webhook',methods=['POST'])
def wh():
 global SEL
 d=request.get_json(force=True,silent=True)
 if not d or 'message' not in d:
  return 'ok',200
 msg=d.get('message')
 cid=msg.get('chat').get('id')
