import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
TOKEN=os.getenv("TELE_TOKEN") or ""
print("V215 TOKEN",len(TOKEN),flush=True)
app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b215.json"
AUTO_FILE="/tmp/auto215.json"
AUTO=False
AUTO_CID=None
if os.path.exists(FILE):
 d=json.load(open(FILE))
 ENTS.update(d.get("ENTS",{}))
if os.path.exists(AUTO_FILE):
 a=json.load(open(AUTO_FILE))
 AUTO=a.get("ON",False)
 AUTO_CID=a.get("CID",None)
print("V215 LOADED AUTO",AUTO,flush=True)
def price(s):
 u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
 r=requests.get(u,timeout=8).json()
 return float(r.get("data",{}).get("amount","0") or 0)
def candles(sym):
 u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
 r=requests.get(u,headers={"User-Agent":"M"},timeout=10).json()
 return sorted(r)[-70:] if isinstance(r,list) else []
def ema(p,n):
 if len(p)<n:
  return []
 k=2/(n+1)
 m=sum(p[:n])/n
 o=[m]
 for x in p[n:]:
  o.append(x*k+o[-1]*(1-k))
 return o
def rsi(p):
 if len(p)<15:
  return 50
 g=l=0
 for i in range(1,15):
  d=p[i]-p[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
def send(c,t):
 u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
 k={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","AUTO"]],"resize_keyboard":True}
 requests.post(u,json={"chat_id":c,"text":t,"reply_markup":k},timeout=10)
def check_and_trade(sym,cid,auto_mode=False):
 try:
  cl=candles(sym)
  if len(cl)==0:
   return None
  cs=[c[4] for c in cl]
  p=cs[-1]
  tp=price(sym)
  p=tp if tp!=0 else p
  e9=ema(cs,9)
  e21=ema(cs,21)
  rr=rsi(cs)
  if len(e9)==0 or len(e21)==0:
   return None
  a=e9[-1]
  b=e21[-1]
  if rr<30 and sym not in ENTS:
   ENTS[sym]={"entry":p}
   open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
   if auto_mode:
    return "🚨🚨🚨 AUTO COMPRA EJECUTADA 🚨🚨🚨\n"+sym+" A "+str(round(p,4))+"\nRSI: "+str(int(rr))+" BARATISIMO\nE9: "+str(round(a,3))+"\nMODO: AUTOMATICO ON"
   else:
    return "🚨 ALERTA COMPRA FUERTE "+sym+" 🚨"
  if rr>70 and sym in ENTS:
   en=ENTS[sym]["entry"]
   pnl=(p/en-1)*100
   del ENTS[sym]
   open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
   if auto_mode:
    return "🚨🚨🚨 AUTO VENTA EJECUTADA 🚨🚨🚨\n"+sym+" A "+str(round(p,4))+"\nGANANCIA: "+str(round(pnl,2))+"%\nRSI: "+str(int(rr))+" CARO\nMODO: AUTOMATICO ON"
   else:
    return "🚨 ALERTA VENTA FUERTE "+sym+" 🚨"
  if p>a and a>b and rr<35 and sym not in ENTS and auto_mode:
   ENTS[sym]={"entry":p}
   open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
   return "🚨 AUTO COMPRA "+sym+" 🚨\nPRECIO: "+str(round(p,4))+"\nRSI: "+str(int(rr))+"\nTENDENCIA ALCISTA"
  if p<a and a<b and rr>65 and sym in ENTS and auto_mode:
   en=ENTS[sym]["entry"]
   pnl=(p/en-1)*100
   del ENTS[sym]
   open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
   return "🚨 AUTO VENTA "+sym+" 🚨\nPRECIO: "+str(round(p,4))+"\nPNL: "+str(round(pnl,2))+"%"
 except:
  return None
 return None
def auto_loop():
 global AUTO
 print("V215 AUTO LOOP START",flush=True)
 while True:
  time.sleep(600)
  if not AUTO or not AUTO_CID:
   continue
  print("V215 AUTO TRADE CHECK",flush=True)
  for s in ["BTC","ETH","SOL","XRP"]:
   msg=check_and_trade(s,AUTO_CID,True)
   if msg:
    send(AUTO_CID,msg)
    time.sleep(3)
threading.Thread(target=auto_loop,daemon=True).start()
@app.route("/")
def home():
 return "V215 LIVE AUTO TRADER "+str(AUTO),200
@app.route("/webhook",methods=["POST"])
def wh():
 global SEL,AUTO,AUTO_CID
 d=request.get_json(force=True,silent=True)
 if not d or "message" not in d:
  return "ok",200
 cid=d["message"]["chat"]["id"]
 txt=d["message"].get("text","").upper().strip()
 SEL="BTC" if "BTC" in txt else SEL
 SEL="ETH" if "ETH" in txt else SEL
 SEL="SOL" if "SOL" in txt else SEL
 SEL="XRP" if "XRP" in txt else SEL
 pn=price(SEL)
 if pn==0 and SEL in ENTS:
  pn=ENTS[SEL]["entry"]
 if "AUTO" in txt:
  AUTO=not AUTO
  AUTO_CID=cid
  open(AUTO_FILE,"w").write(json.dumps({"ON":AUTO,"CID":cid}))
  if AUTO:
   send(cid,"🤖 AUTO TRADING ON 🤖\nMODO: COMPRAS Y VENTAS AUTOMATICAS ACTIVADAS\nCADA 10 MIN REVISO BTC ETH SOL XRP\nSI RSI<30 COMPRO SOLO\nSI RSI>70 VENDO SOLO\nAVISOS EN MAYUSCULAS\n\n🚨 RIESGO: USA DINERO SIMULADO")
  else:
   send(cid,"🔕 AUTO TRADING OFF 🔕\nMODO MANUAL\nYA NO COMPRO SOLO")
  return "ok
