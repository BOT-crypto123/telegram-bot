import os,requests,io,json,time,threading
from flask import Flask,request
from datetime import datetime,timedelta
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP"
E={}
ON=False
CID=None
F="/tmp/b.json"
G="/tmp/a.json"
def L():
 global E,ON,CID
 if os.path.exists(F):
  E=json.load(open(F)).get("ENTS",{})
 if os.path.exists(G):
  d=json.load(open(G))
  ON=d.get("ON",0)
  CID=d.get("CID")
L()
def p(s):
 r=requests.get("https://api.coinbase.com/v2/prices/"+s+"-USD/spot",timeout=8).json()
 return float(r.get("data",{}).get("amount","0")or 0)
def c(s):
 r=requests.get("https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",headers={"User-Agent":"M"},timeout=10).json()
 return sorted(r)[-60:] if isinstance(r,list) else []
def rsi(a):
 if len(a)<15:
  return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 88 if l==0 else 12 if g==0 else 100-100/(1+g/l)
def snd(x,t):
 k={"keyboard":[["BTC","ETH"],["SOL","XRP"],["GRAF","AUTO"]],"resize_keyboard":True}
 requests.post("https://api.telegram.org/bot"+T+"/sendMessage",json={"chat_id":x,"text":t,"reply_markup":k},timeout=10)
def lp():
 while True:
  time.sleep(600)
  if ON and CID:
   for s in ["BTC","ETH","SOL","XRP"]:
    cl=c(s)
    if cl and rsi([a[4] for a in cl])<30:
     snd(CID,"AUTO COMPRA FUERTE "+s)
threading.Thread(target=lp,daemon=True).start()
@A.route("/")
def h():
 return "V233 MINI LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,ON,CID
 d=request.get_json(force=True,silent=True) or {}
 m=d.get("message",{})
 cid=m.get("chat",{}).get("id",0)
 t=m.get("text","").upper()
 if "BTC" in t:
  S="BTC"
 if "ETH" in t:
  S="ETH"
 if "SOL" in t:
  S="SOL"
 if "XRP" in t:
  S="XRP"
 if "AUTO" in t:
  ON=not ON
  CID=cid
  open(G,"w").write(json.dumps({"ON":ON,"CID":cid}))
  snd(cid,"AUTO ON" if ON else "AUTO OFF")
  return "ok",200
 cl=c(S)
 cs=[a[4] for a in cl]
 pr=p(S) or cs[-1]
 rr=rsi(cs)
 pc=(pr/cs[-2]-1)*100 if len(cs)>1 else 0
 sg="ESPERA"
 if rr<30:
  sg="COMPRA FUERTE"
 elif rr>70:
  sg="VENTA FUERTE"
 elif rr<45:
  sg="COMPRA"
 elif rr>55:
  sg="VENTA"
 from PIL import Image,ImageDraw
 mn=min(cs)
 mx=max(cs)
 if mn==mx:
  mx*=1.001
 im=Image.new("RGB",(1000,560),(10,14,21))
 dr=ImageDraw.Draw(im)
 i=0
 for x in cl:
  xx=20+i*13
  y1=490-(x[1]-mn)/(mx-mn)*460
  y2=490-(x[2]-mn)/(mx-mn)*460
  yt=490-(max(x[3],x[4])-mn)/(mx-mn)*460
  yb=490-(min(x[3],x[4])-mn)/(mx-mn)*460
  co=(0,230,118) if x[4]>=x[3] else (255,61,87)
  dr.line([xx+3,y1,xx+3,y2],fill=co)
  dr.rectangle([xx,yt,xx+6,yb],fill=co)
  i+=1
 hr=(datetime.utcnow()-timedelta(hours=6)).strftime("%I:%M %p")
 cap=S+" "+str(round(pr,4))+" | "+hr+" | "+("+" if pc>=0 else "")+str(round(pc,2))+"%\nRSI:"+str(round(rr,1))+" SENAL:"+sg+"\nV233 MINI AUTO:"+str(ON)
 b=io.BytesIO()
 b.name="g.png"
 im.save(b,"PNG")
 b.seek(0)
 requests.post("https://api.telegram.org/bot"+T+"/sendPhoto",data={"chat_id":cid,"caption":cap},files={"photo":b},timeout=12)
 return "ok",200
A.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
