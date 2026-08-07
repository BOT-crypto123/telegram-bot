import os,json,requests,threading,time,asyncio
from flask import Flask
from datetime import datetime
print("V39.6 SL/TP ALERT")
BOT=None
for k,v in os.environ.items():
 if "TELE" in k.upper() and "TOKEN" in k.upper():
  BOT=v
if not BOT: BOT=os.environ.get("BOT_TOKEN")
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k.upper() and "URL" in k.upper(): URL=v
 if "UPSTASH" in k.upper() and "TOKEN" in k.upper():
  if "REDIS" in k.upper() and v!=BOT: TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home(): return "V39.6 SL/TP LIVE"
def load():
 try:
  if not URL or not TOK: return {"users":{}}
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  res=r.json().get("result")
  if res: return json.loads(res)
 except: pass
 return {"users":{}}
def save(d):
 try: requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(d)],timeout=10)
 except: pass
def market():
 try:
  b=float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=8).json()["data"]["amount"])
  e=float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot",timeout=8).json()["data"]["amount"])
  x=float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot",timeout=8).json()["data"]["amount"])
  fx=17.22
  try: fx=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=5).json()["rates"]["MXN"]
  except: pass
  return b,e,x,fx
 except: return 64280,1898,1.02,17.22
def getu(uid,d):
 uid=str(uid)
 if uid not in d["users"]:
  b,e,x,fx=market()
  d["users"][uid]={"efectivo":0.0,"btc":(333.33/fx)/b,"eth":(333.33/fx)/e,"xrp":(333.33/fx)/x,"inicial":1000.0,"stoploss":7.0,"takeprofit":10.0,"precio_compra":{"btc":b,"eth":e,"xrp":x},"alert
