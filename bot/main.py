import os,requests,io,json,time,threading
from flask import Flask,request
T=os.getenv("TELE_TOKEN")or""
A=Flask(__name__)
S="XRP"
E={}
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
def s2(x,t):
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],
  ["COMPRAR","VENDER"],["AUTO"]],
  "resize_keyboard":True}
 try:
  requests.post(
   "https://api.telegram.org/bot"+T+"/sendMessage",
   json={"chat_id":x,"text":t,"reply_markup":kb},
   timeout=10)
 except:
  pass
def lp():
 while True:
  time.sleep(300)
  if not ON or not CID:
   continue
  try:
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
     s2(CID,"AUTO COMPRO "+sy+" RSI "+str(round(rr,1)))
    if rr>70 and E.get(sy):
     pf=(pr/E[sy]-1)*100
     del E[sy]
     s2(CID,"AUTO VENDIO "+sy+" PROFIT "+str(round(pf,2))+"%")
  except:
   time.sleep(60)
threading.Thread(target=lp,daemon=True).start()
@A.route("/")
def h():
 return "V242 LIVE",200
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
  s2(cid,"AUTO ON RSI<30 COMPRA RSI>70 VENDE" if ON else "AUTO OFF")
  return "ok",200
 cl=c(S)
 cs=[]
 for q in cl:
  cs.append(q[4])
 if not cs:
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
  msg="COMPRADO "+S
 if "VENDER" in t:
  if E.get(S):
   pf=(pr/E[S]-1)*100
   msg="VENDIDO "+S+" "+str(round(pf,2))+"%"
   del E[S]
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
 st="ON" if ON else "OFF"
 a1=S+" "+str(round(pr,4))
 a2=sgn+str(round(pc,2))+"% RSI:"+str(round(rr,1))
 a3="SENAL:"+sg+" AUTO:"+st+" V242"
 if msg:
  a3=msg+"\n"+a3
 cap=a1+"\n"+a2+"\n"+a3
 b=io.BytesIO()
 b.name="g.png"
 im.save(b,"PNG")
 b.seek(0)
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],
  ["COMPRAR","VENDER"],["AUTO"]],
  "resize_keyboard":True}
 requests.post(
  "https://api.telegram.org/bot"+T+"/sendPhoto",
  data={"chat_id":cid,"caption":cap,
  "reply_markup":json.dumps(kb)},
  files={"photo":b},timeout=12)
 return "ok",200
A.run(host="0.0.0.0",port=int(os.getenv("PORT","10000")))
