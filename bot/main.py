import os,json,requests,threading,time,asyncio
from flask import Flask
from datetime import datetime
print("V39.6.1 SL/TP FIX")
BOT=None
for k,v in os.environ.items():
 if "TELE" in k.upper() and "TOKEN" in k.upper():
  BOT=v
if not BOT:
 BOT=os.environ.get("BOT_TOKEN")
URL=os.environ.get("UPSTASH_REDIS_REST_URL")
TOK=os.environ.get("UPSTASH_REDIS_REST_TOKEN")
for k,v in os.environ.items():
 if "UPSTASH" in k.upper() and "URL" in k.upper():
  URL=v
 if "UPSTASH" in k.upper() and "TOKEN" in k.upper():
  if "REDIS" in k.upper() and v!=BOT:
   TOK=v
KEY="btc-vicente-v36-1-final"
app=Flask(__name__)
@app.route("/")
def home():
 return "V39.6.1 LIVE"
def load():
 try:
  if not URL or not TOK:
   return {"users":{}}
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  res=r.json().get("result")
  if res:
   return json.loads(res)
 except:
  pass
 return {"users":{}}
def save(d):
 try:
  requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["SET",KEY,json.dumps(d)],timeout=10)
 except:
  pass
def market():
 try:
  b=float(requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=8).json()["data"]["amount"])
  e=float(requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot",timeout=8).json()["data"]["amount"])
  x=float(requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot",timeout=8).json()["data"]["amount"])
  fx=17.22
  try:
   fx=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=5).json()["rates"]["MXN"]
  except:
   pass
  return b,e,x,fx
 except:
  return 64280,1898,1.02,17.22
def getu(uid,d):
 uid=str(uid)
 if uid not in d["users"]:
  b,e,x,fx=market()
  nuevo={}
  nuevo["efectivo"]=0.0
  nuevo["btc"]=(333.33/fx)/b
  nuevo["eth"]=(333.33/fx)/e
  nuevo["xrp"]=(333.33/fx)/x
  nuevo["inicial"]=1000.0
  nuevo["stoploss"]=7.0
  nuevo["takeprofit"]=10.0
  nuevo["precio_compra"]={}
  nuevo["precio_compra"]["btc"]=b
  nuevo["precio_compra"]["eth"]=e
  nuevo["precio_compra"]["xrp"]=x
  nuevo["alertas"]=True
  nuevo["ultima_alerta"]={}
  d["users"][uid]=nuevo
  save(d)
 u=d["users"][uid]
 if "alertas" not in u:
  u["alertas"]=True
 if "ultima_alerta" not in u:
  u["ultima_alerta"]={}
 return u
def texto(u):
 b,e,x,fx=market()
 tot=u["efectivo"]+u["btc"]*b*fx+u["eth"]*e*fx+u["xrp"]*x*fx
 gan=(tot-u["inicial"])/u["inicial"]*100
 al="ON" if u.get("alertas") else "OFF"
 s=f"V39.6.1 {al} SL:-{u['stoploss']:.0f}% TP:+{u['takeprofit']:.0f}%\n"
 s+=f"MXN:{fx:.2f} Ef:{u['efectivo']:.2f}\n"
 s+=f"BTC {b:.0f} ETH {e:.0f} XRP {x:.2f}\n"
 s+=f"TOTAL:{tot:.2f} ({gan:+.1f}%)"
 return s
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
def kb_main(u):
 t="Apagar" if u.get("alertas") else "Prender"
 r=[]
 r.append([InlineKeyboardButton("COMPRAR",callback_data="menu_c"),InlineKeyboardButton("VENDER",callback
