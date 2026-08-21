import os, json, requests, threading, time
from flask import Flask, request
app = Flask(__name__)
FILE="bot_data.json"
data={"b":5000.0,"pos":[],"gan_total":0.0,"coins":["BTC","ETH","SOL","XRP","DOGE","AVAX","LINK","ADA"],"alert_users":[]}

def load():
 if os.path.exists(FILE):
  try: data.update(json.load(open(FILE)))
  except: pass
def save(): json.dump(data,open(FILE,'w'))
load()

def P(s):
 try: return float(requests.get(f"https://data-api.binance.vision/api/v3/ticker/price?symbol={s}USDT",timeout=3).json()['price'])
 except: return 0
def C(s):
 try: return [float(x[4]) for x in requests.get(f"https://data-api.binance.vision/api/v3/klines?symbol={s}USDT&interval=1h&limit=80",timeout=5).json()]
 except: return []
def RSI(cl,p=14):
 if len(cl)<p+1: return 50
 g=l=0
 for i in range(1,p+1):
  d=cl[-i]-cl[-i-1]
  if d>0: g+=d
  else: l+=-d
 if l==0: return 100
 return 100-(100/(1+g/l))
def EMA(cl,p=20):
 if len(cl)<p: return cl[-1]
 k=2/(p+1); e=cl[0]
 for c in cl[1:]: e=c*k+e*(1-k)
 return e

@app.route('/webhook',methods=['POST'])
def wh():
 d=request.json
 if "message" in d:
  c=d["message"]["chat"]["id"]; t=d["message"].get("text","").upper().strip()
  if c not in data["alert_users"]: data["alert_users"].append(c)
  if t in data["coins"] and len(data["pos"])<5 and not any(p['sym']==t for p in data["pos"]):
   closes=C(t); rsi=RSI(closes); price=closes[-1] if closes else P(t)
   data["pos"].append({"sym":t,"monto":50,"entry":price}); data["b"]-=50; save()
 save()
 return {"ok":True}

def auto():
 time.sleep(10)
 while True:
  try:
   btc_c=0
   try: btc_c=float(requests.get("https://data-api.binance.vision/api/v3/ticker/24hr?symbol=BTCUSDT",timeout=3).json()['priceChangePercent'])
   except: pass
   for sym in data["coins"]:
    closes=C(sym)
    if not closes: continue
    rsi=RSI(closes); price=closes[-1]; ema=EMA(closes)
    # COMPRA
    if rsi<32 and price>ema*0.995 and btc_c>-1.5 and len(data["pos"])<5 and not any(p['sym']==sym for p in data["pos"]):
     data["pos"].append({"sym":sym,"monto":50,"entry":price,"max":0}); data["b"]-=50; save()
    # VENTA
    for p in data["pos"][:]:
     if p["sym"]==sym:
      gan=(price-p["entry"])/p["entry"]*100
      if gan>p.get("max",0): p["max"]=gan
      if gan>=2.5 or gan>=3.5 and rsi>60 or gan<=-2 or rsi>=72 or (p.get("max",0)>=4 and gan<=p["max"]-1):
       data["b"]+=50*(1+gan/100); data["gan_total"]+=50*gan/100; data["pos"].remove(p); save()
   time.sleep(180)
  except: time.sleep(10)

threading.Thread(target=auto,daemon=True).start()
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
