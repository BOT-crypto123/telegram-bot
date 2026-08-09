import os,requests,io,json,time,threading as th
from flask import Flask,request
from datetime import datetime
import pytz

T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP";E={};O=False;C=0
FILE="bot/trades.json"
if not os.path.exists(FILE): FILE="trades.json"

def load_trades():
 try:
  if os.path.exists(FILE):
   with open(FILE,"r") as f:
    d=json.load(f)
    if not isinstance(d, dict) or "trades" not in d:
     return {"trades":[],"balance":0,"ganancia_hoy":0,"ganados":0,"perdidos":0}
    return d
 except: pass
 return {"trades":[],"balance":0,"ganancia_hoy":0,"ganados":0,"perdidos":0}
 try:
  if os.path.exists(FILE):
   with open(FILE,"r") as f: return json.load(f)
 except: pass
 return {"trades":[],"balance":0,"ganancia_hoy":0,"ganados":0,"perdidos":0}

def save_trades(data):
 try:
  with open(FILE,"w") as f: json.dump(data,f)
 except: pass

TRADES=load_trades()

def p(s):
 try:
  j=requests.get(f"https://api.coinbase.com/v2/prices/{s}-USD/spot",timeout=8).json()
  return float(j["data"]["amount"])
 except:return 0
def q(s):
 try:
  j=requests.get(f"https://api.exchange.coinbase.com/products/{s}-USD/candles?granularity=60",timeout=10).json()
  if not isinstance(j,list):return []
  o=[]
  for c in j:
   try:float(c[4]);o.append(c)
   except:continue
  return sorted(o)[-60:]
 except:return []
def rsi(a):
 if len(a)<15:return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0;l+=-d if d<0 else 0
 return 88 if l==0 else 100-100/(1+g/l)
def em(a,n):
 if len(a)<n:return a[-1]
 k=2.0/(n+1.0);e=a[0]
 for x in a[1:]:e=x*k+e*(1-k)
 return e
def m(x,t):
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["AUTO"]],"resize_keyboard":True}
 try:requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":kb},timeout=8)
 except:pass

def resumen_texto():
 total = len(TRADES["trades"])
 hoy = datetime.now(pytz.timezone("America/Mexico_City")).strftime("%d/%m/%Y")
 gan = TRADES.get("ganancia_hoy",0)
 bal = TRADES.get("balance",0)
 g = TRADES.get("ganados",0)
 p_ = TRADES.get("perdidos",0)
 return f"📊 RESUMEN {hoy} - 10:00 PM\n---------------------------\n💰 Balance acumulado: ${bal:.2f}\n📈 Ganancia hoy: ${gan:.2f}\n✅ Ganados: {g} | ❌ Perdidos: {p_}\n📦 Total trades: {total}\nBot V270 - AUTO {'ON' if O else 'OFF'}"

@A.route("/")
def h():return "V270 LIVE",200

@A.route("/webhook",methods=["POST"])
def w():
 global S,E,O,C,TRADES
 d=request.json or {};g=d.get("message",{});i=g.get("chat",{}).get("id",0)
 if not i:return "ok",200
 t=g.get("text","").upper()

 # COMANDOS NUEVOS DE GANANCIAS
 if "/BALANCE" in t or "/GANANCIAS" in t or "/RESUMEN" in t or "/REPORTE" in t:
  m(i,resumen_texto());return "ok",200

 if "BTC"in t:S="BTC"
 if "ETH"in t:S="ETH"
 if "SOL"in t:S="SOL"
 if "XRP"in t:S
