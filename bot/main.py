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
def get_candles(sym):
 try:
  mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT"}
  pair=mp.get(sym,"BTCUSDT")
  url="https://api.binance.com/api/v3/klines?symbol="+pair+"&interval=15m&limit=30"
  r=requests.get(url,timeout=10).json()
  out=[]
  for x in r:
   o=float(x[1]); h=float(x[2]); l=float(x[3]); c=float(x[4])
   out.append([o,h,l,c])
  return out
 except:
  return []
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except:
  return
def send_graf(cid,sym,p):
 try:
  candles=get_candles(sym)
  if len(candles)<5:
   send_text(cid,sym+" "+str(round(p,2)))
   return
  plt.clf()
  fig,ax=plt.subplots(figsize=(5,3))
  fig.patch.set_facecolor('#0e0e0e')
  ax.set_facecolor('#0e0e0e')
  for i in range(len(candles)):
   o,h,l,c=candles[i]
   col='green' if c>=o else 'red'
   ax.plot([i,i],[l,h],color=col,linewidth=1)
   ax.plot([i,i],[o,c],color=col,linewidth=4)
  ax.set_title(sym+" "+str(round(p,2)),color='white')
  ax.tick_params(colors='white')
  plt.tight_layout()
  path="/tmp/g.png"
  plt.savefig(path,facecolor=fig.get_facecolor())
  plt.close()
  u="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
  cap=sym+" "+str(round(p,2))+" SL -"+str(SL)+"% TP +"+str(TP)+"%"
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
    if p < 1:
     continue
    for k in list(ENTS.keys()):
     if k == sym:
      ent=ENTS[k]["entry"]
      cid=ENTS[k]["chat"]
      pnl=(p/ent-1)*100
      if pnl < -SL:
       send_text(cid,"ROJA VENDER "+k)
       del ENTS[k]
      if pnl > TP:
       if k in ENTS:
        send_text(cid,"VERDE VENDER "+k)
        del ENTS[k]
    LAST[sym]=p
  except:
   time.sleep(5)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home():
 return "V53 VELAS LIVE",200
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
  msg=d["message"].get("text","")
  t=msg.upper().strip()
  if t=="BTC" or t=="ETH" or t=="SOL" or t=="XRP":
   SEL=t
  p=price(SEL)
  if p < 1:
   p=LAST.get(SEL,0)
  if "GRAF" in t:
   send_graf(cid,SEL,p)
   return "ok",200
  if "COMPRAR" in t:
   ENTS[SEL]={"entry":p,"chat":cid}
   send_text(cid,"ABIERTA "+SEL)
   return "ok",200
  if "VENDER" in t:
   if SEL in ENTS:
    del ENTS[SEL]
   send_text(cid,"CERRADA "+SEL)
   return "ok",200
  if "PRO" in t:
   if len(ENTS)==0:
    send_text(cid,"Sin partidas")
   else:
    out=""
    for k,v in ENTS.items():
     pp=price(k)
     if pp < 1:
      pp=v["entry"]
     pnl=(pp/v["entry"]-1)*100
     out=out+k+" "+str(round(pnl,2))+"% "
    send_text(cid,out)
   return "ok",200
  send_text(cid,SEL+" "+str(round(p,2)))
  return "ok",200
 except:
  return "ok",200
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
