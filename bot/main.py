import os,requests,threading,time,io
from flask import Flask,request
from PIL import Image, ImageDraw
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC";SL=5.0;TP=10.0;ENTS={};LAST={};CHATS=set()
def price(s):
 try:
  u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
  r=requests.get(u,timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def get_candles(sym):
 try:
  mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT"}
  pair=mp.get(sym,"BTCUSDT")
  url="https://api.binance.com/api/v3/klines?symbol="+pair+"&interval=15m&limit=24"
  r=requests.get(url,timeout=10).json()
  out=[]
  for x in r:
   out.append([float(x[1]),float(x[2]),float(x[3]),float(x[4])])
  return out
 except: return []
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except: return
def send_graf(cid,sym,p):
 try:
  candles=get_candles(sym)
  if len(candles)<4:
   send_text(cid,sym+" "+str(round(p,2)))
   return
  W,H=800,400
  bg="#0a0a0a"
  img=Image.new("RGB",(W,H),bg)
  d=ImageDraw.Draw(img)
  lows=[c[2] for c in candles]; highs=[c[1] for c in candles]
  mn=min(lows); mx=max(highs)
  if mx==mn: mx=mn*1.01
  pad=20
  def y_of(v): return H-pad - (v-mn)/(mx-mn)*(H-pad*2)
  bw=W//len(candles)//2
  for i,c in enumerate(candles):
   o,h,l,cl=c
   x=i*(W//len(candles))+bw
   col="#00ff88" if cl>=o else "#ff3333"
   # mecha
   d.line([x,y_of(h),x,y_of(l)],fill=col,width=1)
   # cuerpo
   top=min(y_of(o),y_of(cl)); bot=max(y_of(o),y_of(cl))
   if abs(bot-top)<2: bot=top+3
   d.rectangle([x-bw//2,top,x+bw//2,bot],fill=col)
  # titulo
  d.text((10,10),sym+" "+str(round(p,2)),fill="white")
  bio=io.BytesIO(); bio.name="graf.png"
  img.save(bio,"PNG"); bio.seek(0)
  u="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
  requests.post(u,data={"chat_id":cid,"caption":sym+" "+str(round(p,2))+" SL -"+str(SL)+"% TP +"+str(TP)+"%"},files={"photo":bio},timeout=15)
 except Exception as e:
  send_text(cid,sym+" "+str(round(p,2))+" err")
def checker():
 while True:
  time.sleep(180)
  try:
   for sym in ["BTC","ETH","SOL","XRP"]:
    p=price(sym)
    if p<1: continue
    for k in list(ENTS.keys()):
     if k==sym:
      ent=ENTS[k]["entry"]; cid=ENTS[k]["chat"]
      pnl=(p/ent-1)*100
      if pnl < -SL:
       send_text(cid,"ROJA VENDER "+k+" "+str(round(p,2))); del ENTS[k]
      if pnl > TP:
       if k in ENTS:
        send_text(cid,"VERDE VENDER "+k+" "+str(round(p,2))); del ENTS[k]
    LAST[sym]=p
  except: time.sleep(5)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home(): return "V55 VELAS PIL",200
@app.route("/webhook",methods=["POST"])
def wh():
 global SEL
 try:
  d=request.get_json(force=True,silent=True)
  if not d or "message" not in d: return "ok",200
  cid=d["message"]["chat"]["id"]
  CHATS.add(cid)
  t=d["message"].get("text","").upper().strip()
  if t in ["BTC","ETH","SOL","XRP"]: SEL=t
  p=price(SEL)
  if p<1: p=LAST.get(SEL,0)
  if "GRAF" in t:
   send_graf(cid,SEL,p); return "ok",200
  if "COMPRAR" in t:
   ENTS[SEL]={"entry":p,"chat":cid}
   send_text(cid,"ABIERTA "+SEL+" "+str(round(p,2))); return "ok",200
  if "VENDER" in t:
   if SEL in ENTS: del ENTS[SEL]
   send_text(cid,"CERRADA "+SEL); return "ok",200
  if "PRO" in t:
   if len(ENTS)==0: send_text(cid,"Sin partidas")
   else:
    out=""
    for k,v in ENTS.items():
     pp=price(k)
     if pp<1: pp=v["entry"]
     pnl=(pp/v["entry"]-1)*100
     out+=k+" "+str(round(pnl,2))+"% "
    send_text(cid,out)
   return "ok",200
  send_text(cid,SEL+" "+str(round(p,2)))
  return "ok",200
 except: return "ok",200
if __name__=="__main__":
 app.run(host
