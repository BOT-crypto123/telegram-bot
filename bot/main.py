import os,requests,threading,time
from flask import Flask,request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC";SL=5.0;TP=10.0
ENTS={};LAST={};CHATS=set();ABUY={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def send(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except: pass
def checker():
 while True:
  time.sleep(180)
  try:
   for sym in ["BTC","ETH","SOL","XRP"]:
    p=price(sym)
    if p==0: continue
    # checa ventas
    for k in list(ENTS.keys()):
     if k!=sym: continue
     ent=ENTS[k]["entry"]
     cid=ENTS[k]["chat"]
     pnl=(p/ent-1)*100
     if pnl<=-SL:
      send(cid,"🔴 VENDER "+k+" "+str(round(p,2))+" PnL "+str(round(pnl,2))+"% SL")
      del ENTS[k]
     if pnl>=TP:
      send(cid,"🟢 VENDER "+k+" "+str(round(p,2))+" PnL "+str(round(pnl,2))+"% TP")
      if k in ENTS: del ENTS[k]
    # checa compra -3%
    if sym in LAST:
     ch=(p/LAST[sym]-1)*100
     if ch<=-3:
      now=time.time()
      last=ABUY.get(sym,0)
      if now-last>3600:
       for cid in CHATS:
        send(cid,"🔵 COMPRA "+sym+" "+str(round(p,2))+" cayo "+str(round(ch,2))+"%")
       ABUY[sym]=now
    LAST[sym]=p
  except: pass
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home():
 return "V50 LIVE "+SEL,200
@app.route("/webhook",methods=["POST"])
def wh():
 global SEL,SL,TP
 try:
  d=request.get_json(force=True,silent=True)
  if not d or "message" not in d: return "ok",200
  cid=d["message"]["chat"]["id"]
  CHATS.add(cid)
  t=d["message"].get("text","").upper().strip()
  if t.startswith("SL "):
   try: SL=float(t.replace("SL","").replace("%","").strip())
   except: pass
   send(cid,"SL -"+str(SL)+"% OK")
   return "ok",200
  if t.startswith("TP "):
   try: TP=float(t.replace("TP","").replace("%","").strip())
   except: pass
   send(cid,"TP +"+str(TP)+"% OK")
   return "ok",200
  if t in ["BTC","ETH","SOL","XRP"]: SEL=t
  p=price(SEL)
  if p==0: p=LAST.get(SEL,0)
  else: LAST[SEL]=p
  if "COMPRAR" in t:
   ENTS[SEL]={"entry":p,"chat":cid}
   send(cid,"ABIERTA "+SEL+" "+str(round(p,2))+" Te aviso venta")
  elif "VENDER" in t:
   if SEL in ENTS: del ENTS[SEL]
   send(cid,"CERRADA "+SEL)
  elif "PRO" in t:
   if not ENTS: send(cid,"Sin partidas")
   else:
    s=""
    for k,v in ENTS.items():
     pp=price(k)
     pnl=(pp/v["entry"]-1)*100
     s+=k+" "+str(round(pnl,2))+"% "
    send(cid,s)
  else:
   send(cid,SEL+" "+str(round(p,2))+" SL -"+str(SL)+"% TP +"+str(TP)+"%")
  return "ok",200
 except: return "ok",200
if __name__=="__main__":
 app.run(host="0.0.0.0",port=int(os.environ.get("PORT",10000)))
