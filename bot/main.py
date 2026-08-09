import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
T=os.getenv("TELE_TOKEN") or ""
A=Flask(__name__)
S="XRP"
E={}
ON=False
CID=None
F="/tmp/b.json"
G="/tmp/a.json"
if os.path.exists(F):
 E=json.load(open(F)).get("ENTS",{})
if os.path.exists(G):
 d=json.load(open(G))
 ON=d.get("ON",False)
 CID=d.get("CID",None)
def prc(s):
 r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
 return float(r.get("data",{}).get("amount","0") or 0)
def cnd(sym):
 r=requests.get("https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60",headers={"User-Agent":"M"},timeout=10).json()
 return sorted(r)[-60:] if isinstance(r,list) else []
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
  if d>0:
   g+=d
  else:
   l+=-d
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
def snd(c,t):
 k={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","AUTO"]],"resize_keyboard":True}
 requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":c,"text":t,"reply_markup":k},timeout=10)
def loop():
 while True:
  time.sleep(600)
  if not ON or not CID:
   continue
  for s in ["BTC","ETH","SOL","XRP"]:
   cl=cnd(s)
   if not cl:
    continue
   cs=[a[4] for a in cl]
   if rsi(cs)<30:
    snd(CID,"AUTO COMPRA FUERTE "+s)
threading.Thread(target=loop,daemon=True).start()
@A.route("/")
def home():
 return "V231 LIVE",200
@A.route("/webhook",methods=["POST"])
def wh():
 global S,ON,CID
 d=request.get_json(force=True,silent=True)
 if not d:
  return "ok",200
 m=d.get("message",{})
 if not m:
  return "ok",200
 cid=m.get("chat",{}).get("id",0)
 txt=m.get("text","").upper()
 if "BTC" in txt:
  S="BTC"
 if "ETH" in txt:
  S="ETH"
 if "SOL" in txt:
  S="SOL"
 if "XRP" in txt:
  S="XRP"
 pn=prc(S)
 if "AUTO" in txt:
  ON=not ON
  CID=cid
  open(G,"w").write(json.dumps({"ON":ON,"CID":cid}))
  snd(cid,"AUTO ON" if ON else "AUTO OFF")
  return "ok",200
 if "GRAF" in txt:
  from PIL import Image,ImageDraw
  cl=cnd(S)
  cs=[a[4] for a in cl]
  p=prc(S)
  if p==0:
   p=cs[-1]
  rr=rsi(cs)
  e9=ema(cs,9)
  e21=ema(cs,21)
  pc=(p/cs[-2]-1)*100 if len(cs)>1 else 0
  sg="ESPERA"
  pr="LATERAL 50%"
  if rr<30:
   sg="COMPRA FUERTE"
   pr="SUBIDA FUERTE 85%"
  elif rr>70:
   sg="VENTA FUERTE"
   pr="BAJADA FUERTE 85%"
  elif e9 and e21 and e9[-1]>e21[-1]:
   sg="COMPRA"
   pr="SUBIDA 68%"
  elif e9 and e21 and e9[-1]<e21[-1]:
   sg="VENTA"
   pr="BAJADA 66%"
  mn=min(cs)
  mx=max(cs)
  if mn==mx:
   mn*=0.998
   mx*=1.002
  im=Image.new("RGB",(1000,560),(10,14,21))
  dr=ImageDraw.Draw(im)
  i=0
  for c in cl:
   x=20+i*13
   lo=c[1]
   hi=c[2]
   op=c[3]
   cc=c[4]
   y_lo=490-(lo-mn)/(mx-mn)*460
   y_hi=490-(hi-mn)/(mx-mn)*460
   y_op=490-(op-mn)/(mx-mn)*460
   y_cc=490-(cc-mn)/(mx-mn)*460
   y_top=min(y_op,y_cc)
   y_bot=max(y_op,y_cc)
   if y_top==y_bot:
    y_bot+=2
   col=(0,230,118) if cc>=op else (255,61,87)
   dr.line([x+3,y_lo,x+3,y_hi],fill=col)
   dr.rectangle([x,y_top,x+6,y_bot],fill=col)
   i+=1
  hr=(datetime.utcnow()-timedelta(hours=6)).strftime("%I:%M %p")
  e9v=str(round(e9[-1],2)) if e9 else "--"
  e21v=str(round(e21[-1],2)) if e21 else "--"
  sg2="+" if pc>=0 else ""
  cap=S+" "+str(round(p,4))+" | "+hr+" | "+sg2+str(round(pc,2))+"%\nEMA9:"+e9v+" EMA21:"+e21v+"\nRSI:"+str(round(rr,1))+" PRED:"+pr+"\nSENAL:"+sg+" V231"
  bio=io.BytesIO()
  bio.name="g.png"
  im.save(bio,"PNG")
  bio.seek(0)
  requests.post("https://api.telegram.org/bot"+T+"/sendPhoto",
