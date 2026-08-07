import os, json, requests, threading, time
from flask import Flask, request
print("V39.6.5 FIX")

BOT=os.environ.get("BOT_TOKEN")
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k and "URL" in k: URL=v
 if "UPSTASH" in k and "TOKEN" in k and v!=BOT and "REDIS" in k: TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home(): return "V39.6.5 LIVE"

def load():
 try:
  if not URL or not TOK: return {"users":{}}
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  j=r.json().get("result")
  if j: return json.loads(j)
 except: pass
 return {"users":{}}
def save(data):
 try: requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(data)],timeout=10)
 except: pass
def send_msg(cid,txt,btn=None):
 try:
  p={"chat_id":cid,"text":txt,"parse_mode":"Markdown"}
  if btn: p["reply_markup"]=json.dumps({"inline_keyboard":btn})
  requests.post(f"https://api.telegram.org/bot{BOT}/sendMessage",json=p,timeout=10)
 except: pass
def get_price(s):
 try: return float(requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={s}",timeout=5).json()["price"])
 except: return 0
def get_prices():
 return get_price("BTCUSDT") or 64293,get_price("ETHUSDT") or 1903,get_price("XRPUSDT") or 1.03
def get_rsi(sym):
 try:
  r=requests.get(f"https://api.binance.com/api/v3/klines?symbol={sym}&interval=1h&limit=100",timeout=8).json()
  cl=[float(c[4]) for c in r]
  dl=[cl[i]-cl[i-1] for i in range(1,len(cl))]
  gn=[d if d>0 else 0 for d in dl]
  ls=[-d if d<0 else 0 for d in dl]
  ag=sum(gn[-14:])/14; al=sum(ls[-14:])/14
  if al==0: return 70
  return round(100-(100/(1+ag/al)),1)
 except: return 50
def get_user(cid):
 db=load();uid=str(cid)
 if uid not in db.get("users",{}):
  db.setdefault("users",{})[uid]={"on":True,"sl":-5,"tp":10,"entry":0,"last_rsi_alert":{}};save(db)
 return db,uid
def check_loop():
 while True:
  try:
   time.sleep(300)
   db=load()
   if not db.get("users"): continue
   btc,eth,xrp=get_prices()
   rb=get_rsi("BTCUSDT"); reth=get_rsi("ETHUSDT"); rx=get_rsi("XRPUSDT")
   print(f"CHECK {rb} {reth} {rx}")
   for uid,u in db["users"].items():
    if not u.get("on",True): continue
    now=time.time(); lm=u.get("last_rsi_alert",{})
    for sym,price,rsi in [("BTC",btc,rb),("ETH",eth,reth),("XRP",xrp,rx)]:
     if now-lm.get(sym,0)<7200: continue
     if rsi<30:
      send_msg(uid,f"🟢 COMPRA {sym} RSI {rsi} {price}"); lm[sym]=now
     elif rsi>70:
      send_msg(uid,f"🔴 VENTA {sym} RSI {rsi} {price}"); lm[sym]=now
    u["last_rsi_alert"]=lm
   save(db)
  except: time.sleep(60)
threading.Thread(target=check_loop,daemon=True).start()

@app.route("/webhook",methods=["POST"])
@app.route("/"+(BOT or "hook"),methods=["POST"])
def webhook():
 try:
  data=request.get_json()
  if "message" in data and "text" in data["message"]:
   cid=data["message"]["chat"]["id"]; txt=data["message"]["text"]
   if "/start" in txt:
    db,uid=get_user(cid); u=db["users"][uid]; u["on"]=True
    btc,eth,xrp=get_prices(); rx=get_rsi("XRPUSDT")
    f=f"V39.6.5 ON SL:{u.get('sl',-5)}% TP:+{u.get('tp',10)}%\nBTC {btc} ETH {eth} XRP {xrp}\nRSI XRP {rx}"
    btn=[[{"text":"COMPRAR","callback_data":"COMPRAR"},{"text":"VENDER","callback_data":"VENDER"}],[{"text":"SL","callback_data":"SL"},{"text":"TP","callback_data":"TP"}],[{"text":"GRAF","callback_data":"GRAF"},{"text":"PRO","callback_data":"PRO"}],[{"text":"Apagar","callback_data":"APAGAR"}],[{"text":"ACT","callback_data":"ACT"}]]
    send_msg(cid,f,btn); save(db); return "ok"
  if "callback_query" in data:
   cb=data["callback_query"]; cid=cb["message"]["chat"]["id"]; cmd=cb["data"]
   db,uid=get_user(cid); u=db["users"][uid]; btc,eth,xrp=get_prices(); t=None
   if cmd=="COMPRAR": u["entry"]=btc; t=f"Entrada {btc}"
   elif cmd=="VENDER": u["entry"]=0; t="Venta"
   elif cmd=="SL":
    opts=[-3,-5,-7,-10]; cur=u.get("sl",-5); u["sl"]=opts[(opts.index(cur)+1)%4] if cur in opts else -5; t=f"SL {u['sl']}%"
   elif cmd=="TP":
    opts=[5,10,15,20]; cur=u.get("tp",10); u["tp"]=opts[(opts.index(cur)+1)%4] if cur in opts else 10; t=f"TP +{u['tp']}%"
   elif cmd=="APAGAR": u["on"]=False; t="APAGADO"
   elif cmd=="ACT": u["on"]=True; t="PRENDIDO"
   elif cmd=="PRO" or cmd=="GRAF":
    rb=get_rsi("BTCUSDT"); reth=get_rsi("ETHUSDT"); rx=get_rsi("XRPUSDT")
    send_msg(cid,f"BTC {btc} RSI {rb} ETH {eth} RSI {reth} XRP {xrp} RSI {rx}"); t=None
   if t is not None:
    rx=get_rsi("XRPUSDT"); f=f"V39.6.5 {'ON' if u.get('on') else 'OFF'} SL:{u.get('sl')}% TP:+{u.get('tp')}%\nBTC {btc} ETH {eth} XRP {xrp} RSI {rx}\n{t}"
    btn=[[{"text":"COMPRAR","callback_data":"COMPRAR"},{"text":"VENDER","callback_data":"VENDER"}],[{"text":"SL","callback_data":"SL"},{"text":"TP","callback_data":"TP"}],[{"text":"GRAF","callback_data":"GRAF"},{"text":"PRO","callback_data":"PRO"}],[{"text":"Apagar","callback_data":"APAGAR"}],[{"text":"ACT","callback_data":"ACT"}]]
    send_msg(cid,f,btn)
   save(db)
 except Exception as e: print(e)
 return "ok"

def set_hook():
 time.sleep(4)
 try:
  base=os.environ.get("RENDER_EXTERNAL_URL")
  if base and BOT: requests.get(f"https://api.telegram.org/bot{BOT}/setWebhook?url={base}/{BOT}",timeout=10)
 except: pass
threading.Thread(target=set_hook,daemon=True).start()
if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
