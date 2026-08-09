import os,requests,io,json
from flask import Flask,request
from datetime import datetime,timedelta
TOKEN=os.getenv("TELE_TOKEN") or ""
print("V212 TOKEN",len(TOKEN),flush=True)
app=Flask(__name__)
SEL="XRP"
ENTS={}
FILE="/tmp/b212.json"
if os.path.exists(FILE):
 d=json.load(open(FILE))
 ENTS.update(d.get("ENTS",{}))
print("V212 LOADED",flush=True)
def price(s):
 u="https://api.coinbase.com/v2/prices/"+s+"-USD/spot"
 r=requests.get(u,timeout=8).json()
 return float(r.get("data",{}).get("amount","0") or 0)
def candles(sym):
 u="https://api.exchange.coinbase.com/products/"+sym+"-USD/candles?granularity=60"
 r=requests.get(u,headers={"User-Agent":"M"},timeout=10).json()
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
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
def send(c,t):
 u="https://api.telegram.org/bot"+TOKEN+"/sendMessage"
 k={"keyboard":[["BTC","ETH"],["SOL","XRP"],["COMPRAR","VENDER"],["GRAF","PRO"]],"resize_keyboard":True}
 requests.post(u,json={"chat_id":c,"text":t,"reply_markup":k},timeout=10)
@app.route("/")
def home():
 return "V212 LIVE",200
@app.route("/webhook",methods=["POST"])
def wh():
 global SEL
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
 if "GRAF" in txt:
  from PIL import Image,ImageDraw
  cl=candles(SEL)
  if len(cl)==0:
   send(cid,"X")
   return "ok",200
  cs=[c[4] for c in cl]
  p=cs[-1]
  tp=price(SEL)
  p=tp if tp!=0 else p
  e9=ema(cs,9)
  e21=ema(cs,21)
  rr=rsi(cs)
  pr="N"
  se="E"
  sc=50
  if len(e9)>0 and len(e21)>0:
   a=e9[-1]
   b=e21[-1]
   if p>a and a>b:
    pr="S"
    se="C"
    sc=68
   if p<a and a<b:
    pr="B"
    se="V"
    sc=66
   if rr<30:
    pr="F"
    se="C"
    sc=92
   if rr>70:
    pr="F"
    se="V"
    sc=91
  mn=min(cs)
  mx=max(cs)
  if mn==mx:
   mn=mn*0.998
   mx=mx*1.002
  W,H=1000,560
  im=Image.new("RGB",(W,H),(10,14,21))
  dr=ImageDraw.Draw(im)
  i=0
  for c in cl:
   x=20+i*13
   lo,hi,o,cc=c[1],c[2],c[3],c[4]
   y1=H-70-(lo-mn)/(mx-mn)*(H-100)
   y2=H-70-(hi-mn)/(mx-mn)*(H-100)
   yo=H-70-(o-mn)/(mx-mn)*(H-100)
   yc=H-70-(cc-mn)/(mx-mn)*(H-100)
   yt=min(yo,yc)
   yb=max(yo,yc)
   yb=yt+2 if yt==yb else yb
   col=(0,230,118) if cc>=o else (255,61,87)
   dr.line([x+3,y1,x+3,y2],fill=col)
   dr.rectangle([x,yt,x+6,yb],fill=col)
   i+=1
  hr=(datetime.utcnow()-timedelta(hours=6)).strftime("%H:%M")
  e9s=str(round(e9[-1],1)) if len(e9)>0 else "--"
  e21s=str(round(e21[-1],1)) if len(e21)>0 else "--"
  cap=SEL+" "+str(round(p,2))+" "+hr+"\nE9:"+e9s+" E21:"+e21s+"\nR:"+str(int(rr))+" P:"+pr+" "+str(sc)+"%\n"+se+" V212"
  bio=io.BytesIO()
  bio.name="g.png"
  im.save(bio,"PNG")
  bio.seek(0)
  requests.post("https://api.telegram.org/bot"+TOKEN+"/sendPhoto",data={"chat_id":cid,"caption":cap},files={"photo":bio},timeout=12)
  return "ok",200
 if "COMPRAR" in txt:
  ENTS[SEL]={"entry":pn}
  open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
  send(cid,"OK")
  return "ok",200
 if "VENDER" in txt:
  if SEL in ENTS:
   pnl=(pn/ENTS[SEL]["entry"]-1)*100
   del ENTS[SEL]
   open(FILE,"w").write(json.dumps({"ENTS":ENTS}))
   send(cid=str(round(pnl,1))+"%")
  else:
   send(cid,"X")
  return "ok",200
 send(cid,SEL+" "+str(round(pn,2))+" V212")
 return "ok",200
print("V212 STARTING",flush=True)
port=int(os.getenv("PORT","10000"))
print("V212 BIND",port,flush=True)
app.run(host="0.0.0.0",port=port,debug=False,use_reloader=False)
