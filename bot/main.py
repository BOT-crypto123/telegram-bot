import os,json,requests,threading,time,traceback
from flask import Flask,request
print("V39.6.5 MANUAL ALERTAS - FIX XRP")
BOT=os.environ.get("BOT_TOKEN")
#... tu mismo inicio
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k and "URL" in k: URL=v
 if "UPSTASH" in k and "TOKEN" in k:
  if "REDIS" in k and v!=BOT: TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home(): return "V39.6.5 LIVE MANUAL - BTC ETH XRP"

def load():
 try:
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  j=r.json().get("result")
  if j: return json.loads(j)
 except: pass
 return {"users":{}}
def save(data):
 try: requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(data)],timeout=10)
 except: pass
def send_msg(chat_id,text,buttons=None):
 try:
  url=f"https://api.telegram.org/bot{BOT}/sendMessage"
  payload={"chat_id":chat_id,"text":text,"parse_mode":"Markdown"}
  if buttons: payload["reply_markup"]=json.dumps({"inline_keyboard":buttons})
  requests.post(url,json=payload,timeout=10)
 except: pass

def get_prices():
 try:
  def gp(s): return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}",timeout=5).json()["price"])
  return gp("BTCUSDT"),gp("ETHUSDT"),gp("XRPUSDT")
 except: return 64122,1895,1.02

def get_rsi(symbol):
 try:
  r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100",timeout=8).json()
  closes=[float(c[4]) for c in r]
  deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
  gains=[d if d>0 else 0 for d in deltas]
  losses=[-d if d<0 else 0 for d in deltas]
  avg_gain=sum(gains[-14:])/14
  avg_loss=sum(losses[-14:])/14
  if avg_loss==0: return 70
  rs=avg_gain/avg_loss
  return round(100-(100/(1+rs)),1)
 except: return 50

def check_alerts():
 while True:
  try:
   time.sleep(300) # 5 min
   db=load()
   if not db.get("users"): continue
   btc,eth,xrp=get_prices()
   rsi_btc=get_rsi("BTCUSDT")
   rsi_eth=get_rsi("ETHUSDT")
   rsi_xrp=get_rsi("XRPUSDT")
   print(f"CHECK RSI BTC:{rsi_btc} ETH:{rsi_eth} XRP:{rsi_xrp}")
   for uid,u in db["users"].items():
    if not u.get("on",True): continue
    now=time.time()
    last_map=u.get("last_rsi_alert",{})
    for sym,price,rsi in [("BTC",btc,rsi_btc),("ETH",eth,rsi_eth),("XRP",xrp,rsi_xrp)]:
     if now-last_map.get(sym,0) < 7200: continue
     if rsi < 30:
      send_msg(uid,f"🟢 *COMPRA {sym} RSI {rsi} PRECIO {price}* - Tu decides SL:{u.get('sl',-5)}%")
      last_map[sym]=now
     elif rsi > 70:
      send_msg(uid,f"🔴 *VENTA {sym} RSI {rsi} PRECIO {price}* - Tu decides")
      last_map[sym]=now
    u["last_rsi_alert"]=last_map
   save(db)
  except Exception as e:
   print(f"loop err {e}")
   time.sleep(60)

threading.Thread(target=check_alerts,daemon=True).start()

#... tu mismo webhook de botones COMPRAR/VENDER/SL/TP/GRAF/PRO/Apagar/ACT
# Mantén tu código de botones igual, solo cambia el print de versión a V39.6.5
