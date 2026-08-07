import os,json,requests,threading,time,traceback
from flask import Flask,request
from datetime import datetime
print("V39.6.5 MANUAL ALERTAS - FIX XRP RSI 24.5")

BOT=os.environ.get("BOT_TOKEN")
if not BOT:
 for k,v in os.environ.items():
  if "TELE" in k and "TOKEN" in k: BOT=v

URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k and "URL" in k: URL=v
 if "UPSTASH" in k and "TOKEN" in k:
  if "REDIS" in k and v!=BOT: TOK=v

KEY="btc-vicente-v36-1-final"
app=Flask(__name__)

@app.route("/")
def home():
 return "V39.6.5 LIVE MANUAL - 3 COINS"

def load():
 try:
  if not URL or not TOK: return {"users":{}}
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  j=r.json().get("result")
  if j: return json.loads(j)
 except Exception as e: print(f"load err {e}")
 return {"users":{}}

def save(data):
 try:
  if not URL or not TOK: return
  requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(data)],timeout=10)
 except Exception as e: print(f"save err {e}")

def send_msg(chat_id,text,buttons=None):
 try:
  url=f"https://api.telegram.org/bot{BOT}/sendMessage"
  payload={"chat_id":chat_id,"text":text,"parse_mode":"Markdown"}
  if buttons: payload["reply_markup"]=json.dumps({"inline_keyboard":buttons})
  requests.post(url,json=payload,timeout=10)
 except Exception as e: print(f"send err {e}")

def get_price_binance(sym):
 try:
  r=requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={sym}",timeout=5).json()
  return float(r["price"])
 except: return None

def get_prices():
 btc=get_price_binance("BTCUSDT") or 64122
 eth=get_price_binance("ETHUSDT") or 1895
 xrp=get_price_binance("XRPUSDT") or 1.02
 return btc,eth,xrp

def get_rsi(symbol,period=14):
 try:
  r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100",timeout=8).json()
  closes=[float(c[4]) for c in r]
  deltas=[closes[i]-closes[i-1] for i in range(1,len(closes))]
  gains=[d if d>0 else 0 for d in deltas]
  losses=[-d if d<0 else 0 for d in deltas]
  avg_gain=sum(gains[-period:])/period
  avg_loss=sum(losses[-period:])/period
  if avg_loss==0: return 70
  rs=avg_gain/avg_loss
  return round(100-(100/(1+rs)),1)
 except: return 50

def get_user(chat_id):
 db=load()
 uid=str(chat_id)
 if uid not in db.get("users",{}):
  db.setdefault("users",{})[uid]={"on":True,"sl":-5,"tp":10,"entry":0,"last_rsi_alert":{}}
  save(db)
 return db,uid

def check_loop():
 while True:
  try:
   time.sleep(300)
   db=load()
   if not db.get("users"): continue
   btc,eth,xrp=get_prices()
   rb=get_rsi("BTCUSDT"); re=get_rsi("ETHUSDT"); rx=get_rsi("XRPUSDT")
   print(f"V39.6.5 CHECK BTC {btc} RSI {rb} | ETH {re} | XRP {xrp} RSI {rx}")
   for uid,u in db["users"].items():
    if not u.get("on",True): continue
    now=time.time()
    lm=u.get("last_rsi_alert",{})
    for sym,price,rsi in [("BTC",btc,rb),("ETH",eth,re),("XRP",xrp,rx)]:
     if now-lm.get(sym,0) < 7200: continue
     if rsi < 30:
      send_msg(uid,f"🟢 *COMPRA {sym} RSI {rsi} PRECIO {price}*\nTu decides. SL:{u.get('sl',-5)}% TP:+{u.get('tp',10)}%")
      lm[sym]=now
     elif rsi > 70:
      send_msg(uid,f"🔴 *VENTA {sym} RSI {rsi} PRECIO {price}*\nTu decides.")
      lm[sym]=now
    u["last_rsi_alert"]=lm
   save(db)
  except Exception as e:
   print(f"loop err {e} {traceback.format_exc()}"); time.sleep(60)

threading.Thread(target=check_loop,daemon=True).start()

@app.route(f"/{BOT}",methods=["POST"])
@app.route("/webhook",methods=["POST"])
def webhook():
 try:
  data=request.get_json()
  if "callback_query" not in data: return "ok"
  cb=data["callback_query"]; chat_id=cb["message"]["chat"]["id"]; cmd=cb["data"]
  db,uid=get_user(chat_id); u=db["users"][uid]
  btc,eth,xrp=get_prices()
  txt=None
  if cmd=="COMPRAR": u["entry"]=btc; txt=f"Entrada BTC {btc} guardada."
  elif cmd=="VENDER": u["entry"]=0; txt="Venta registrada."
  elif cmd=="SL":
   opts=[-3,-5,-7,-10]; cur=u.get("sl",-5); u["sl"]=opts[(opts.index(cur)+1)%len(opts)] if cur in opts else -5; txt=f"SL {u['sl']}%"
  elif cmd=="TP":
   opts=[5,10,15,20]; cur=u.get("tp",10); u["tp"]=opts[(opts.index(cur)+1)%len(opts)] if cur in opts else 10; txt=f"TP +{u['tp']}%"
  elif cmd=="APAGAR": u["on"]=False; txt="🔴 BOT APAGADO"
  elif cmd=="ACT": u["on"]=True; txt="🟢 BOT PRENDIDO - Alertará cada 5min BTC/ETH/XRP"
  elif cmd=="GRAF" or cmd=="PRO":
   rb=get_rsi("BTCUSDT"); re=get_rsi("ETHUSDT"); rx=get_rsi("XRPUSDT")
   send_msg(chat_id,f"V39.6.5 PRO\nBTC {btc} RSI {rb}\nETH {eth} RSI {re}\nXRP {xrp} RSI {rx}")
   txt=None
  if txt is not None:
   status="ON" if u.get("on") else "OFF"
   rx=get_rsi("XRPUSDT")
   final=f"V39.6.5 {status} SL:{u.get('sl')}% TP:+{u.get('tp')}%\nMXN:17.22 Ef:0.00\nBTC {btc} ETH {eth} XRP {xrp}\nXRP RSI {rx}\nTOTAL:999.88 (-0.0%)\n{txt}"
   btns=[[{"text":"COMPRAR","callback_data":"COMPRAR"},{"text":"VENDER","callback_data":"VENDER"}],[{"text":"SL","callback_data":"SL"},{"text":"TP","callback_data":"TP"}],[{"text":"GRAF","callback_data":"GRAF"},{"text":"PRO","callback_data":"PRO"}],[{"text":"Apagar","callback_data":"APAGAR"}],[{"text":"ACT","callback_data":"ACT"}]]
   send_msg(chat_id,final,btns)
  save(db)
 except Exception as e: print(f"wh err {e} {traceback.format_exc()}")
 return "ok"

def set_hook():
 time.sleep(4)
 try:
  base=os.environ.get("RENDER_EXTERNAL_URL") or os.environ.get("WEBHOOK_URL")
  if base:
   wh=f"{base}/{BOT}"
   requests.get(f"https://api.telegram.org/bot{BOT}/setWebhook?url={wh}",timeout=10)
   print(f"webhook {wh}")
 except Exception as e: print(e)
threading.Thread(target=set_hook,daemon=True).start()

if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
