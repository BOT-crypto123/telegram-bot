import os,json,requests,threading,time,asyncio
from flask import Flask
from datetime import datetime
print("V39.6.2 FIX CEL")
BOT=os.environ.get("BOT_TOKEN")
if not BOT:
 for k,v in os.environ.items():
  if "TELE" in k.upper() and "TOKEN" in k.upper():
   BOT=v
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
 return "V39.6.2 LIVE"
def load():
 try:
  if not URL or not TOK:
   return {"users":{}}
  r=requests.post(URL,headers={"Authorization":f"Bearer {TOK}"},json=["GET",KEY],timeout=10)
  j=r.json().get("result")
  if j:
   return json.loads(j)
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
  b=requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot",timeout=8).json()
  b=float(b["data"]["amount"])
  e=requests.get("https://api.coinbase.com/v2/prices/ETH-USD/spot",timeout=8).json()
  e=float(e["data"]["amount"])
  x=requests.get("https://api.coinbase.com/v2/prices/XRP-USD/spot",timeout=8).json()
  x=float(x["data"]["amount"])
  fx=17.22
  try:
   f=requests.get("https://api.exchangerate-api.com/v4/latest/USD",timeout=5).json()
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
 if "alertas" not in u:
  u["alertas"]=True
 if "ultima_alerta" not in u:
  u["ultima_alerta"]={}
 return u
def texto(u):
 b,e,x,fx=market()
 tot=u["efectivo"]
 tot+=u["btc"]*b*fx
 tot+=u["eth"]*e*fx
 tot+=u["xrp"]*x*fx
 gan=(tot-u["inicial"])/u["inicial"]*100
 al="ON" if u.get("alertas") else "OFF"
 t=f"V39.6.2 {al} SL:-{u['stoploss']:.0f}%"
 t+=f" TP:+{u['takeprofit']:.0f}%\n"
 t+=f"MXN:{fx:.2f} Ef:{u['efectivo']:.2f}\n"
 t+=f"BTC {b:.0f} ETH {e:.0f} XRP {x:.2f}\n"
 t+=f"TOTAL:{tot:.2f} ({gan:+.1f}%)"
 return t
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
def kb_main(u):
 a="Apagar" if u.get("alertas") else "Prender"
 b1=InlineKeyboardButton("COMPRAR",callback_data="menu_c")
 b2=InlineKeyboardButton("VENDER",callback_data="menu_v")
 b3=InlineKeyboardButton(f"SL -{u['stoploss']:.0f}%",callback_data="menu_sl")
 b4=InlineKeyboardButton(f"TP +{u['takeprofit']:.0f}%",callback_data="menu_tp")
 b5=InlineKeyboardButton("GRAFICA 7D",callback_data="grafica")
 b6=InlineKeyboardButton("PRO MAX",callback_data="pro")
 b7=InlineKeyboardButton(a,callback_data="toggle_alert")
 b8=InlineKeyboardButton("ACTUALIZAR",callback_data="act")
 r=[[b1,b2],[b3,b4],[b5,b6],[b7],[b8]]
 return InlineKeyboardMarkup(r)
def kb_pro():
 b1=InlineKeyboardButton("BTC PRO",callback_data="pro_btc")
 b2=InlineKeyboardButton("ETH PRO",callback_data="pro_eth")
 b3=InlineKeyboardButton("XRP PRO",callback_data="pro_xrp")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2],[b3],[b4]])
def kb_sl():
 b1=InlineKeyboardButton("-5%",callback_data="sl_5")
 b2=InlineKeyboardButton("-7%",callback_data="sl_7")
 b3=InlineKeyboardButton("-10%",callback_data="sl_10")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2,b3],[b4]])
def kb_tp():
 b1=InlineKeyboardButton("+10%",callback_data="tp_10")
 b2=InlineKeyboardButton("+15%",callback_data="tp_15")
 b3=InlineKeyboardButton("+20%",callback_data="tp_20")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2,b3],[b4]])
def kb_c():
 b1=InlineKeyboardButton("XRP $100",callback_data="c_xrp_100")
 b2=InlineKeyboardButton("BTC $100",callback_data="c_btc_100")
 b3=InlineKeyboardButton("ETH $100",callback_data="c_eth_100")
 b4=InlineKeyboardButton("Volver",callback_data="act")
 return InlineKeyboardMarkup([[b1,b2],[b3],[b4]])
def kb_v():
 b1=InlineKeyboardButton("Vender XRP",callback_data="v_xrp")
 b2=InlineKeyboardButton("Vender
