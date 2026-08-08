import os,requests,threading,time
from flask import Flask,request
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
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except:
  return
def send_graf(cid,sym,p):
 try:
  # grafica con quickchart sin librerias
  chart_url="https://quickchart.io/chart?c={type:'line',data:{labels:['-1h','-45m','-30m','-15m','ahora'],datasets:[{label:'"+sym+"',data:["+str(p*0.99)+","+str(p*0.995)+","+str(p*1.005)+","+str(p)+"]}]}}"
  u="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
  cap=sym+" "+str(round(p,2))+" SL -"+str(SL)+"% TP +"+str(TP)+"%"
  requests.post(u,json={"chat_id":cid,"caption":cap,"photo":chart_url},timeout=15)
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
       send_text(cid,"ROJA VENDER "+k+" SL")
       del ENTS[k]
      if pnl > TP:
       if k in ENTS:
        send_text(cid,"VERDE VENDER "+k+" TP")
        del ENTS[k]
    if sym in LAST:
     last_p=LAST[sym]
     ch=(p/last_p-1)*100
     if ch < -3:
      now=time.time()
      last=ABUY.get(sym,0)
      if now-last > 3600:
       for cid in CHATS:
        send_text(cid,"AZUL COMPRA "+sym)
       ABUY[sym]=now
    LAST[sym]=p
  except:
   time.sleep(5)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home():
 return "V52 LIVE",200
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
  if t.startswith("SL "):
   try:
    v=t.replace("SL","").replace("%","").strip()
    SL=float(v)
   except:
    pass
   send_text(cid,"SL OK -"+str(SL))
   return "ok",200
  if t.startswith("TP "):
   try:
    v=t.replace("TP","").replace("%","").strip()
    TP=float(v)
   except:
    pass
   send_text(cid,"TP OK +"+str(TP))
   return "ok",200
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
