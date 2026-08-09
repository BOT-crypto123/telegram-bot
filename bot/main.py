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
if os.path.exists(F):
 E=json.load(open(F))
if os.path.exists(G):
 d=json.load(open(G))
 ON=d.get("ON",0)
 CID=d.get("CID")
def p(s):
 r=requests.get(
  "https://api.coinbase.com/v2/prices/"+s+"-USD/spot",
  timeout=8).json()
 return float(r["data"]["amount"])
def c(s):
 r=requests.get(
  "https://api.exchange.coinbase.com/products/"+s+"-USD/candles?granularity=60",
  headers={"User-Agent":"M"},timeout=10).json()
 return sorted(r)[-60:]
def rsi(a):
 g=l=0
 for i in range(1,15):
  d=a[i]-a[i-1]
  g+=d if d>0 else 0
  l+=-d if d<0 else 0
 return 100-100/(1+g/l) if l else 88
def sav():
 open(F,"w").write(json.dumps(E))
def s2(x,t):
 kb={"keyboard":[["BTC","ETH"],["SOL","XRP"],
  ["COMPRAR","VENDER"],["AUTO"]],
  "resize_keyboard":True}
 requests.post(
  "https://api.telegram.org/bot"+T+"/sendMessage",
  json={"chat_id":x,"text":t,"reply_markup":kb},
  timeout=10)
def lp():
 while True:
  time.sleep(300)
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
   # AUTO COMPRA RSI<30
   if rr<30 and not E.get(sy):
    E[sy]=pr
    sav()
    s2(CID,"AUTO COMPRO "+sy+" EN "+str(pr)+" RSI "+str(round(rr,1)))
   # AUTO VENTA RSI>70
   if rr>70 and E.get(sy):
    pf=(pr/E[sy]-1)*100
    del E[sy]
    sav()
    s2(CID,"AUTO VENDIO "+sy+" PROFIT "+str(round(pf,2))+"%")
threading.Thread(target=lp,daemon=True).start()
@A.route("/")
def h():
 return "V240 LIVE",200
@A.route("/webhook",methods=["POST"])
def w():
 global S,E,ON,CID
 j=request.get_json(force=True,silent=True)or{}
 m=j.get("message",{})
 cid=m["chat"]["id"]
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
  s2(cid,"AUTO ON - COMPRANDO SOLO RSI<30 VENDIENDO RSI>70" if ON else "AUTO OFF")
  return "ok",200
 cl=c(S)
 cs=[]
 for q in cl:
  cs.append(q[4])
 pr=p(S)
 rr=rsi(cs)
 pc=(pr/cs[-2]-1)*100
