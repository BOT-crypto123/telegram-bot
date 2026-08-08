import os,requests,threading,time,io,random
from flask import Flask,request
TOKEN=os.getenv("TELE_TOKEN") or os.getenv("BOT_TOKEN") or ""
app=Flask(__name__)
SEL="BTC";SL=5.0;TP=10.0;ENTS={};LAST={}
def price(s):
 try:
  r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
  return float(r["data"]["amount"])
 except: return 0
def get_candles(sym):
 try:
  mp={"BTC":"BTCUSDT","ETH":"ETHUSDT","SOL":"SOLUSDT","XRP":"XRPUSDT"}
  pair=mp.get(sym,"BTCUSDT")
  url="https://api.binance.com/api/v3/klines?symbol="+pair+"&interval=15m&limit=30"
  r=requests.get(url,timeout=6).json()
  if isinstance(r,list) and len(r)>5:
   out=[]
   for x in r: out.append([float(x[1]),float(x[2]),float(x[3]),float(x[4])])
   return out
  return []
 except: return []
def send_text(cid,txt):
 try:
  u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
  requests.post(u,json={"chat_id":cid,"text":txt,"reply_markup":kb},timeout=10)
 except: return

def send_graf(cid,sym,p):
 try:
  from PIL import Image, ImageDraw
  candles=get_candles(sym)
  if len(candles)<5:
   candles=[]
   base=p if p>0 else 65000
   for i in range(30):
    o=base*(1+random.uniform(-0.005,0.005))
    c=o*(1+random.uniform(-0.008,0.008))
    h=max(o,c)*(1+random.uniform(0,0.003))
    l=min(o,c)*(1-random.uniform(0,0.003))
    candles.append([o,h,l,c])
    base=c

  W,H=900,480
  img=Image.new("RGB",(W,H),"#0a0a0a")
  d=ImageDraw.Draw(img)
  mn=min([c[2] for c in candles]); mx=max([c[1] for c in candles])
  # AJUSTA PARA QUE SE VEA LA ENTRADA
  entry=None
  if sym in ENTS: entry=ENTS[sym]["entry"]
  if entry:
   mn=min(mn,entry*0.995); mx=max(mx,entry*1.005)
  if mx==mn: mx=mn*1.01
  pad=50
  def yf(v): return H-pad - (v-mn)/(mx-mn)*(H-pad*2-20)
  step=W//len(candles); bw=max(4,step-6)
  for i,c in enumerate(candles):
   o,h,l,cl=c
   x=i*step+bw//2+15
   col="#00ff88" if cl>=o else "#ff3b3b"
   d.line([x,yf(h),x,yf(l)],fill=col,width=2)
   top=min(yf(o),yf(cl)); bot=max(yf(o),yf(cl))
   if bot-top<3: bot=top+4
   d.rectangle([x-bw//2,top,x+bw//2,bot],fill=col)

  # LINEA AMARILLA ENTRADA + SL/TP
  if entry:
   ye=yf(entry)
   d.line([0,ye,W,ye],fill="#ffcc00",width=2)
   d.text((15,ye-18),"ENTRADA "+str(round(entry,2)),fill="#ffcc00")
   # SL
   ysl=yf(entry*(1-SL/100))
   d.line([0,ysl,W,ysl],fill="#ff3b3b",width=1)
   d.text((W-140,ysl-12),"SL -"+str(SL)+"%",fill="#ff3b3b")
   # TP
   ytp=yf(entry*(1+TP/100))
   d.line([0,ytp,W,ytp],fill="#00ff88",width=1)
   d.text((W-140,ytp-12),"TP +"+str(TP)+"%",fill="#00ff88")

  d.text((15,10),sym+" "+str(round(p,2)),fill="white")
  bio=io.BytesIO(); bio.name="graf.png"
  img.save(bio,"PNG"); bio.seek(0)
  u="https://api.telegram.org/bot"+TOKEN+"/sendPhoto"
  requests.post(u,data={"chat_id":cid},files={"photo":bio},timeout=20)
  return
 except Exception as e:
  print("ERR",e)
  send_text(cid,sym+" "+str(round(p,2)))

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
       send_text(cid,"ROJA VENDER "+k+" "+str(round(p,2))+" "+str(round(pnl,2))+"%"); del ENTS[k]
      if pnl > TP:
       if k in ENTS:
        send_text(cid,"VERDE VENDER "+k+" "+str(round(p,2))+" "+str(round(pnl,2))+"%"); del ENTS[k]
    LAST[sym]=p
  except: time.sleep(5)
threading.Thread(target=checker,daemon=True).start()
@app.route("/")
def home(): return "V59 ENTRADA LINE",200
@app.route("/webhook",methods=["POST"])
def wh():
 global SEL
 try:
  d=request.get_json(force=True,silent=True)
  if not d or "message" not in d: return "ok",200
  cid=d["message"]["chat"]["id"]
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
     out+=k+" "+str(round((pp/v["entry"]-1)*100,2))+"% "
    send_text(cid,out)
   return "ok",200
  send_text(cid,SEL+" "+str(round(p,2))); return "ok",200
 except: return "ok",200
if __name__=="__main__":
  port=int(os.getenv("PORT","10000"))
  app.run(host="0.0.0.0",port=port)
