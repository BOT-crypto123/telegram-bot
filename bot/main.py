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
 total=len(TRADES["trades"]);hoy=datetime.now(pytz.timezone("America/Mexico_City")).strftime("%d/%m/%Y")
 return f"📊 RESUMEN {hoy} - 10:00 PM\n---------------------------\n💰 Balance: ${TRADES.get('balance',0):.2f}\n📈 Hoy: ${TRADES.get('ganancia_hoy',0):.2f}\n✅ Ganados: {TRADES.get('ganados',0)} | ❌ Perdidos: {TRADES.get('perdidos',0)}\n📦 Trades: {total}\nBot V270 - AUTO {'ON' if O else 'OFF'}"
@A.route("/")
def h():return "V270 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,O,C,TRADES
 d=request.json or {};g=d.get("message",{});i=g.get("chat",{}).get("id",0)
 if not i:return "ok",200
 t=g.get("text","").upper()
 if "/BALANCE" in t or "/GANANCIAS" in t or "/RESUMEN" in t or "/REPORTE" in t:
  m(i,resumen_texto());return "ok",200
 if "BTC"in t:S="BTC"
 if "ETH"in t:S="ETH"
 if "SOL"in t:S="SOL"
 if "XRP"in t:S="XRP"
 if "AUTO"in t:O=not O;C=i;m(i,"AUTO ON"if O else"AUTO OFF");return "ok",200
 z=q(S)
 if not z:return "ok",200
 v=[]
 for c in z:
  try:v.append(float(c[4]))
  except:continue
 if not v:return "ok",200
 pr=p(S)or v[-1];uu=rsi(v);jj=em(v,9);kk=em(v,21);pc=(pr/v[-2]-1)*100 if len(v)>1 else 0
 sg="COMPRA"if uu<30 else"VENTA"if uu>70 else"ESPERA"
 pd="SUBIDA"if uu<30 or(30<=uu<50 and jj>kk)else"BAJADA"if uu>70 or(uu>50 and jj<kk)else"LATERAL"
 ms=""
 if"COMPRAR"in t:
  E[S]=pr;ms=f"COMPR
