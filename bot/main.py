import os,requests,threading,time
from flask import Flask,request
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC"
SL=5.0
TP=10.0
ENTS={}
LAST={}
CHATS=set()
ABUY={}
def price(s):
 try:
  u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
  r=requests.get(u,timeout=8).json()
  return float(r["data"]["amount"])
 except:
  return 0
def get_hist(sym):
 try:
  mp={"BTC":"bitcoin","ETH":"ethereum","SOL":"solana","XRP":"ripple"}
  coin=mp.get(sym,"bitcoin")
  url="https://api.coingecko.com/api/v3/coins/"+coin+"/market_chart?vs_currency=usd&days=1"
  r=requests.get(url,timeout=10).json()
  arr=r.get("prices",[])
  out=[]
  for x in arr[-50:]:
   out.append(x[1])
  return out
 except:
  return []
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except:
  pass
def send_graf(cid,sym,p):
 try:
  hist=get_hist(sym)
  if len(hist)<5:
   hist=[p*0.99,p,p*1.01]
  plt.clf()
  plt.figure(figsize=(4,2))
  plt.plot(hist)
  plt.title(sym+" "+str(round(p,2)))
  plt.tight_layout()
  path="/tmp/g.png"
  plt.savefig(path)
  plt.close()
  u="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
  cap=sym+" "+str(round(p,2))
  with open(path,"rb") as f:
   requests.post(u,data={"chat_id":cid,"caption":cap},files={"photo":f},timeout=15)
 except:
  send_text(cid,sym+" "+str(round(p,2)))
def checker():
 while True:
  time.sleep(180)
  try:
   for sym in ["BTC","ETH","SOL","XRP"]:
    p=price(sym)
    if p==0:
     continue
    # ventas
    for k in list(ENTS.keys()):
     is_same = (k == sym)
     if is_same == False:
      continue
     ent=ENTS[k]["entry"]
     cid=ENTS[k]["chat"]
     pnl=(p/ent-1)*100
     sell=False
     if pnl < -SL + 0.001:
      sell=True
      send_text(cid,"ROJA VENDER "+k+" "+str(round(p,2))+" SL")
     if pnl > TP - 0.001:
      sell=True
      send_text(cid,"VERDE VENDER "+k+" "+str(round(p,2))+" TP")
     if sell:
      if k in ENTS:
       del ENTS[k]
    # compras
    if sym in LAST:
     ch=(p/LAST[sym]-1)*100
     if ch < -2.9:
      now=time.time()
      last=ABUY.get(sym,0)
      if now - last > 3600:
       for cid in CHATS:
        send_text(cid,"AZUL COMPRA "+sym+" "+str(round(p,2))+" cayo")
       ABUY[sym]=now
    LAST[sym]=p
  except:
   pass
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home():
 return "V51 LIVE",200
@app.route("/webhook",methods=["POST"])
def wh():
 global SEL,SL,TP
 try:
  d=request.get_json(force=True,silent=True)
  if d is None:
   return "ok",200
  if "message" not in d:
   return "ok",200
  cid=d["message"]["chat"]["id"]
  CHATS.add(cid)
  txt=d["message"].get("text","")
  t=txt.upper().strip()
  if t.startswith("SL "):
   try:
    SL=float(t.replace("SL","").replace("%","").strip())
   except:
    pass
   send_text(cid,"SL -"+str(SL)+"% OK")
   return "ok",200
  if t.startswith("TP "):
   try:
    TP=float(t.replace("TP","").replace("%","").strip())
   except:
    pass
   send_text(cid,"TP +"+str(TP)+"% OK")
   return "ok",200
  if t=="BTC" or t=="ETH" or t=="SOL" or t=="XRP":
   SEL=t
  p=price(SEL)
  if p==0:
   p=LAST.get(SEL,0)
  else:
   LAST[SEL]=p
  if "GRAF" in t:
   send_graf(cid,SEL,p)
   return "ok",200
  if "COMPRAR" in t:
   ENTS[SEL]={"entry":p,"chat":cid}
   send_text(cid,"ABIERTA "+SEL+" "+str(round(p,2)))
   return "ok",200
  if "VENDER" in t:
   if SEL in ENTS:
    del ENTS[SEL]
   send_text(cid,"CERRADA "+SEL)
   return "ok",200
  if "PRO" in t:
   if len(ENTS)==0:
    send_text
