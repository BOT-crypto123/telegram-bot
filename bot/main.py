import os,requests,io,json,time,threading
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP"
E={}
ON=False
CID=None
F="/tmp/b.json"
G="/tmp/a.json"
try:
 if os.path.exists(F):
  E=json.load(open(F))
except:
 E={}
try:
 if os.path.exists(G):
  d=json.load(open(G))
  ON=d.get("ON",0)
  CID=d.get("CID")
except:
 ON=False
 CID=None
def p(s):
 try:
  r=requests.get(
   "https://api.coinbase.com/v2/prices/"+s+"-USD/spot",
   timeout=8).json()
  return float(r["data"]["amount"])
 except:
  return 0
def c(s):
 try:
  r=requests.get(
   "https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",
   headers={"User-Agent":"M"},timeout=10).json()
  return sorted(r)[-60:]
 except:
  return []
def rsi(a):
 if len(a)<15:
  return 50
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 100-100/(1+g/l) if l else 88
def sav():
 try:
  open(F,"w").write(json.dumps(E))
 except:
  pass
def s2(x,t):
 try:
  kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],
   ["COMPRAR","VENDER"],["AUTO"]],
   "resize_keyboard":True}
  requests.post(
   "https://api.telegram.org/bot"+T+"/sendMessage",
   json={"chat_id":x,"text":t,"reply_markup":kb},
   timeout=10)
 except:
  pass
def lp():
 while True:
  time.sleep(300)
  try:
   if not ON or not CID:
    continue
   for sy in ["BTC","ETH","SOL","XRP"]:
    cl=c(sy)
    if not cl:
     continue
    cs=[]
    for q in cl:
     cs.append(q[4])
    rr=rsi(cs)
    pr=p(sy)
    if rr<30 and not E.get(sy):
     E[sy]=pr
     sav()
     s2(CID,"AUTO COMPRO "+sy+" RSI "+str(round(rr,1)))
    if rr>70 and E.get(sy):
     pf=(pr/E[sy]-1)*100
     del E[sy]
     sav()
     s2(CID,"AUTO VENDIO "+sy+" PROFIT "+str(round(pf,2))+"%")
  except:
   time.sleep(60)
threading.Thread(target=lp,daemon=True).start()
@A.route("/")
def h():
 return "V241 LIVE AUTO:"+str(ON),200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,ON,CID
 j=request.get_json(force=True,silent=True)or{}
 m=j.get("message",{})
 cid=m.get("chat",{}).get("id",0)
 if not cid:
  return "ok",200
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
  try:
   open(G,"w").write(json.dumps({"ON":ON,"CID":cid}))
  except:
   pass
  s2(cid,"AUTO ON - COMPRA RSI<30 VENDE RSI>70" if ON else "AUTO OFF")
  return "ok",200
 cl=c(S)
 cs=[]
 for q in cl:
  cs.append(q[4])
 if not cs:
  s2(cid,"SIN DATOS")
  return "ok",200
 pr=p(S) or cs[-1]
 rr=rsi(cs)
 pc=(pr/cs[-2]-1)*100 if len(cs)>1 else 0
 sg="ESPERA"
 if rr<30:
  sg="COMPRA FUERTE"
 elif rr>70:
  sg="VENTA FUERTE"
 msg=""
 if "COMPRAR" in t:
  E[S]=pr
  sav()
  msg="COMPRADO "+S+" EN "+str(pr)
 if "VENDER" in t:
  en=E.get(S,0)
  if en:
   pf=(pr/en-1)*100
   msg="VENDIDO "+S+" PROFIT "+str(round(pf,2))+"%"
   del E[S]
   sav()
  else:
   msg="NO TIENES "+S
 from PIL import Image,ImageDraw
 mn=min(cs)
 mx=max(cs)
 if mn==mx:
  mx*=1.001
 im=Image.new("RGB",(800,400),(10,14,21))
 dr=ImageDraw.Draw(im)
 i=0
 for x in cl:
  xx=10+i*12
  y1=380-(x[1]-mn)/(mx-mn)*350
  y2=380-(x[2]-mn)/(mx-mn)*350
  yt=380-(max(x[3],x[4])-mn)/(mx-mn)*350
  yb=380-(min(x[3],x[4])-mn)/(mx-mn)*350
  co=(0,230,118) if x[4]>=x[3] else (255,61,87)
  dr.line([xx,y1,xx,y2],fill=co)
  dr.rectangle([xx,yt,xx+4,yb],fill=co)
  i+=1
 sgn="+" if pc>=0 else ""
 a1=S+" "+str(round(pr,4))
 a2
