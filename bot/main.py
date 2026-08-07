import os,json,requests
import threading,time,asyncio
from flask import Flask
from datetime import datetime
print("V39.6.3 FIX CEL")
BOT=os.environ.get("BOT_TOKEN")
if not BOT:
 for k,v in os.environ.items():
  if "TELE" in k and "TOKEN" in k:
   BOT=v
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k and "URL" in k:
  URL=v
 if "UPSTASH" in k and "TOKEN" in k:
  if "REDIS" in k and v!=BOT:
   TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home():
 return "V39.6.3 LIVE"
def load():
 try:
  if not URL or not TOK:
   return {"users":{}}
  r=requests.post(URL,headers={
   "Authorization":f"Bearer {TOK}"
  },json=["GET",KEY],timeout=10)
  j=r.json().get("result")
  if j:
   return json.loads(j)
 except:
  pass
 return {"users":{}}
def save(d):
 try:
  requests.post(URL,headers={
   "Authorization":f"Bearer {TOK}"
  },json=["SET",KEY,json.dumps(d)],timeout=10)
 except:
  pass
def market():
 try:
  a="https://api.coinbase.com/v2/prices/"
  b=requests.get(a+"BTC-USD/spot",timeout=8).json()
  b=float(b["data"]["amount"])
  e=requests.get(a+"ETH-USD/spot",timeout=8).json()
  e=float(e["data"]["amount"])
  x=requests.get(a+"XRP-USD/spot",timeout=8).json()
  x=float(x["data"]["amount"])
  fx=17.22
  try:
   f=requests.get(
    "https://api.exchangerate-api.com/v4/latest/USD",
    timeout=5).json()
   fx=f["rates"]["MXN"]
  except:
   pass
  return b,e,x,fx
 except:
  return 64000,1890,1.02,17.22
def getu(uid,d):
 uid=str(uid)
 if uid not in d["users"]:
  b,e,x,fx=market()
  u={}
  u["efectivo"]=0.0
  u["btc"]=(333.33/fx)/b
  u["eth"]=(333.33/fx)/e
  u["xrp"]=(333.33/fx)/x
  u["inicial"]=1000.0
  u["stoploss"]=7.0
  u["takeprofit"]=10.0
  u["precio_compra"]={}
  u["precio_compra"]["btc"]=b
  u["precio_compra"]["eth"]=e
  u["precio_compra"]["xrp"]=x
  u["alertas"]=True
  u["ultima_alerta"]={}
  d["users"][uid]=u
  save(d)
 u=d["users"][uid]
